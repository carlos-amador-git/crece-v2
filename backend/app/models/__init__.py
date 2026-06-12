from __future__ import annotations

from app.models.alcaldia import AlcaldiaCDMX
from app.models.alerta_crisis import AlertaCrisis
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.campaign_integration import Campaign
from app.models.campana import Campana, CampanaMensaje, CampanaSegmento
from app.models.canvassing import PuntoRuta, RutaCanvassing
from app.models.ciudadano import Ciudadano
from app.models.compliance_purge_audit import CompliancePurgeAudit
from app.models.competitor_profile import (
    CompetitorMetricsMonthly,
    CompetitorPost,
    CompetitorProfile,
)
from app.models.contenido import ContenidoGenerado
from app.models.contenido_pieza import ContenidoPieza
from app.models.crm_interaccion import CrmInteraccion
from app.models.dirigente import Dirigente
from app.models.efemeride import Efemeride, EfemerideAmbito, EfemerideTipo, EfemerideViralidad
from app.models.electoral import IntencionVoto, SeccionElectoral
from app.models.encuesta import Encuesta
from app.models.evento import Evento, EventoAsistente
from app.models.follower import FollowerEngagement, SocialFollower
from app.models.gasto_electoral import AlertaCompliance, GastoElectoral
from app.models.hitl_audit import HitlEditsLog
from app.models.ia_content_registry import IaContentRegistry
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.models.legacy import CiudadanoLegacy, PromotorLegacy
from app.models.llm_health_log import LLMHealthLog
from app.models.metrica_social import MetricaSocial
from app.models.oauth_token import OAuthPlatform, OAuthTokenByPlatform, OAuthTokenStatus
from app.models.organizacion import Organizacion
from app.models.plan_ia import PlanIA
from app.models.programa_social import ProgramaBeneficiario, ProgramaSocial
from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.social import SentimentAnalysis, SocialPost, SocialProfile
from app.models.solicitud import SeguimientoSolicitud, SolicitudCiudadana
from app.models.topic_trend import TopicTrend
from app.models.unidad_territorial import UnidadTerritorial
from app.models.user import User
from app.models.voter_score import VoterScore
from app.models.voter_score_integration import VoterScoreIntegration
from app.models.watched_profile import WatchedLikeEvent, WatchedProfile, compute_watched_hash

__all__ = [
    "AlcaldiaCDMX",
    "AlertaCompliance",
    "AlertaCrisis",
    "ApiKey",
    "AuditLog",
    "Campaign",
    "Campana",
    "CampanaMensaje",
    "CampanaSegmento",
    "Ciudadano",
    "CiudadanoLegacy",
    "CompetitorMetricsMonthly",
    "CompetitorPost",
    "CompetitorProfile",
    "CompliancePurgeAudit",
    "ContenidoGenerado",
    "ContenidoPieza",
    "CrmInteraccion",
    "Dirigente",
    "Efemeride",
    "EfemerideAmbito",
    "EfemerideTipo",
    "EfemerideViralidad",
    "Encuesta",
    "Evento",
    "EventoAsistente",
    "FollowerEngagement",
    "GastoElectoral",
    "HitlEditsLog",
    "IaContentRegistry",
    "IngestJob",
    "IngestJobStatus",
    "IntencionVoto",
    "LLMHealthLog",
    "MetricaSocial",
    "OAuthPlatform",
    "OAuthTokenByPlatform",
    "OAuthTokenStatus",
    "Organizacion",
    "PlanIA",
    "ProgramaBeneficiario",
    "ProgramaSocial",
    "PromesaDirigente",
    "PromesaEstado",
    "PromotorLegacy",
    "PuntoRuta",
    "RecomendacionPlanIA",
    "RutaCanvassing",
    "SeccionElectoral",
    "SeguimientoSolicitud",
    "SentimentAnalysis",
    "SocialFollower",
    "SocialPost",
    "SocialProfile",
    "SolicitudCiudadana",
    "TopicTrend",
    "UnidadTerritorial",
    "User",
    "VoterScore",
    "VoterScoreIntegration",
    "WatchedLikeEvent",
    "WatchedProfile",
    "compute_watched_hash",
]
