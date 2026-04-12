from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campana import (
    Campana,
    CampanaMensaje,
    CampanaSegmento,
    EstadoCampana,
    EstadoMensaje,
)
from app.models.ciudadano import Ciudadano
from app.models.voter_score import VoterScore
from app.schemas.campana import CampanaSegmentoCreate


class CampaignManager:
    """Orchestrates WhatsApp campaign lifecycle on the CRECE side.

    IMPORTANT: This service NEVER calls WhatsApp Cloud API directly.
    Actual message delivery is handled by Chatwoot-MX via webhook integration.
    """

    @staticmethod
    async def build_segment(
        db: AsyncSession,
        campana_id: int,
        segmento: CampanaSegmentoCreate,
    ) -> int:
        """Build a segment filter and return the count of matching ciudadanos.

        Creates a CampanaSegmento record with the resolved count.
        """
        query = select(func.count(Ciudadano.id)).where(
            Ciudadano.telefono.isnot(None),
            Ciudadano.telefono != "",
        )

        query = CampaignManager._apply_segment_filters(query, segmento)

        result = await db.execute(query)
        count = result.scalar_one()

        db_segmento = CampanaSegmento(
            campana_id=campana_id,
            filtro_seccion_id=segmento.filtro_seccion_id,
            filtro_intencion_voto=segmento.filtro_intencion_voto,
            filtro_edad_rango=segmento.filtro_edad_rango,
            filtro_escolaridad=segmento.filtro_escolaridad,
            filtro_es_simpatizante=segmento.filtro_es_simpatizante,
            filtro_es_promotor=segmento.filtro_es_promotor,
            filtro_score_min=segmento.filtro_score_min,
            filtro_score_max=segmento.filtro_score_max,
            ciudadanos_count=count,
        )
        db.add(db_segmento)
        await db.flush()

        return count

    @staticmethod
    async def prepare_campaign(db: AsyncSession, campana_id: int) -> int:
        """Resolve all segment filters into CampanaMensaje records.

        For each matching ciudadano with a phone number, creates a pending
        message record. Deduplicates across segments so each ciudadano
        receives at most one message per campaign.

        Returns the total number of messages created.
        """
        campana = await db.get(Campana, campana_id)
        if campana is None:
            raise ValueError(f"Campaign {campana_id} not found")

        if campana.estado != EstadoCampana.BORRADOR:
            raise ValueError(
                f"Campaign must be in BORRADOR state to prepare, current: {campana.estado}"
            )

        # Collect all segments for this campaign
        seg_result = await db.execute(
            select(CampanaSegmento).where(CampanaSegmento.campana_id == campana_id)
        )
        segmentos = list(seg_result.scalars().all())

        if not segmentos:
            raise ValueError("Campaign has no segments defined")

        # Union of all ciudadano IDs matching any segment
        ciudadano_ids: set[int] = set()

        for seg in segmentos:
            query = select(Ciudadano.id, Ciudadano.telefono).where(
                Ciudadano.telefono.isnot(None),
                Ciudadano.telefono != "",
            )
            query = CampaignManager._apply_segment_filters_raw(query, seg)

            result = await db.execute(query)
            for row in result.all():
                ciudadano_ids.add(row.id)

        # Delete any previously prepared messages (idempotent re-preparation)
        existing = await db.execute(
            select(CampanaMensaje.ciudadano_id).where(CampanaMensaje.campana_id == campana_id)
        )
        existing_ids = {row.ciudadano_id for row in existing.all()}
        new_ids = ciudadano_ids - existing_ids

        # Fetch phone numbers for new ciudadanos
        if new_ids:
            phone_result = await db.execute(
                select(Ciudadano.id, Ciudadano.telefono).where(Ciudadano.id.in_(new_ids))
            )
            for row in phone_result.all():
                mensaje = CampanaMensaje(
                    campana_id=campana_id,
                    ciudadano_id=row.id,
                    telefono=row.telefono,
                    estado=EstadoMensaje.PENDIENTE,
                )
                db.add(mensaje)

        total = len(existing_ids) + len(new_ids)

        # Update campaign counters
        campana.total_destinatarios = total
        campana.estado = EstadoCampana.PROGRAMADA
        await db.flush()

        return total

    @staticmethod
    async def get_campaign_payload(
        db: AsyncSession,
        campana_id: int,
    ) -> list[dict]:
        """Return the payload ready for Chatwoot-MX webhook consumption.

        Each entry contains the information Chatwoot needs to deliver
        a WhatsApp message. CRECE never calls WhatsApp directly.
        """
        campana = await db.get(Campana, campana_id)
        if campana is None:
            raise ValueError(f"Campaign {campana_id} not found")

        result = await db.execute(
            select(CampanaMensaje).where(
                CampanaMensaje.campana_id == campana_id,
                CampanaMensaje.estado == EstadoMensaje.PENDIENTE,
            )
        )
        mensajes = list(result.scalars().all())

        payload = []
        for msg in mensajes:
            payload.append(
                {
                    "mensaje_id": msg.id,
                    "telefono": msg.telefono,
                    "mensaje": campana.plantilla_mensaje,
                    "variables": campana.variables_plantilla,
                    "ciudadano_id": msg.ciudadano_id,
                    "campana_id": campana_id,
                }
            )

        return payload

    @staticmethod
    async def update_delivery_status(
        db: AsyncSession,
        mensaje_id: int,
        status: EstadoMensaje,
        chatwoot_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Process a delivery status webhook callback from Chatwoot-MX.

        Updates the individual message record and increments campaign counters.
        """
        mensaje = await db.get(CampanaMensaje, mensaje_id)
        if mensaje is None:
            raise ValueError(f"Message {mensaje_id} not found")

        old_status = mensaje.estado
        mensaje.estado = status
        now = datetime.now(UTC)

        if chatwoot_id:
            mensaje.chatwoot_message_id = chatwoot_id

        if error:
            mensaje.error_mensaje = error

        # Set delivery timestamps based on status progression
        if status == EstadoMensaje.ENVIADO and mensaje.enviado_at is None:
            mensaje.enviado_at = now
        elif status == EstadoMensaje.ENTREGADO and mensaje.entregado_at is None:
            mensaje.entregado_at = now
            if mensaje.enviado_at is None:
                mensaje.enviado_at = now
        elif status == EstadoMensaje.LEIDO and mensaje.leido_at is None:
            mensaje.leido_at = now
            if mensaje.entregado_at is None:
                mensaje.entregado_at = now
            if mensaje.enviado_at is None:
                mensaje.enviado_at = now

        # Update campaign-level counters (increment only on status transitions)
        campana = await db.get(Campana, mensaje.campana_id)
        if campana is not None:
            CampaignManager._update_campaign_counter(campana, old_status, status)

        await db.flush()

    @staticmethod
    async def get_campaign_analytics(
        db: AsyncSession,
        campana_id: int,
    ) -> dict:
        """Compute delivery funnel analytics for a campaign."""
        campana = await db.get(Campana, campana_id)
        if campana is None:
            raise ValueError(f"Campaign {campana_id} not found")

        # Count failed messages
        failed_result = await db.execute(
            select(func.count(CampanaMensaje.id)).where(
                CampanaMensaje.campana_id == campana_id,
                CampanaMensaje.estado == EstadoMensaje.FALLIDO,
            )
        )
        total_fallidos = failed_result.scalar_one()

        total = campana.total_destinatarios or 0
        enviados = campana.total_enviados or 0
        entregados = campana.total_entregados or 0

        return {
            "campana_id": campana_id,
            "nombre": campana.nombre,
            "estado": campana.estado,
            "total_destinatarios": total,
            "total_enviados": enviados,
            "total_entregados": entregados,
            "total_leidos": campana.total_leidos or 0,
            "total_respondidos": campana.total_respondidos or 0,
            "total_fallidos": total_fallidos,
            "tasa_envio": (enviados / total) if total > 0 else 0.0,
            "tasa_entrega": (entregados / enviados) if enviados > 0 else 0.0,
            "tasa_lectura": ((campana.total_leidos or 0) / entregados if entregados > 0 else 0.0),
            "tasa_respuesta": (
                (campana.total_respondidos or 0) / entregados if entregados > 0 else 0.0
            ),
            "tasa_fallo": (total_fallidos / total) if total > 0 else 0.0,
        }

    # ── Private helpers ──────────────────────────────────

    @staticmethod
    def _apply_segment_filters(query, segmento: CampanaSegmentoCreate):
        """Apply segment filters from a Pydantic schema to a query."""
        if segmento.filtro_seccion_id is not None:
            query = query.where(Ciudadano.seccion_id == segmento.filtro_seccion_id)
        if segmento.filtro_intencion_voto is not None:
            query = query.where(Ciudadano.intencion_voto == segmento.filtro_intencion_voto)
        if segmento.filtro_edad_rango is not None:
            query = query.where(Ciudadano.edad_rango == segmento.filtro_edad_rango)
        if segmento.filtro_escolaridad is not None:
            query = query.where(Ciudadano.escolaridad == segmento.filtro_escolaridad)
        if segmento.filtro_es_simpatizante is not None:
            query = query.where(Ciudadano.es_simpatizante_mc == segmento.filtro_es_simpatizante)
        if segmento.filtro_es_promotor is not None:
            query = query.where(Ciudadano.es_promotor == segmento.filtro_es_promotor)
        if segmento.filtro_score_min is not None or segmento.filtro_score_max is not None:
            query = query.join(VoterScore, VoterScore.ciudadano_id == Ciudadano.id)
            if segmento.filtro_score_min is not None:
                query = query.where(VoterScore.score >= segmento.filtro_score_min)
            if segmento.filtro_score_max is not None:
                query = query.where(VoterScore.score <= segmento.filtro_score_max)
        return query

    @staticmethod
    def _apply_segment_filters_raw(query, segmento: CampanaSegmento):
        """Apply segment filters from an ORM model to a query."""
        if segmento.filtro_seccion_id is not None:
            query = query.where(Ciudadano.seccion_id == segmento.filtro_seccion_id)
        if segmento.filtro_intencion_voto is not None:
            query = query.where(Ciudadano.intencion_voto == segmento.filtro_intencion_voto)
        if segmento.filtro_edad_rango is not None:
            query = query.where(Ciudadano.edad_rango == segmento.filtro_edad_rango)
        if segmento.filtro_escolaridad is not None:
            query = query.where(Ciudadano.escolaridad == segmento.filtro_escolaridad)
        if segmento.filtro_es_simpatizante is not None:
            query = query.where(Ciudadano.es_simpatizante_mc == segmento.filtro_es_simpatizante)
        if segmento.filtro_es_promotor is not None:
            query = query.where(Ciudadano.es_promotor == segmento.filtro_es_promotor)
        if segmento.filtro_score_min is not None or segmento.filtro_score_max is not None:
            query = query.join(VoterScore, VoterScore.ciudadano_id == Ciudadano.id)
            if segmento.filtro_score_min is not None:
                query = query.where(VoterScore.score >= segmento.filtro_score_min)
            if segmento.filtro_score_max is not None:
                query = query.where(VoterScore.score <= segmento.filtro_score_max)
        return query

    @staticmethod
    def _update_campaign_counter(
        campana: Campana,
        old_status: EstadoMensaje,
        new_status: EstadoMensaje,
    ) -> None:
        """Increment campaign delivery counters based on status transitions.

        Only increments when transitioning forward through the delivery funnel.
        """
        # Define the funnel order for forward-only transitions
        funnel_order = {
            EstadoMensaje.PENDIENTE: 0,
            EstadoMensaje.ENVIADO: 1,
            EstadoMensaje.ENTREGADO: 2,
            EstadoMensaje.LEIDO: 3,
            EstadoMensaje.RESPONDIDO: 4,
            EstadoMensaje.FALLIDO: -1,
        }

        old_rank = funnel_order.get(old_status, 0)
        new_rank = funnel_order.get(new_status, 0)

        if new_status == EstadoMensaje.FALLIDO:
            # No counter to increment for failures (tracked via query)
            return

        if new_rank <= old_rank:
            # Not a forward transition, skip
            return

        # Increment all counters between old and new status
        if new_rank >= 1 and old_rank < 1:
            campana.total_enviados += 1
        if new_rank >= 2 and old_rank < 2:
            campana.total_entregados += 1
        if new_rank >= 3 and old_rank < 3:
            campana.total_leidos += 1
        if new_rank >= 4 and old_rank < 4:
            campana.total_respondidos += 1
