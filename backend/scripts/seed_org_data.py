"""
Seed sample posts and demo data for GOB-OAXACA and CDMX-IND orgs.
Idempotent — checks for existing data before inserting.

Run with: docker exec crece-backend python -m scripts.seed_org_data
"""
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.plan_ia import PlanIA, TipoPlan
from app.models.social import (
    Platform,
    PostType,
    SentimentLabel,
    SocialPost,
    SocialProfile,
)

# Sample posts for each new dirigente
DIRIGENTE_POSTS = {
    "Saymi Adriana Pineda Velasco": {
        "platform": Platform.TWITTER,
        "posts": [
            {
                "content": "Oaxaca es un destino turistico de talla mundial. Desde la Secretaria de Turismo trabajamos para que cada visitante viva una experiencia unica y segura. #OaxacaMagico #TurismoOaxaca",
                "sentiment_score": 0.78,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 234,
                "comments": 45,
                "shares": 89,
                "views": 12000,
                "engagement_rate": 4.19,
            },
            {
                "content": "Inauguramos la ruta gastronomica Valles Centrales. 15 comunidades, 15 cocinas tradicionales, un solo camino de sabor. Esto es identidad. #GastronomiaOaxaquena",
                "sentiment_score": 0.85,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 567,
                "comments": 78,
                "shares": 156,
                "views": 25000,
                "engagement_rate": 6.41,
            },
            {
                "content": "Preocupante la baja en turismo internacional este trimestre. Necesitamos replantear la estrategia de promocion en mercados europeos y asiaticos.",
                "sentiment_score": -0.35,
                "sentiment_label": SentimentLabel.NEGATIVE,
                "is_political": True,
                "likes": 89,
                "comments": 34,
                "shares": 23,
                "views": 5600,
                "engagement_rate": 2.61,
            },
        ],
    },
    "Yesenia Nolasco Ramírez": {
        "platform": Platform.FACEBOOK,
        "posts": [
            {
                "content": "Hoy arrancamos el programa de mejoramiento vial en la capital oaxaquena. 23 calles principales seran rehabilitadas. La movilidad es un derecho, no un privilegio.",
                "sentiment_score": 0.72,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 456,
                "comments": 123,
                "shares": 67,
                "views": 35000,
                "engagement_rate": 1.85,
            },
            {
                "content": "Lanzamos la app MueveOaxaca para reporte ciudadano de baches, semaforos y senalizacion. Descargala y ayudanos a mejorar tu ciudad.",
                "sentiment_score": 0.65,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 789,
                "comments": 234,
                "shares": 345,
                "views": 48000,
                "engagement_rate": 2.86,
            },
            {
                "content": "Reconozco que el transporte publico en Oaxaca tiene rezagos graves. No es aceptable que las unidades circulen sin aire acondicionado ni condiciones dignas. Estamos trabajando en ello.",
                "sentiment_score": -0.25,
                "sentiment_label": SentimentLabel.NEGATIVE,
                "is_political": True,
                "likes": 1200,
                "comments": 456,
                "shares": 234,
                "views": 67000,
                "engagement_rate": 2.81,
            },
        ],
    },
    "Gabriela Jiménez Godoy": {
        "platform": Platform.TWITTER,
        "posts": [
            {
                "content": "Desde la Camara de Diputados aprobamos la reforma al articulo 4 constitucional que garantiza el derecho a la vivienda digna. Un paso historico para Mexico.",
                "sentiment_score": 0.82,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 2340,
                "comments": 567,
                "shares": 890,
                "views": 125000,
                "engagement_rate": 3.06,
            },
            {
                "content": "CDMX necesita un plan integral de seguridad que combine prevencion, inteligencia y justicia restaurativa. No mas parches ni cifras maquilladas.",
                "sentiment_score": -0.42,
                "sentiment_label": SentimentLabel.NEGATIVE,
                "is_political": True,
                "likes": 1567,
                "comments": 890,
                "shares": 456,
                "views": 89000,
                "engagement_rate": 3.25,
            },
            {
                "content": "Manana sesion extraordinaria para discutir el presupuesto de egresos. Defenderemos que la educacion y salud sean prioridad, no los megaproyectos faraonicos.",
                "sentiment_score": 0.15,
                "sentiment_label": SentimentLabel.NEUTRAL,
                "is_political": True,
                "likes": 890,
                "comments": 234,
                "shares": 178,
                "views": 45000,
                "engagement_rate": 2.89,
            },
            {
                "content": "Feliz inicio de semana! Hoy acompane a los ninos del DIF CDMX en su festival de primavera. Sus sonrisas son la mejor motivacion para seguir trabajando.",
                "sentiment_score": 0.90,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": False,
                "likes": 3456,
                "comments": 234,
                "shares": 567,
                "views": 178000,
                "engagement_rate": 4.75,
            },
        ],
    },
    "César Cravioto Romero": {
        "platform": Platform.TWITTER,
        "posts": [
            {
                "content": "Como Secretario de Gobierno de la CDMX informo: se activo el protocolo de proteccion civil por lluvias atipicas en 6 alcaldias. Mantenganse informados por canales oficiales.",
                "sentiment_score": 0.10,
                "sentiment_label": SentimentLabel.NEUTRAL,
                "is_political": True,
                "likes": 4567,
                "comments": 890,
                "shares": 2345,
                "views": 234000,
                "engagement_rate": 3.50,
            },
            {
                "content": "Reunion de trabajo con las 16 alcaldias para coordinar el programa de seguridad alimentaria. Ningun nino en CDMX debe irse a dormir con hambre.",
                "sentiment_score": 0.68,
                "sentiment_label": SentimentLabel.POSITIVE,
                "is_political": True,
                "likes": 2345,
                "comments": 456,
                "shares": 678,
                "views": 145000,
                "engagement_rate": 2.40,
            },
            {
                "content": "La oposicion puede criticar todo lo que quiera, pero los hechos hablan: CDMX tiene la menor tasa de desempleo en 10 anos. Eso no se logra con discursos, se logra gobernando.",
                "sentiment_score": -0.15,
                "sentiment_label": SentimentLabel.NEGATIVE,
                "is_political": True,
                "likes": 5678,
                "comments": 2345,
                "shares": 1234,
                "views": 345000,
                "engagement_rate": 2.68,
            },
        ],
    },
}

