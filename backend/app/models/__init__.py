from __future__ import annotations

from app.models.alcaldia import AlcaldiaCDMX
from app.models.alerta_crisis import AlertaCrisis
from app.models.api_key import ApiKey
from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.campana import Campana, CampanaMensaje, CampanaSegmento
from app.models.campaign_integration import Campaign
from app.models.canvassing import PuntoRuta, RutaCanvassing
from app.models.ciudadano import Ciudadano
from app.models.contenido import ContenidoGenerado
from app.models.contenido_pieza import ContenidoPieza
from app.models.crm_interaccion import CrmInteraccion
from app.models.dirigente import Dirigente
from app.models.electoral import IntencionVoto, SeccionElectoral
from app.models.encuesta import Encuesta
from app.models.evento import Evento, EventoAsistente
from app.models.gasto_electoral import AlertaCompliance, GastoElectoral
from app.models.ia_content_registry import IaContentRegistry
from app.models.metrica_social import MetricaSocial
from app.models.organizacion import Organizacion
from app.models.plan_ia import PlanIA
from app.models.programa_social import ProgramaBeneficiario, ProgramaSocial
from app.models.social import SentimentAnalysis, SocialPost, SocialProfile
from app.models.solicitud import SeguimientoSolicitud, SolicitudCiudadana
from app.models.user import User
from app.models.voter_score import VoterScore
from app.models.voter_score_integration import VoterScoreIntegration

__all__ = [
    "AlcaldiaCDMX",
    "AlertaCompliance",
    "AlertaCrisis",
    "ApiKey",
    "Campana",
    "Campaign",
    "CampanaMensaje",
    "CampanaSegmento",
    "Ciudadano",
    "Competidor",
    "CompetidorSocialProfile",
    "ContenidoGenerado",
    "ContenidoPieza",
    "CrmInteraccion",
    "Dirigente",
    "Encuesta",
    "Evento",
    "EventoAsistente",
    "GastoElectoral",
    "IaContentRegistry",
    "IntencionVoto",
    "MetricaSocial",
    "Organizacion",
    "PlanIA",
    "PuntoRuta",
    "ProgramaBeneficiario",
    "ProgramaSocial",
    "RutaCanvassing",
    "SeccionElectoral",
    "SeguimientoSolicitud",
    "SentimentAnalysis",
    "SocialPost",
    "SocialProfile",
    "SolicitudCiudadana",
    "User",
    "VoterScore",
    "VoterScoreIntegration",
]
