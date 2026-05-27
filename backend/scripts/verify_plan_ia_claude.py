"""Verificación end-to-end del pipeline Plan IA migrado a Claude.

Corre el PlanIAPipeline real contra un dirigente real (Piña por defecto),
usando Claude (sin Ollama). NO mockea: hace la llamada real a la Claude API.

Por defecto es **dry-run** — ejecuta cargar diagnóstico → render prompt →
Claude → parse → AntiVanityValidator, pero NO persiste recomendaciones.
Con `--persist` corre el flujo completo `generate()` que sí escribe filas
`recomendaciones_plan_ia` (estado='propuesta').

Uso (dentro del contenedor backend en staging):
    python backend/scripts/verify_plan_ia_claude.py --name "piña"
    python backend/scripts/verify_plan_ia_claude.py --dirigente-id 3 --persist

Args:
    --name SUBSTR       busca dirigente por nombre (ilike). Default "piña".
    --dirigente-id ID   usa un dirigente por id (ignora --name).
    --org-id N          org scope (default: el org del dirigente, o 1).
    --persist           persiste las recomendaciones válidas (flujo completo).

Principios MD:
- NO mockear. Si falta CLAUDE_API_KEY o el modelo falla, reporta blocker y sale != 0.
- Correr el script ES la verificación (CLAUDE.md Regla 2/5).

Exit codes: 0 = ≥1 recomendación válida; 1 = sin válidas / blocker.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Permite ejecutar el script sin instalar el paquete (`python scripts/...`)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import async_session_factory  # noqa: E402
from app.models.dirigente import Dirigente  # noqa: E402
from app.services.plan_ia.llm_pipeline import (  # noqa: E402
    _classify_perfil_1_5,
    _load_diagnostico_18_bloques,
    _load_prompt_body,
    default_pipeline,
)
from app.services.plan_ia.rag_memory import (  # noqa: E402
    fetch_historico,
    format_historico_for_prompt,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("verify_plan_ia_claude")


async def _pick_dirigente(
    session: AsyncSession, *, dirigente_id: int | None, name: str
) -> Dirigente:
    """Selecciona dirigente por id explícito o por nombre (ilike)."""
    if dirigente_id is not None:
        d = await session.get(Dirigente, dirigente_id)
        if d is None:
            raise RuntimeError(f"Dirigente id={dirigente_id} no existe")
        return d
    d = (
        await session.execute(
            select(Dirigente).where(Dirigente.full_name.ilike(f"%{name}%")).limit(1)
        )
    ).scalar_one_or_none()
    if d is not None:
        return d
    d = (await session.execute(select(Dirigente).limit(1))).scalar_one_or_none()
    if d is None:
        raise RuntimeError("No hay dirigentes en la DB para verificar")
    logger.warning("Sin match para '%s'; usando fallback id=%d (%s)", name, d.id, d.full_name)
    return d


def _print_recs(titulo: str, items: list[dict]) -> None:
    """Imprime recomendaciones, tolerante a las 3 formas posibles:
    raw del LLM, persistida (created_ids), o rechazada
    ({"recomendacion": {...}, "errores": [...]})."""
    print(f"\n--- {titulo} ({len(items)}) ---")
    for i, item in enumerate(items, 1):
        rec = item.get("recomendacion", item)  # desenvuelve la forma rechazada
        errores = item.get("errores")
        accion = (rec.get("accion_texto") or "").strip()
        bloques = rec.get("bloques_citados") or (
            rec.get("evidencia_respaldo") or {}
        ).get("bloques_citados", [])
        rid = rec.get("id")
        head = f"[{i}]" + (f" id={rid}" if rid else "")
        print(f"{head} tipo={rec.get('tipo')} principio={rec.get('principio_conductual')}")
        print(f"    acción: {accion[:280]}")
        if rec.get("criterio_exito") is not None:
            print(f"    criterio_exito: {rec.get('criterio_exito')}")
        print(f"    bloques_citados: {bloques}")
        if errores:
            print(f"    ❌ errores: {errores}")


async def _run(args: argparse.Namespace) -> int:
    if not settings.CLAUDE_API_KEY:
        logger.error("BLOCKER: CLAUDE_API_KEY no configurada en el env del proceso.")
        return 1

    print("=" * 70)
    print("VERIFICACIÓN Plan IA → Claude")
    print(f"  provider activo : {default_pipeline.provider}")
    print(f"  modelo activo   : {default_pipeline.active_model}")
    print(f"  modo            : {'PERSIST (escribe DB)' if args.persist else 'dry-run (sin escritura)'}")
    print("=" * 70)

    if default_pipeline.provider != "claude":
        logger.warning(
            "El pipeline NO está en Claude (provider=%s). Revisa AI_PROVIDER/OLLAMA_ENABLED.",
            default_pipeline.provider,
        )

    async with async_session_factory() as session:
        dirigente = await _pick_dirigente(
            session, dirigente_id=args.dirigente_id, name=args.name
        )
        org_id = args.org_id or dirigente.org_id or 1
        print(f"\nDirigente: id={dirigente.id} · {dirigente.full_name} · org_id={org_id}")
        print(f"Cargo: {dirigente.cargo} · perfil_1.5: {_classify_perfil_1_5(dirigente)}")

        if args.persist:
            result = await default_pipeline.generate(session, dirigente.id, org_id)
            if result.get("error"):
                logger.error("BLOCKER: %s", result["error"])
                return 1
            print(f"\npipeline meta: {result['pipeline']}")
            _print_recs("RECOMENDACIONES CREADAS (persistidas)", result["recomendaciones_creadas"])
            _print_recs("RECHAZADAS", result.get("rechazadas", []))
            valid_count = result["pipeline"]["valid_count"]
        else:
            # Dry-run: ejecuta el path real sin persistir
            bloques = await _load_diagnostico_18_bloques(session, dirigente.id, org_id)
            historico = await fetch_historico(session, dirigente.id, org_id, limit=10)
            historico_json = format_historico_for_prompt(historico)
            prompt_body = _load_prompt_body()
            perfil = _classify_perfil_1_5(dirigente)

            valid, rejected, last_raw = await default_pipeline._generate_and_validate(
                dirigente=dirigente,
                bloques=bloques,
                historico_json=historico_json,
                perfil_1_5=perfil,
                prompt_body=prompt_body,
            )
            print(f"\nresultado: válidas={len(valid)} rechazadas={len(rejected)}")
            _print_recs("RECOMENDACIONES VÁLIDAS", valid)
            _print_recs("RECHAZADAS", rejected)
            print(f"\nraw_tail (últimos 400 chars de la respuesta Claude):\n{(last_raw or '')[-400:]}")
            valid_count = len(valid)

    print("\n" + "=" * 70)
    if valid_count > 0:
        print(f"✅ PASS — {valid_count} recomendación(es) válida(s) generada(s) con Claude")
        return 0
    print("❌ FAIL — 0 recomendaciones válidas (revisa logs / prompt / respuesta)")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica el pipeline Plan IA migrado a Claude")
    parser.add_argument("--name", default="piña", help="busca dirigente por nombre (ilike)")
    parser.add_argument("--dirigente-id", type=int, default=None, help="usa un dirigente por id")
    parser.add_argument("--org-id", type=int, default=None, help="org scope (default: el del dirigente)")
    parser.add_argument("--persist", action="store_true", help="persiste recomendaciones (flujo completo)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