# Sample plans for each org
ORG_PLANS = {
    "gob-oaxaca": {
        "dirigente_name": "Saymi Adriana Pineda Velasco",
        "plan": """# Plan de Posicionamiento Digital — 90 Dias
## Saymi Pineda Velasco | Secretaria de Turismo Oaxaca

### Diagnostico Actual
- IPD estimado: 5.2/10 (moderado)
- Presencia en 2 plataformas (Twitter + Instagram)
- Engagement promedio: 4.4% (bueno en Instagram)
- Sin presencia en TikTok ni YouTube

### Fase 1: Consolidacion (Dias 1-30)
1. **Optimizar perfil** Instagram con bio institucional + linktree
2. **Calendario editorial**: 4 posts/semana con contenido turistico de Oaxaca
3. **Hashtags propios**: #OaxacaMagico #TurismoOaxaca
4. **Stories diarios** mostrando destinos turisticos

### Fase 2: Expansion (Dias 31-60)
1. **Crear TikTok** con reels de gastronomia y tradiciones
2. **Colaboraciones** con influencers de viajes
3. **Contenido bilingual** para mercado internacional
4. **Live semanal** desde destinos turisticos

### Fase 3: Liderazgo (Dias 61-90)
1. **YouTube** con mini-documentales de comunidades
2. **Medicion** de impacto en reservaciones turisticas
3. **Meta**: IPD 7.0/10, +5K seguidores Instagram

### KPIs
| Metrica | Actual | Meta 90 dias |
|---------|--------|-------------|
| IPD | 5.2 | 7.0 |
| Seguidores totales | ~20,800 | ~35,000 |
| Plataformas activas | 2 | 4 |
| Engagement promedio | 4.4% | 5.5% |
""",
    },
    "cdmx-ind": {
        "dirigente_name": "Gabriela Jiménez Godoy",
        "plan": """# Plan de Estrategia Digital — 90 Dias
## Gabriela Jimenez Godoy | Diputada Federal

### Diagnostico Actual
- IPD estimado: 7.1/10 (alto)
- Presencia en 4 plataformas (Twitter, Instagram, Facebook, TikTok)
- Audiencia total: ~180K seguidores
- Engagement: 3.5% promedio (solido)

### Fase 1: Autoridad Tematica (Dias 1-30)
1. **Posicionar** como experta en vivienda y educacion
2. **Thread semanal** en Twitter con datos duros del presupuesto
3. **Infografias** compartibles sobre reformas aprobadas
4. **Q&A mensual** en Instagram Live

### Fase 2: Amplificacion (Dias 31-60)
1. **Podcast corto** (5 min) sobre trabajo legislativo
2. **Alianzas** con periodistas especializados en politica
3. **TikTok educativo**: "Un minuto en la Camara"
4. **Newsletter** quincenal con resumen legislativo

### Fase 3: Consolidacion (Dias 61-90)
1. **YouTube Shorts** con clips de tribuna
2. **Cross-posting** automatizado entre plataformas
3. **Meta**: IPD 8.5/10, +30K seguidores totales

### KPIs
| Metrica | Actual | Meta 90 dias |
|---------|--------|-------------|
| IPD | 7.1 | 8.5 |
| Seguidores totales | ~180,000 | ~210,000 |
| Posts/semana | ~8 | ~15 |
| Engagement promedio | 3.5% | 4.5% |
""",
    },
}


