"""Anti-vanity validator — Sprint S4 T-1.4.

Rechaza recomendaciones que no citan al menos un bloque del diagnóstico
(B01..B18) con evidencia específica. Post-generación post-processor para el
pipeline Plan IA `llm_pipeline.py`.

Regla dura (D-24 bloque 8):
- `evidencia_respaldo.bloques_citados` debe contener ≥ 1 código `B01..B18`.
- Evidencia específica presente: `post_id_referencia` OR `metrica_referencia` OR
  `ventana_temporal` no null/empty.
- `accion_texto` no puede contener patrones vacíos "más X" / "mejor Y" /
  "publica más" / "gana más followers" sin contexto específico adicional.
- Los 5 elementos de anatomía §2.6.7 presentes: tipo, accion_texto,
  ventana_duracion_dias, criterio_exito, principio_conductual.

Si rechaza, retorna feedback estructurado que el pipeline inyecta en el retry
como `{{RETRY_FEEDBACK}}`.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Bloques válidos del diagnóstico (B01..B18). Cualquier otra etiqueta se rechaza.
_BLOQUE_RE = re.compile(r"^B(0[1-9]|1[0-8])$")
_BLOQUE_INLINE_RE = re.compile(r"\bB(0[1-9]|1[0-8])\b")

# Tipos válidos de recomendación (matching recomendaciones_plan_ia.tipo check).
_VALID_TIPOS = frozenset({"start", "stop", "continue"})

# Patrones de vanidad vacía — sin contexto específico se rechazan. Un patrón
# puede aparecer si la acción añade mucho contexto adicional (>30 chars después
# del match).
_VANITY_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bpublica\s+m[aá]s\s+contenido\b", re.IGNORECASE), "publica más contenido"),
    (re.compile(r"\bgana(r)?\s+m[aá]s\s+seguidores\b", re.IGNORECASE), "gana más seguidores"),
    (re.compile(r"\bgana(r)?\s+m[aá]s\s+followers\b", re.IGNORECASE), "gana más followers"),
    (re.compile(r"\bsube\s+m[aá]s\s+stor(ies|ias)\b", re.IGNORECASE), "sube más stories"),
    (re.compile(r"\bmejora(r)?\s+tu\s+narrativa\b", re.IGNORECASE), "mejora tu narrativa"),
    (re.compile(r"\bmejora(r)?\s+tu\s+comunicaci[oó]n\b", re.IGNORECASE), "mejora tu comunicación"),
    (re.compile(r"\bm[aá]s\s+interacci[oó]n\b(?!.{30,})", re.IGNORECASE), "más interacción (sin contexto)"),
    (re.compile(r"\bconecta\s+con\s+tu\s+audiencia\b", re.IGNORECASE), "conecta con tu audiencia"),
    (re.compile(r"\baumenta\s+tu\s+engagement\b(?!.{30,})", re.IGNORECASE), "aumenta tu engagement (sin contexto)"),
)


class AntiVanityValidator:
    """Validador post-generación de recomendaciones Plan IA.

    Uso:
        validator = AntiVanityValidator()
        ok, errors = validator.validate(recomendacion_dict)
        if not ok:
            # re-solicitar al LLM con retry feedback
            ...
    """

    def validate(self, recomendacion: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a single recommendation dict.

        Returns:
            (is_valid, list_of_error_strings)
        """
        errors: list[str] = []

        # 1) Anatomía §2.6.7 — 5 elementos obligatorios
        tipo = recomendacion.get("tipo")
        if tipo not in _VALID_TIPOS:
            errors.append(
                f"'tipo' debe ser uno de {sorted(_VALID_TIPOS)}, recibido: {tipo!r}"
            )

        accion_texto = (recomendacion.get("accion_texto") or "").strip()
        if len(accion_texto) < 40:
            errors.append(
                f"'accion_texto' debe tener ≥40 caracteres (acción específica), "
                f"recibido {len(accion_texto)} chars"
            )

        ventana = recomendacion.get("ventana_duracion_dias")
        if not isinstance(ventana, int) or ventana < 1 or ventana > 180:
            errors.append(
                f"'ventana_duracion_dias' debe ser int entre 1 y 180, recibido: {ventana!r}"
            )

        criterio = recomendacion.get("criterio_exito")
        if not isinstance(criterio, dict) or not criterio:
            errors.append("'criterio_exito' debe ser dict no vacío con metrica/umbral/direccion")
        else:
            # Chequear subcampos mínimos
            for key in ("metrica", "umbral", "direccion"):
                if key not in criterio or criterio[key] in (None, ""):
                    errors.append(f"'criterio_exito.{key}' faltante o vacío")

        principio = (recomendacion.get("principio_conductual") or "").strip()
        if len(principio) < 4:
            errors.append(
                "'principio_conductual' obligatorio — cita una etiqueta "
                "(Kahneman Anchoring, Cialdini Authority, etc.)"
            )

        # 2) Evidencia — cita bloque B01..B18 + evidencia específica
        evidencia = recomendacion.get("evidencia_respaldo") or {}
        if not isinstance(evidencia, dict):
            errors.append("'evidencia_respaldo' debe ser dict")
            evidencia = {}

        bloques_citados = evidencia.get("bloques_citados") or []
        if not isinstance(bloques_citados, list):
            bloques_citados = []

        # Normalizar + deduplicar + validar cada código
        valid_bloques = [b for b in bloques_citados if isinstance(b, str) and _BLOQUE_RE.match(b)]
        if not valid_bloques:
            # Fallback: buscar mención inline en accion_texto (algunos LLM lo mencionan
            # en texto y olvidan popularlo en el dict)
            inline = _BLOQUE_INLINE_RE.findall(accion_texto)
            if not inline:
                errors.append(
                    "'evidencia_respaldo.bloques_citados' debe incluir ≥1 código "
                    "B01..B18 del diagnóstico. Sin cita a bloque, la recomendación "
                    "se considera ruido vanidoso."
                )

        # Evidencia específica: al menos uno de los 3 campos
        has_post = evidencia.get("post_id_referencia") not in (None, 0, "")
        has_metrica = bool((evidencia.get("metrica_referencia") or "").strip()) if isinstance(
            evidencia.get("metrica_referencia"), str
        ) else False
        has_ventana = bool((evidencia.get("ventana_temporal") or "").strip()) if isinstance(
            evidencia.get("ventana_temporal"), str
        ) else False
        if not (has_post or has_metrica or has_ventana):
            errors.append(
                "'evidencia_respaldo' debe incluir al menos uno de: "
                "post_id_referencia, metrica_referencia, ventana_temporal. "
                "Sin evidencia específica no hay anclaje empírico."
            )

        # 3) Anti-vanidad: patrones vacíos en accion_texto
        for pattern, label in _VANITY_PATTERNS:
            m = pattern.search(accion_texto)
            if not m:
                continue
            # Si tras el match quedan menos de 30 chars de contexto, es vanidad.
            tail = accion_texto[m.end() :].strip()
            if len(tail) < 30:
                errors.append(
                    f"'accion_texto' contiene patrón vanidoso '{label}' sin "
                    f"contexto específico suficiente. Reescribe con acción concreta "
                    f"(verbo + objeto + ventana temporal + métrica meta)."
                )

        return (not errors, errors)

    def validate_batch(
        self, recomendaciones: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate a list of recommendations.

        Returns:
            (valid_recomendaciones, rejected_with_reasons)
            rejected_with_reasons = [{"recomendacion": dict, "errores": [str,...]}, ...]
        """
        valid: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for rec in recomendaciones:
            ok, errors = self.validate(rec)
            if ok:
                valid.append(rec)
            else:
                rejected.append({"recomendacion": rec, "errores": errors})
        return valid, rejected

    @staticmethod
    def feedback_for_retry(rejected: list[dict[str, Any]]) -> str:
        """Build a human-readable feedback block for the LLM retry prompt."""
        if not rejected:
            return ""
        lines = [
            "El validador anti-vanidad rechazó algunas recomendaciones del intento "
            "anterior. Corrige los siguientes problemas y regenera TODAS las "
            "recomendaciones con los problemas resueltos:",
            "",
        ]
        for idx, item in enumerate(rejected, 1):
            rec = item.get("recomendacion") or {}
            accion = (rec.get("accion_texto") or "").strip()[:120]
            errores = item.get("errores") or []
            lines.append(f"Recomendación {idx} (\"{accion}...\"):")
            for e in errores:
                lines.append(f"  - {e}")
            lines.append("")
        lines.append(
            "Recuerda: cada recomendación DEBE citar ≥1 bloque B01..B18 en "
            "`evidencia_respaldo.bloques_citados` + al menos uno de "
            "post_id_referencia/metrica_referencia/ventana_temporal. "
            "No repitas patrones de vanidad."
        )
        return "\n".join(lines)
