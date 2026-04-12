from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.solicitud import (
    CanalOrigen,
    EstadoSolicitud,
    SeguimientoSolicitud,
    SolicitudCiudadana,
    TipoSolicitud,
)
from app.schemas.solicitud import (
    HeatmapPoint,
    ParticipacionDashboardStats,
    SolicitudCreate,
)

# ── Keyword-based categorization rules ─────────────────────
# Each rule: (regex_pattern, category, priority)
_CATEGORIZATION_RULES: list[tuple[str, str, int]] = [
    (r"inseguridad|robo|asalto|violencia|crimen|delincuencia|balacera|extorsion", "seguridad", 1),
    (
        r"bache|agua|luz|basura|drenaje|alcantarilla|alumbrado|pavimento|fugas",
        "servicios_publicos",
        2,
    ),
    (r"hospital|clinica|salud|medicamento|enfermedad|ambulancia|doctor|medico", "salud", 2),
    (r"escuela|maestro|educacion|beca|universidad|preparatoria|kinder", "educacion", 3),
    (r"transporte|metrobus|metro|ruta|camion|trafico|vialidad|semaforo", "transporte", 3),
    (r"empleo|trabajo|desempleo|negocio|economia|comercio", "economia", 3),
    (r"parque|deporte|recreacion|cultura|biblioteca|espacio.publico", "cultura_deporte", 4),
    (r"medio.ambiente|contaminacion|ruido|arbol|area.verde|ecologia", "medio_ambiente", 3),
    (r"vivienda|predio|construccion|regularizacion|terreno", "vivienda", 3),
]


