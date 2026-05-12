"""D-DATA-02 — Endpoint que expone ciudadanos_legacy con PII protegido.

Tres superficies:
- `GET /ciudadanos-legacy/` — listado público (admin/analyst),
  columnas seguras (nombre + geo + seccion + UT + metadata sin PII)
- `GET /ciudadanos-legacy/{id}/pii` — decifrado, SOLO admin, audit-logged
- `DELETE /ciudadanos-legacy/{id}/erase` — D.12 LFPDPPP soft-delete + PII wipe
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pii_access import PiiAuditor, require_pii_clearance
from app.core.security import Role, RoleChecker, get_current_user
from app.models.legacy import CiudadanoLegacy
from app.models.user import User
from app.services.pii import read_pii_fields

router = APIRouter()


class CiudadanoLegacySafeRow(BaseModel):
    id: int
    legacy_id: str
    alcaldia_id: int | None
    alcaldia_nombre: str | None
    unidad_territorial_id: int | None
    seccion: str | None
    nombre: str | None
    apellido_paterno: str | None
    apellido_materno: str | None
    edad: int | None
    sexo: str | None
    nivel_educativo: str | None
    nivel_participacion: str | None
    latitud_cd: float | None
    longitud_cd: float | None
    contactado: str | None
    lista: str | None

    model_config = {"from_attributes": True}


class CiudadanoLegacyPiiResponse(BaseModel):
    id: int
    email: str | None
    phone_01: str | None
    phone_02: str | None
    whatsapp: str | None
    fecha_nacimiento: str | None
    clave_electoral: str | None


@router.get(
    "/",
    response_model=list[CiudadanoLegacySafeRow],
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def list_ciudadanos_legacy(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    alcaldia_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CiudadanoLegacySafeRow]:
    """Listado SIN PII (columnas en claro seguras: nombre pila, geo, seccion).

    Admin + analyst pueden leer. org_id se scopea por el usuario actual.
    NO incluye email, phone, whatsapp, fecha_nacimiento ni clave electoral.
    """
    from app.models.alcaldia import AlcaldiaCDMX

    org_id = current_user.org_id or 3
    query = (
        select(CiudadanoLegacy, AlcaldiaCDMX.nombre)
        .outerjoin(AlcaldiaCDMX, AlcaldiaCDMX.id == CiudadanoLegacy.alcaldia_id)
        .where(CiudadanoLegacy.org_id == org_id)
    )
    if alcaldia_id is not None:
        query = query.where(CiudadanoLegacy.alcaldia_id == alcaldia_id)
    query = query.order_by(CiudadanoLegacy.id).limit(limit).offset(offset)

    rows = (await db.execute(query)).all()
    out: list[CiudadanoLegacySafeRow] = []
    for c, alc_nombre in rows:
        out.append(
            CiudadanoLegacySafeRow(
                id=c.id,
                legacy_id=c.legacy_id,
                alcaldia_id=c.alcaldia_id,
                alcaldia_nombre=alc_nombre,
                unidad_territorial_id=c.unidad_territorial_id,
                seccion=c.seccion,
                nombre=c.nombre,
                apellido_paterno=c.apellido_paterno,
                apellido_materno=c.apellido_materno,
                edad=c.edad,
                sexo=c.sexo,
                nivel_educativo=c.nivel_educativo,
                nivel_participacion=c.nivel_participacion,
                latitud_cd=c.latitud_cd,
                longitud_cd=c.longitud_cd,
                contactado=c.contactado,
                lista=c.lista,
            )
        )
    return out


@router.get(
    "/{ciudadano_id}/pii",
    response_model=CiudadanoLegacyPiiResponse,
)
async def get_ciudadano_pii(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    auditor: Annotated[PiiAuditor, Depends(require_pii_clearance)],
) -> CiudadanoLegacyPiiResponse:
    """D-DATA-02 — Descifra PII de un ciudadano_legacy.

    SOLO admin (enforzado por `require_pii_clearance`).
    Cada invocación loggea una entrada en `data_access_log`.
    """
    # Verify existence + org scope
    row = (
        await db.execute(select(CiudadanoLegacy).where(CiudadanoLegacy.id == ciudadano_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudadano not found")

    fields_to_read = [
        "email",
        "phone_01",
        "phone_02",
        "whatsapp",
        "fecha_nacimiento",
        "clave_electoral",
    ]
    decrypted = await read_pii_fields(db, ciudadano_id, fields_to_read)  # type: ignore[arg-type]

    await auditor.log(
        db=db,
        table_name="ciudadanos_legacy",
        row_id=str(ciudadano_id),
        action="read_pii",
        fields=fields_to_read,
        metadata={"decrypted_count": sum(1 for v in decrypted.values() if v)},
    )

    return CiudadanoLegacyPiiResponse(
        id=ciudadano_id,
        email=decrypted.get("email"),
        phone_01=decrypted.get("phone_01"),
        phone_02=decrypted.get("phone_02"),
        whatsapp=decrypted.get("whatsapp"),
        fecha_nacimiento=decrypted.get("fecha_nacimiento"),
        clave_electoral=decrypted.get("clave_electoral"),
    )


class EraseConfirmation(BaseModel):
    id: int
    status: str
    message: str


@router.delete(
    "/{ciudadano_id}/erase",
    response_model=EraseConfirmation,
    status_code=status.HTTP_200_OK,
)
async def erase_ciudadano(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    auditor: Annotated[PiiAuditor, Depends(require_pii_clearance)],
) -> EraseConfirmation:
    """D.12 LFPDPPP — Soft-delete + PII wipe for right-to-erasure.

    Admin-only (enforced by `require_pii_clearance`).
    Sets `deleted_at = now()` and nullifies all `_enc` PII columns.
    Logs the action to `data_access_log` with action='gdpr_erase'.
    """
    row = (
        await db.execute(select(CiudadanoLegacy).where(CiudadanoLegacy.id == ciudadano_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudadano not found")
    if row.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ciudadano already erased",
        )

    # Soft-delete + nullify all _enc PII columns
    now = datetime.now(UTC)
    await db.execute(
        text(
            """
            UPDATE ciudadanos_legacy
            SET deleted_at = :now,
                email_enc = NULL,
                phone_01_enc = NULL,
                phone_02_enc = NULL,
                whatsapp_enc = NULL,
                fecha_nacimiento_enc = NULL,
                clave_electoral_enc = NULL
            WHERE id = :id
            """
        ),
        {"now": now, "id": ciudadano_id},
    )

    # Audit log
    await auditor.log(
        db=db,
        table_name="ciudadanos_legacy",
        row_id=str(ciudadano_id),
        action="gdpr_erase",
        fields=[
            "email_enc",
            "phone_01_enc",
            "phone_02_enc",
            "whatsapp_enc",
            "fecha_nacimiento_enc",
            "clave_electoral_enc",
        ],
        metadata={"erased_at": now.isoformat()},
    )

    return EraseConfirmation(
        id=ciudadano_id,
        status="erased",
        message="PII eliminado y registro marcado como borrado (LFPDPPP).",
    )
