from __future__ import annotations

from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.campana import Campana, CampanaMensaje, CampanaSegmento
from app.models.canvassing import PuntoRuta, RutaCanvassing
from app.models.ciudadano import Ciudadano
from app.models.contenido import ContenidoGenerado
from app.models.dirigente import Dirigente
from app.models.electoral import IntencionVoto, SeccionElectoral
from app.models.encuesta import Encuesta
from app.models.evento import Evento, EventoAsistente
from app.models.gasto_electoral import AlertaCompliance, GastoElectoral
from app.models.metrica_social import MetricaSocial
from app.models.organizacion import Organizacion
from app.models.plan_ia import PlanIA
from app.models.programa_social import ProgramaBeneficiario, ProgramaSocial
from app.models.social import SentimentAnalysis, SocialPost, SocialProfile
from app.models.solicitud import SeguimientoSolicitud, SolicitudCiudadana
from app.models.user import User
from app.models.voter_score import VoterScore

__all__ = [
    "AlertaCompliance",
    "Campana",
    "CampanaMensaje",
    "CampanaSegmento",
    "Ciudadano",
    "Competidor",
    "CompetidorSocialProfile",
    "ContenidoGenerado",
    "Dirigente",
    "Encuesta",
    "Evento",
    "EventoAsistente",
    "GastoElectoral",
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
]