class ParticipacionService:
    """Service layer for Participacion Ciudadana module."""

    @staticmethod
    def auto_categorize(descripcion: str) -> tuple[str, int]:
        """Suggest a category and priority from request description using keyword matching.

        Returns:
            Tuple of (category, priority). Defaults to ("general", 3) if no match.
        """
        text = descripcion.lower()
        for pattern, category, priority in _CATEGORIZATION_RULES:
            if re.search(pattern, text):
                return category, priority
        return "general", 3

    @staticmethod
    async def create_solicitud(
        db: AsyncSession,
        data: SolicitudCreate,
        user_id: int,
    ) -> SolicitudCiudadana:
        """Create a new solicitud ciudadana with auto-categorization and initial seguimiento."""
        solicitud_data = data.model_dump(exclude={"latitud", "longitud"})

        # Build geometry from lat/lon
        if data.latitud is not None and data.longitud is not None:
            solicitud_data["ubicacion"] = f"SRID=4326;POINT({data.longitud} {data.latitud})"

        # Auto-categorize if no category provided
        if not solicitud_data.get("categoria"):
            cat, pri = ParticipacionService.auto_categorize(data.descripcion)
            solicitud_data["categoria"] = cat
            # Only override priority if not explicitly provided
            if data.prioridad is None:
                solicitud_data["prioridad"] = pri

        # Default priority if still None
        if solicitud_data.get("prioridad") is None:
            solicitud_data["prioridad"] = 3

        solicitud = SolicitudCiudadana(**solicitud_data)
        db.add(solicitud)
        await db.flush()
        await db.refresh(solicitud)

        # Create initial seguimiento
        seguimiento = SeguimientoSolicitud(
            solicitud_id=solicitud.id,
            usuario_id=user_id,
            accion="creacion",
            detalle=f"Solicitud creada via canal {data.canal.value}",
            estado_anterior=None,
            estado_nuevo=EstadoSolicitud.RECIBIDA.value,
        )
        db.add(seguimiento)
        await db.flush()

        await db.refresh(solicitud)
        return solicitud

    @staticmethod
    async def assign_solicitud(
        db: AsyncSession,
        solicitud_id: int,
        asignado_a_id: int | None,
        dirigente_responsable_id: int | None,
        user_id: int,
    ) -> SolicitudCiudadana:
        """Assign a solicitud to a user and/or dirigente. Updates estado to ASIGNADA."""
        result = await db.execute(
            select(SolicitudCiudadana).where(SolicitudCiudadana.id == solicitud_id)
        )
        solicitud = result.scalar_one_or_none()
        if solicitud is None:
            raise ValueError(f"Solicitud {solicitud_id} not found")

        estado_anterior = solicitud.estado.value

        if asignado_a_id is not None:
            solicitud.asignado_a_id = asignado_a_id
        if dirigente_responsable_id is not None:
            solicitud.dirigente_responsable_id = dirigente_responsable_id

        solicitud.estado = EstadoSolicitud.ASIGNADA

        # Build detail message
        parts: list[str] = []
        if asignado_a_id is not None:
            parts.append(f"usuario_id={asignado_a_id}")
        if dirigente_responsable_id is not None:
            parts.append(f"dirigente_id={dirigente_responsable_id}")
        detalle = f"Asignada a {', '.join(parts)}"

        seguimiento = SeguimientoSolicitud(
            solicitud_id=solicitud.id,
            usuario_id=user_id,
            accion="asignacion",
            detalle=detalle,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoSolicitud.ASIGNADA.value,
        )
        db.add(seguimiento)
        await db.flush()
        await db.refresh(solicitud)
        return solicitud

    @staticmethod
    async def respond_solicitud(
        db: AsyncSession,
        solicitud_id: int,
        respuesta: str,
        user_id: int,
    ) -> SolicitudCiudadana:
        """Respond to a solicitud and update estado to RESUELTA."""
        result = await db.execute(
            select(SolicitudCiudadana).where(SolicitudCiudadana.id == solicitud_id)
        )
        solicitud = result.scalar_one_or_none()
        if solicitud is None:
            raise ValueError(f"Solicitud {solicitud_id} not found")

        estado_anterior = solicitud.estado.value
        solicitud.respuesta = respuesta
        solicitud.fecha_respuesta = datetime.now(UTC)
        solicitud.estado = EstadoSolicitud.RESUELTA

        seguimiento = SeguimientoSolicitud(
            solicitud_id=solicitud.id,
            usuario_id=user_id,
            accion="respuesta",
            detalle=f"Respuesta proporcionada: {respuesta[:200]}",
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoSolicitud.RESUELTA.value,
        )
        db.add(seguimiento)
        await db.flush()
        await db.refresh(solicitud)
        return solicitud

    @staticmethod
    async def get_dashboard_stats(
        db: AsyncSession,
        org_id: int | None = None,
    ) -> ParticipacionDashboardStats:
        """Aggregate dashboard statistics for solicitudes ciudadanas."""
        base_filter = True
        if org_id is not None:
            base_filter = SolicitudCiudadana.org_id == org_id

        # Total count
        total_result = await db.execute(
            select(func.count(SolicitudCiudadana.id)).where(base_filter)
        )
        total = total_result.scalar_one()

        # By tipo
        tipo_result = await db.execute(
            select(
                SolicitudCiudadana.tipo,
                func.count(SolicitudCiudadana.id),
            )
            .where(base_filter)
            .group_by(SolicitudCiudadana.tipo)
        )
        by_tipo = {row[0].value: row[1] for row in tipo_result.all()}

        # By estado
        estado_result = await db.execute(
            select(
                SolicitudCiudadana.estado,
                func.count(SolicitudCiudadana.id),
            )
            .where(base_filter)
            .group_by(SolicitudCiudadana.estado)
        )
        by_estado = {row[0].value: row[1] for row in estado_result.all()}

        # By prioridad
        prioridad_result = await db.execute(
            select(
                SolicitudCiudadana.prioridad,
                func.count(SolicitudCiudadana.id),
            )
            .where(base_filter)
            .group_by(SolicitudCiudadana.prioridad)
        )
        by_prioridad = {str(row[0]): row[1] for row in prioridad_result.all()}

        # Average resolution time (for resolved solicitudes)
        resolved_filter = SolicitudCiudadana.estado == EstadoSolicitud.RESUELTA
        if org_id is not None:
            resolved_filter = resolved_filter & (SolicitudCiudadana.org_id == org_id)

        avg_result = await db.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        SolicitudCiudadana.fecha_respuesta - SolicitudCiudadana.created_at,
                    )
                )
            ).where(
                resolved_filter,
                SolicitudCiudadana.fecha_respuesta.isnot(None),
            )
        )
        avg_seconds = avg_result.scalar_one()
        avg_resolution_hours = round(avg_seconds / 3600.0, 2) if avg_seconds else None

        # Top colonias
        colonia_result = await db.execute(
            select(
                SolicitudCiudadana.colonia,
                func.count(SolicitudCiudadana.id).label("count"),
            )
            .where(base_filter, SolicitudCiudadana.colonia.isnot(None))
            .group_by(SolicitudCiudadana.colonia)
            .order_by(func.count(SolicitudCiudadana.id).desc())
            .limit(10)
        )
        top_colonias = [{"colonia": row[0], "count": row[1]} for row in colonia_result.all()]

        return ParticipacionDashboardStats(
            total=total,
            by_tipo=by_tipo,
            by_estado=by_estado,
            by_prioridad=by_prioridad,
            avg_resolution_hours=avg_resolution_hours,
            top_colonias=top_colonias,
        )

    @staticmethod
    async def get_heatmap_data(
        db: AsyncSession,
        org_id: int | None = None,
    ) -> list[HeatmapPoint]:
        """Return solicitudes with location data for map visualization."""
        from geoalchemy2.functions import ST_X, ST_Y

        query = select(
            ST_Y(SolicitudCiudadana.ubicacion).label("lat"),
            ST_X(SolicitudCiudadana.ubicacion).label("lon"),
            SolicitudCiudadana.tipo,
            SolicitudCiudadana.prioridad,
            SolicitudCiudadana.titulo,
        ).where(SolicitudCiudadana.ubicacion.isnot(None))

        if org_id is not None:
            query = query.where(SolicitudCiudadana.org_id == org_id)

        result = await db.execute(query)
        return [
            HeatmapPoint(
                lat=row.lat,
                lon=row.lon,
                tipo=row.tipo.value,
                prioridad=row.prioridad,
                titulo=row.titulo,
            )
            for row in result.all()
        ]

    @staticmethod
    async def create_from_chatwoot(
        db: AsyncSession,
        conversation_id: str,
        content: str,
        sender_name: str | None,
        user_id: int,
    ) -> SolicitudCiudadana:
        """Create a solicitud from a Chatwoot-MX webhook event.

        Auto-categorizes the content and creates with canal=WHATSAPP.
        """
        categoria, prioridad = ParticipacionService.auto_categorize(content)

        # Truncate content for titulo (max 255 chars)
        titulo = content[:252] + "..." if len(content) > 255 else content

        solicitud_data = SolicitudCreate(
            tipo=TipoSolicitud.SOLICITUD_INFO,
            titulo=titulo,
            descripcion=content,
            canal=CanalOrigen.WHATSAPP,
            categoria=categoria,
            prioridad=prioridad,
            chatwoot_conversation_id=conversation_id,
        )

        return await ParticipacionService.create_solicitud(
            db=db,
            data=solicitud_data,
            user_id=user_id,
        )