async def seed_org_data():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        now = datetime.now(UTC)
        posts_created = 0
        plans_created = 0

        # ── Create sample posts for each dirigente ────────────────
        for dirigente_name, config in DIRIGENTE_POSTS.items():
            # Find dirigente
            result = await session.execute(
                select(Dirigente).where(Dirigente.full_name == dirigente_name)
            )
            dirigente = result.scalar_one_or_none()
            if not dirigente:
                print(f"  SKIP: Dirigente {dirigente_name} not found")
                continue

            # Find the matching profile
            result = await session.execute(
                select(SocialProfile).where(
                    SocialProfile.dirigente_id == dirigente.id,
                    SocialProfile.platform == config["platform"],
                )
            )
            profile = result.scalar_one_or_none()
            if not profile:
                print(f"  SKIP: No {config['platform'].value} profile for {dirigente_name}")
                continue

            # Check existing posts
            existing = await session.execute(
                select(SocialPost.id).where(SocialPost.profile_id == profile.id)
            )
            if existing.scalars().first():
                print(f"  = Posts already exist for {dirigente_name} ({config['platform'].value})")
                continue

            # Create posts
            for i, post_data in enumerate(config["posts"]):
                post = SocialPost(
                    profile_id=profile.id,
                    platform_post_id=f"{config['platform'].value}_{dirigente.id}_{i+1:03d}",
                    content=post_data["content"],
                    post_type=PostType.TEXT,
                    published_at=now - timedelta(days=i + 1),
                    likes=post_data["likes"],
                    comments=post_data["comments"],
                    shares=post_data["shares"],
                    views=post_data["views"],
                    engagement_rate=post_data["engagement_rate"],
                    sentiment_score=post_data["sentiment_score"],
                    sentiment_label=post_data["sentiment_label"],
                    is_political=post_data["is_political"],
                    scraped_at=now,
                )
                session.add(post)
                posts_created += 1

            print(f"  + {len(config['posts'])} posts for {dirigente_name}")

        # ── Create sample plans for each org ──────────────────────
        for org_slug, plan_config in ORG_PLANS.items():
            result = await session.execute(
                select(Dirigente).where(
                    Dirigente.full_name == plan_config["dirigente_name"]
                )
            )
            dirigente = result.scalar_one_or_none()
            if not dirigente:
                print(f"  SKIP: Dirigente {plan_config['dirigente_name']} not found for plan")
                continue

            # Check existing plan
            existing = await session.execute(
                select(PlanIA.id).where(PlanIA.dirigente_id == dirigente.id)
            )
            if existing.scalars().first():
                print(f"  = Plan already exists for {dirigente.full_name}")
                continue

            # Find admin user for generado_por_id
            from app.models.user import Role, User
            admin_result = await session.execute(
                select(User.id).where(User.role == Role.ADMIN).limit(1)
            )
            admin_id = admin_result.scalar()

            plan = PlanIA(
                dirigente_id=dirigente.id,
                tipo=TipoPlan.CONSOLIDACION,
                contenido=plan_config["plan"],
                modelo_ia="gemma3:12b",
                prompt_usado="Genera un plan de posicionamiento digital de 90 dias...",
                datos_entrada={
                    "ipd_score": 5.2 if "oaxaca" in org_slug else 7.1,
                    "platforms": ["twitter", "instagram"],
                },
                generado_por_id=admin_id or 1,
                aprobado=False,
            )
            session.add(plan)
            plans_created += 1
            print(f"  + Plan IA for {dirigente.full_name} ({org_slug})")

        await session.commit()

        # Summary
        total_posts = (await session.execute(text("SELECT count(*) FROM social_posts"))).scalar()
        total_plans = (await session.execute(text("SELECT count(*) FROM planes_ia"))).scalar()
        print("\n✅ Org data seed completado!")
        print(f"   Posts created this run: {posts_created}")
        print(f"   Plans created this run: {plans_created}")
        print(f"   Total posts in DB: {total_posts}")
        print(f"   Total plans in DB: {total_plans}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_org_data())
