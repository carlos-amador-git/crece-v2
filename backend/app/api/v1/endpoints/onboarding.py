"""Sprint S5 · Onboarding Wizard — 9 secciones.

Endpoints registrados:
    POST   /onboarding/profile                       §1
    GET    /onboarding/profile/{dirigente_id}        §1
    POST   /onboarding/accounts/manual               §2
    POST   /onboarding/search                        §3 (opcional D-23)
    POST   /onboarding/validate-account              §4
    POST   /onboarding/confirm-accounts              §5 (regla dura D-23)
    GET    /oauth/init/{platform}                    §6 stub
    POST   /oauth/callback/{platform}                §6 stub
    GET    /oauth/status/{dirigente_id}              §6
    POST   /onboarding/competidores                  §7 (D-22)
    POST   /onboarding/promesas                      §8 (D-17)
    POST   /onboarding/activate/{dirigente_id}       §9 trigger scraping

Auth JWT admin requerida en todos los mutation endpoints.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User
from app.services.onboarding import (
    accounts_service,
    activation_service,
    competidores_service,
    confirmations_service,
    oauth_service,
    profile_service,
    promesas_service,
    serp_service,
    validator_service,
    youtube_oauth_real,
)

router = APIRouter()
oauth_router = APIRouter()


# ──────────────────────────────────────────────────────────────
# §1 · Detección de perfil
# ──────────────────────────────────────────────────────────────


class ProfileRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    perfil: str = Field(..., min_length=3, max_length=30)


@router.post(
    "/profile",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_profile(
    body: ProfileRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        dirigente = await profile_service.set_perfil(
            db, dirigente_id=body.dirigente_id, perfil=body.perfil
        )
    except profile_service.PerfilInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "dirigente_id": dirigente.id,
        "perfil_1_5": dirigente.perfil_1_5,
        "full_name": dirigente.full_name,
    }


@router.get(
    "/profile/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.VIEWER]))],
)
async def get_profile(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await profile_service.get_perfil(db, dirigente_id=dirigente_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ──────────────────────────────────────────────────────────────
# §2 · Input manual URLs
# ──────────────────────────────────────────────────────────────


class ManualAccount(BaseModel):
    plataforma: str
    url: str


class ManualAccountsRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    accounts: list[ManualAccount]


@router.post(
    "/accounts/manual",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_accounts_manual(
    body: ManualAccountsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await accounts_service.persist_manual_accounts(
            db,
            dirigente_id=body.dirigente_id,
            accounts=[a.model_dump() for a in body.accounts],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ──────────────────────────────────────────────────────────────
# §3 · SERP asistido opcional
# ──────────────────────────────────────────────────────────────


class SerpRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=3)
    cargo: str = Field(..., min_length=3)


@router.post(
    "/search",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_search(
    body: SerpRequest,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    return await serp_service.buscar_candidatos(
        nombre=body.nombre, cargo=body.cargo
    )


# ──────────────────────────────────────────────────────────────
# §4 · Validación profiles
# ──────────────────────────────────────────────────────────────


class ValidateAccountRequest(BaseModel):
    platform: str
    handle: str
    nombre_buscado: str = ""


@router.post(
    "/validate-account",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_validate_account(
    body: ValidateAccountRequest,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    return await validator_service.validar_cuenta(
        platform=body.platform,
        handle=body.handle,
        nombre_buscado=body.nombre_buscado,
    )


# ──────────────────────────────────────────────────────────────
# §5 · Confirmación humana obligatoria (D-23 regla dura)
# ──────────────────────────────────────────────────────────────


class ConfirmAccount(BaseModel):
    platform: str
    handle: str
    confirmed: bool = False


class ConfirmAccountsRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    confirmed: list[ConfirmAccount]


@router.post(
    "/confirm-accounts",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_confirm_accounts(
    body: ConfirmAccountsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await confirmations_service.confirmar_cuentas(
            db,
            dirigente_id=body.dirigente_id,
            confirmed=[c.model_dump() for c in body.confirmed],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ──────────────────────────────────────────────────────────────
# §6 · OAuth stubs (meta/tiktok/youtube · X excluida D-19)
# ──────────────────────────────────────────────────────────────


@oauth_router.get(
    "/init/{platform}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def oauth_init(
    platform: str,
    dirigente_id: int,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    # Bifurcación: si YouTube y OAUTH_YOUTUBE_ENABLED + creds GCP → flow real.
    # Otras plataformas (IG/FB/TT) siguen stub hasta Meta App Review.
    if platform.lower() == "youtube" and youtube_oauth_real.is_enabled():
        try:
            return youtube_oauth_real.build_init_url_real(dirigente_id)
        except youtube_oauth_real.YouTubeOAuthError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        return oauth_service.build_init_url(platform, dirigente_id)
    except oauth_service.OAuthPlatformInvalidaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# GET callback que Google llama tras consent.
# Google envía code+state vía query params en un GET; el handler hace exchange
# y redirige al frontend con success/error. Sin auth porque el flow llega
# desde Google (sin JWT) — la validación legítima es la firma HMAC del `state`
# (B-OAUTH-YT-STATE-1 cerrado vía app.services.oauth_state).
@oauth_router.get("/callback/youtube")
async def oauth_callback_youtube_real(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    dirigente_id: int | None = Query(None),
) -> RedirectResponse:
    # Frontend al que el callback redirige tras exchange. Vercel mientras Coolify
    # se actualiza con el código de PLAN-2026-05-13 (`/dashboard/seguidores`,
    # `/dashboard/onboarding?oauth_success=...`). Cambiar a `crece.mdconsultoria-ti.org`
    # post-deploy de Carlos. Overridable via env `OAUTH_FE_REDIRECT_BASE`.
    import os as _os
    fe_base = _os.environ.get(
        "OAUTH_FE_REDIRECT_BASE",
        "https://frontend-zeta-sepia-46.vercel.app",
    )
    if error:
        return RedirectResponse(
            f"{fe_base}/dashboard/onboarding?oauth_error={error}", status_code=302
        )
    if not code:
        return RedirectResponse(
            f"{fe_base}/dashboard/onboarding?oauth_error=missing_code", status_code=302
        )
    if not youtube_oauth_real.is_enabled():
        raise HTTPException(
            status_code=503, detail="OAuth real YouTube no habilitado"
        )
    # State HMAC-signed (B-OAUTH-YT-STATE-1). Verifica firma + extrae
    # dirigente_id del payload firmado. Wire dirigente_id (Query) NO se usa
    # cuando hay state — eso permitía secuestrar oauth para otro dirigente.
    from app.services.oauth_state import OAuthStateError, verify_state
    if state:
        try:
            dirigente_id = verify_state(state)
        except OAuthStateError as exc:
            return RedirectResponse(
                f"{fe_base}/dashboard/onboarding?oauth_error=invalid_state:{exc}",
                status_code=302,
            )
    if dirigente_id is None:
        return RedirectResponse(
            f"{fe_base}/dashboard/onboarding?oauth_error=missing_dirigente",
            status_code=302,
        )
    try:
        tokens = await youtube_oauth_real.exchange_code_for_tokens(code=code)
        await youtube_oauth_real.persist_callback_real(
            db, dirigente_id=dirigente_id, tokens=tokens
        )
    except youtube_oauth_real.YouTubeOAuthError as exc:
        return RedirectResponse(
            f"{fe_base}/dashboard/onboarding?oauth_error={exc}", status_code=302
        )
    except LookupError as exc:
        return RedirectResponse(
            f"{fe_base}/dashboard/onboarding?oauth_error={exc}", status_code=302
        )
    return RedirectResponse(
        f"{fe_base}/dashboard?oauth_success=youtube", status_code=302
    )


class OAuthCallbackRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    platform_user_id: str | None = None
    platform_username: str | None = None


@oauth_router.post(
    "/callback/{platform}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def oauth_callback(
    platform: str,
    body: OAuthCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        token = await oauth_service.persist_callback_stub(
            db,
            dirigente_id=body.dirigente_id,
            platform=platform,
            platform_user_id=body.platform_user_id,
            platform_username=body.platform_username,
        )
    except oauth_service.OAuthPlatformInvalidaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "dirigente_id": token.dirigente_id,
        "platform": token.platform,
        "is_stub": token.is_stub,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "scopes": token.scopes,
        "status": token.status,
    }


@oauth_router.get(
    "/status/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.VIEWER]))],
)
async def oauth_status(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await oauth_service.listar_status(db, dirigente_id=dirigente_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ──────────────────────────────────────────────────────────────
# §7 · Seed competidores (D-22)
# ──────────────────────────────────────────────────────────────


class CompetidorItem(BaseModel):
    full_name: str = Field(..., min_length=3)
    cargo: str = Field(..., min_length=3)
    partido: str | None = None
    url_ref: str | None = None
    es_piloto: bool | None = False


class CompetidoresRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    competidores: list[CompetidorItem]


@router.post(
    "/competidores",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_competidores(
    body: CompetidoresRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await competidores_service.seed_competidores(
            db,
            dirigente_id=body.dirigente_id,
            competidores=[c.model_dump() for c in body.competidores],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=(404 if isinstance(exc, LookupError) else 422),
            detail=str(exc),
        ) from exc


# ──────────────────────────────────────────────────────────────
# §8 · Seed promesas (D-17)
# ──────────────────────────────────────────────────────────────


class PromesaItem(BaseModel):
    texto_promesa: str = Field(..., min_length=10)
    fecha_compromiso: str | None = None
    evidencia_url: str | None = None


class PromesasRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    promesas: list[PromesaItem]


@router.post(
    "/promesas",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_promesas(
    body: PromesasRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return await promesas_service.bulk_seed_promesas(
            db,
            dirigente_id=body.dirigente_id,
            promesas=[p.model_dump() for p in body.promesas],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=(404 if isinstance(exc, LookupError) else 422),
            detail=str(exc),
        ) from exc


# ──────────────────────────────────────────────────────────────
# §9 · Activación final + trigger Celery scrape_all_profiles
# ──────────────────────────────────────────────────────────────


@router.post(
    "/activate/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_activate(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        result = await activation_service.activar_dirigente(
            db, dirigente_id=dirigente_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not result.get("activated"):
        # Checks fallaron — devolvemos 409 con detalle de missing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=result
        )
    return result


# ──────────────────────────────────────────────────────────────
# §10 · Path-scoped aliases (B-ONBOARDING-FE-BE-MISMATCH-1, 2026-05-16)
#
# El frontend espera `dirigente_id` en URL (más RESTful + multi-tenant scope
# claro). Estos endpoints son los nuevos canónicos. Los legacy quedan
# disponibles como deprecated para retrocompat de sesiones piloto activas
# (recomendación Gemini cross-audit · evita 404 en pestañas cacheadas).
#
# Diferencia clave: aplica `assert_dirigente_access` con el path param,
# bloqueando cross-tenant aunque el body diga otro `dirigente_id`.
# ──────────────────────────────────────────────────────────────


class ProfilePathBody(BaseModel):
    perfil: str = Field(..., min_length=3, max_length=30)


@router.post(
    "/{dirigente_id}/profile",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_profile_scoped(
    dirigente_id: int,
    body: ProfilePathBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    await assert_dirigente_access(db, user, dirigente_id)
    try:
        dirigente = await profile_service.set_perfil(
            db, dirigente_id=dirigente_id, perfil=body.perfil
        )
    except profile_service.PerfilInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "dirigente_id": dirigente.id,
        "perfil_1_5": dirigente.perfil_1_5,
        "full_name": dirigente.full_name,
    }


class ManualAccountsPathBody(BaseModel):
    accounts: list[ManualAccount]


@router.post(
    "/{dirigente_id}/accounts-manual",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_accounts_manual_scoped(
    dirigente_id: int,
    body: ManualAccountsPathBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    await assert_dirigente_access(db, user, dirigente_id)
    try:
        return await accounts_service.persist_manual_accounts(
            db,
            dirigente_id=dirigente_id,
            accounts=[a.model_dump() for a in body.accounts],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class ConfirmAccountsPathBody(BaseModel):
    confirmed: list[ConfirmAccount]


@router.post(
    "/{dirigente_id}/confirm-accounts",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_confirm_accounts_scoped(
    dirigente_id: int,
    body: ConfirmAccountsPathBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    await assert_dirigente_access(db, user, dirigente_id)
    try:
        return await confirmations_service.confirmar_cuentas(
            db,
            dirigente_id=dirigente_id,
            confirmed=[c.model_dump() for c in body.confirmed],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class CompetidoresPathBody(BaseModel):
    competidores: list[CompetidorItem]


@router.post(
    "/{dirigente_id}/competidores",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_competidores_scoped(
    dirigente_id: int,
    body: CompetidoresPathBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    await assert_dirigente_access(db, user, dirigente_id)
    try:
        return await competidores_service.seed_competidores(
            db,
            dirigente_id=dirigente_id,
            competidores=[c.model_dump() for c in body.competidores],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=(404 if isinstance(exc, LookupError) else 422),
            detail=str(exc),
        ) from exc


class PromesasPathBody(BaseModel):
    promesas: list[PromesaItem]


@router.post(
    "/{dirigente_id}/promesas",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def post_promesas_scoped(
    dirigente_id: int,
    body: PromesasPathBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    await assert_dirigente_access(db, user, dirigente_id)
    try:
        return await promesas_service.bulk_seed_promesas(
            db,
            dirigente_id=dirigente_id,
            promesas=[p.model_dump() for p in body.promesas],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=(404 if isinstance(exc, LookupError) else 422),
            detail=str(exc),
        ) from exc
