"""
Seed script for CRECE v2.0 — populates database with initial data.
Run with: python -m scripts.seed
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.organizacion import Organizacion
from app.models.user import User, Role
from app.models.dirigente import Dirigente
from app.models.social import SocialProfile, SocialPost, Platform, PostType, SentimentLabel
from app.models.electoral import SeccionElectoral, IntencionVoto
from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.plan_ia import PlanIA, TipoPlan
from app.models.ciudadano import Ciudadano, RangoEdad, Genero, NivelInteres
from app.models.evento import Evento, EventoAsistente, TipoEvento, EstadoEvento
from app.models.programa_social import ProgramaSocial, ProgramaBeneficiario, NivelGobierno


async def seed():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── Organización raíz (D-DX-01 fix) ────────────────────────
        # El endpoint POST /api/v1/api-keys requiere current_user.org_id
        # no NULL (modelo ApiKey.org_id es NOT NULL con FK a organizaciones).
        # Sin este bootstrap, `make reset-db && make seed` dejaba users con
        # org_id=NULL y cualquier creación de API key reventaba con 500.
        org_mc = Organizacion(
            nombre="Movimiento Ciudadano CDMX",
            slug="mc-cdmx",
            tipo="PARTIDO",
        )
        session.add(org_mc)
        await session.flush()

        # ── Users (todos scopados a la org raíz) ──────────────────
        admin = User(
            email="admin@consultoriamd.com",
            hashed_password=hash_password("crece2026!"),
            full_name="Marx Chávez",
            role=Role.ADMIN,
            is_active=True,
            org_id=org_mc.id,
        )
        analyst = User(
            email="analista@consultoriamd.com",
            hashed_password=hash_password("analista2026!"),
            full_name="Ana García",
            role=Role.ANALYST,
            is_active=True,
            org_id=org_mc.id,
        )
        field_op = User(
            email="campo@consultoriamd.com",
            hashed_password=hash_password("campo2026!"),
            full_name="Carlos López",
            role=Role.FIELD_OPERATOR,
            is_active=True,
            org_id=org_mc.id,
        )
        # Demo users for dirigentes (login page quick access)
        user_pina = User(
            email="pina@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="Alejandro Piña Medina",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_mc.id,
        )
        user_solano = User(
            email="solano@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="Rafael Solano Pérez",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_mc.id,
        )
        session.add_all([admin, analyst, field_op, user_pina, user_solano])
        await session.flush()

        # ── Organizaciones adicionales (Multi-Tenant) ─────────────
        org_oaxaca = Organizacion(
            nombre="Gobierno Oaxaca",
            slug="gob-oaxaca",
            tipo="GOBIERNO",
            estado="Oaxaca",
            config={"is_demo": True, "has_synthetic_data": True},
        )
        org_cdmx_ind = Organizacion(
            nombre="CDMX Independiente",
            slug="cdmx-ind",
            tipo="GOBIERNO",
            estado="Ciudad de México",
            config={"is_demo": True, "has_synthetic_data": True},
        )
        session.add_all([org_oaxaca, org_cdmx_ind])
        await session.flush()

        # ── Dirigentes MC CDMX ────────────────────────────────────
        pina = Dirigente(
            full_name="Alejandro Piña Medina",
            cargo="Coordinador Comisión Operativa Estatal",
            partido="MC",
            estado="Ciudad de México",
            municipio="CDMX",
            seccion_electoral="0901",
            org_id=org_mc.id,
        )
        solano = Dirigente(
            full_name="Rafael Solano Pérez",
            cargo="Miembro Comisión Estatal / Analista La Razón",
            partido="MC",
            estado="Ciudad de México",
            municipio="CDMX",
            seccion_electoral="0905",
            org_id=org_mc.id,
        )
        session.add_all([pina, solano])
        await session.flush()

        # Link demo users to dirigentes
        user_pina.dirigente_id = pina.id
        user_solano.dirigente_id = solano.id
        await session.flush()

        # ── Dirigentes GOB-OAXACA ─────────────────────────────────
        pineda = Dirigente(
            full_name="Saymi Adriana Pineda Velasco",
            cargo="Secretaria de Turismo Oaxaca",
            partido="MORENA",
            estado="Oaxaca",
            municipio="Oaxaca de Juárez",
            org_id=org_oaxaca.id,
        )
        nolasco = Dirigente(
            full_name="Yesenia Nolasco Ramírez",
            cargo="Secretaria de Movilidad (SEMOVI) Oaxaca",
            partido="MORENA",
            estado="Oaxaca",
            municipio="Oaxaca de Juárez",
            org_id=org_oaxaca.id,
        )
        session.add_all([pineda, nolasco])
        await session.flush()

        # ── Dirigentes CDMX-IND ───────────────────────────────────
        jimenez = Dirigente(
            full_name="Gabriela Jiménez Godoy",
            cargo="Diputada Federal, Vicecoordinadora",
            partido="MORENA",
            estado="Ciudad de México",
            municipio="CDMX",
            org_id=org_cdmx_ind.id,
        )
        cravioto = Dirigente(
            full_name="César Cravioto Romero",
            cargo="Secretario de Gobierno CDMX",
            partido="MORENA",
            estado="Ciudad de México",
            municipio="CDMX",
            org_id=org_cdmx_ind.id,
        )
        session.add_all([jimenez, cravioto])
        await session.flush()

        # ── Users para nuevas orgs ────────────────────────────────
        user_pineda = User(
            email="pineda@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="Saymi Pineda Velasco",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_oaxaca.id,
            dirigente_id=pineda.id,
        )
        user_nolasco = User(
            email="nolasco@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="Yesenia Nolasco Ramírez",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_oaxaca.id,
            dirigente_id=nolasco.id,
        )
        user_jimenez = User(
            email="jimenez@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="Gabriela Jiménez Godoy",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_cdmx_ind.id,
            dirigente_id=jimenez.id,
        )
        user_cravioto = User(
            email="cravioto@crece.mx",
            hashed_password=hash_password("demo2026!"),
            full_name="César Cravioto Romero",
            role=Role.VIEWER,
            is_active=True,
            org_id=org_cdmx_ind.id,
            dirigente_id=cravioto.id,
        )
        session.add_all([user_pineda, user_nolasco, user_jimenez, user_cravioto])
        await session.flush()

        # ── Social Profiles: Piña ─────────────────────────────────
        pina_twitter = SocialProfile(
            dirigente_id=pina.id,
            platform=Platform.TWITTER,
            handle="@Alejandro_Pinha",
            url="https://x.com/Alejandro_Pinha",
            followers_count=3100,
            following_count=1200,
            posts_count=4500,
        )
        pina_instagram = SocialProfile(
            dirigente_id=pina.id,
            platform=Platform.INSTAGRAM,
            handle="@alejandro.pinha",
            url="https://instagram.com/alejandro.pinha",
            followers_count=2231,
            following_count=890,
            posts_count=531,
        )
        pina_facebook = SocialProfile(
            dirigente_id=pina.id,
            platform=Platform.FACEBOOK,
            handle="alejandropinamedina",
            url="https://facebook.com/alejandropinamedina",
            followers_count=1800,
            following_count=0,
            posts_count=320,
        )

        # ── Social Profiles: Solano ───────────────────────────────
        solano_instagram = SocialProfile(
            dirigente_id=solano.id,
            platform=Platform.INSTAGRAM,
            handle="@rafasolanoperez",
            url="https://instagram.com/rafasolanoperez",
            followers_count=450,
            following_count=300,
            posts_count=85,
        )
        solano_linkedin = SocialProfile(
            dirigente_id=solano.id,
            platform=Platform.TWITTER,  # closest mapping
            handle="@rafasolanoperez",
            url="https://x.com/rafasolanoperez",
            followers_count=170,
            following_count=200,
            posts_count=50,
        )

        # ── Social Profiles: Pineda (Oaxaca) ─────────────────────
        pineda_twitter = SocialProfile(
            dirigente_id=pineda.id,
            platform=Platform.TWITTER,
            handle="@saymipinedav",
            url="https://x.com/saymipinedav",
            followers_count=8800,
            following_count=1500,
            posts_count=3200,
        )
        pineda_instagram = SocialProfile(
            dirigente_id=pineda.id,
            platform=Platform.INSTAGRAM,
            handle="@saymipinedavelasco",
            url="https://instagram.com/saymipinedavelasco",
            followers_count=12000,
            following_count=950,
            posts_count=680,
        )

        # ── Social Profiles: Nolasco (Oaxaca) ────────────────────
        nolasco_twitter = SocialProfile(
            dirigente_id=nolasco.id,
            platform=Platform.TWITTER,
            handle="@Yes_Nolasco",
            url="https://x.com/Yes_Nolasco",
            followers_count=5200,
            following_count=890,
            posts_count=2100,
        )
        nolasco_facebook = SocialProfile(
            dirigente_id=nolasco.id,
            platform=Platform.FACEBOOK,
            handle="YesNolasco",
            url="https://facebook.com/YesNolasco",
            followers_count=32000,
            following_count=0,
            posts_count=1500,
        )

        # ── Social Profiles: Jiménez (CDMX-IND) ─────────────────
        jimenez_twitter = SocialProfile(
            dirigente_id=jimenez.id,
            platform=Platform.TWITTER,
            handle="@GabyJimenezMX",
            url="https://x.com/GabyJimenezMX",
            followers_count=45000,
            following_count=2300,
            posts_count=18000,
        )
        jimenez_instagram = SocialProfile(
            dirigente_id=jimenez.id,
            platform=Platform.INSTAGRAM,
            handle="@gabyjimenezgo",
            url="https://instagram.com/gabyjimenezgo",
            followers_count=28000,
            following_count=1200,
            posts_count=950,
        )
        jimenez_facebook = SocialProfile(
            dirigente_id=jimenez.id,
            platform=Platform.FACEBOOK,
            handle="GabyJimenezGo",
            url="https://facebook.com/GabyJimenezGo",
            followers_count=92000,
            following_count=0,
            posts_count=4200,
        )
        jimenez_tiktok = SocialProfile(
            dirigente_id=jimenez.id,
            platform=Platform.TIKTOK,
            handle="@gabyjimenezmx",
            url="https://tiktok.com/@gabyjimenezmx",
            followers_count=15000,
            following_count=100,
            posts_count=320,
        )

        # ── Social Profiles: Cravioto (CDMX-IND) ────────────────
        cravioto_twitter = SocialProfile(
            dirigente_id=cravioto.id,
            platform=Platform.TWITTER,
            handle="@craviotocesar",
            url="https://x.com/craviotocesar",
            followers_count=67000,
            following_count=3100,
            posts_count=25000,
        )
        cravioto_facebook = SocialProfile(
            dirigente_id=cravioto.id,
            platform=Platform.FACEBOOK,
            handle="craviotocesar",
            url="https://facebook.com/craviotocesar",
            followers_count=48000,
            following_count=0,
            posts_count=3800,
        )

        session.add_all([
            pina_twitter, pina_instagram, pina_facebook,
            solano_instagram, solano_linkedin,
            pineda_twitter, pineda_instagram,
            nolasco_twitter, nolasco_facebook,
            jimenez_twitter, jimenez_instagram, jimenez_facebook, jimenez_tiktok,
            cravioto_twitter, cravioto_facebook,
        ])
        await session.flush()

        # ── Sample Posts: Piña Twitter ────────────────────────────
        now = datetime.utcnow()
        sample_posts = [
            SocialPost(
                profile_id=pina_twitter.id,
                platform_post_id="tw_pina_001",
                content="La Ciudad de México necesita un transporte digno. Desde @MovCiudadanoCMX seguimos trabajando por soluciones reales. #CDMX #TransporteDigno",
                post_type=PostType.TEXT,
                published_at=now - timedelta(days=1),
                likes=45,
                comments=8,
                shares=12,
                views=2300,
                engagement_rate=2.82,
                sentiment_score=0.72,
                sentiment_label=SentimentLabel.POSITIVE,
                is_political=True,
            ),
            SocialPost(
                profile_id=pina_twitter.id,
                platform_post_id="tw_pina_002",
                content="La inseguridad en CDMX no se resuelve con discursos. Se resuelve con presupuesto, coordinación y voluntad política. El gobierno actual nos debe respuestas.",
                post_type=PostType.TEXT,
                published_at=now - timedelta(days=3),
                likes=89,
                comments=23,
                shares=34,
                views=5100,
                engagement_rate=2.86,
                sentiment_score=-0.45,
                sentiment_label=SentimentLabel.NEGATIVE,
                is_political=True,
            ),
            SocialPost(
                profile_id=pina_twitter.id,
                platform_post_id="tw_pina_003",
                content="Gran jornada de afiliación en Iztapalapa. MC crece porque la ciudadanía quiere opciones reales, no promesas vacías. 🍊",
                post_type=PostType.TEXT,
                published_at=now - timedelta(days=5),
                likes=67,
                comments=15,
                shares=28,
                views=3800,
                engagement_rate=2.89,
                sentiment_score=0.85,
                sentiment_label=SentimentLabel.POSITIVE,
                is_political=True,
            ),
            SocialPost(
                profile_id=pina_instagram.id,
                platform_post_id="ig_pina_001",
                content="Recorrido por la colonia Roma. Escuchando a los vecinos, entendiendo sus problemas. Así se construye ciudadanía. #MovimientoCiudadano",
                post_type=PostType.IMAGE,
                published_at=now - timedelta(days=2),
                likes=156,
                comments=12,
                shares=5,
                views=1800,
                engagement_rate=7.74,
                sentiment_score=0.65,
                sentiment_label=SentimentLabel.POSITIVE,
                is_political=True,
            ),
            SocialPost(
                profile_id=pina_facebook.id,
                platform_post_id="fb_pina_001",
                content="Hoy presentamos nuestra propuesta de movilidad sustentable para la CDMX en el foro organizado por la sociedad civil. El futuro es naranja.",
                post_type=PostType.TEXT,
                published_at=now - timedelta(days=4),
                likes=22,
                comments=4,
                shares=3,
                views=800,
                engagement_rate=1.61,
                sentiment_score=0.55,
                sentiment_label=SentimentLabel.POSITIVE,
                is_political=True,
            ),
        ]
        session.add_all(sample_posts)

        # ── Sample Posts: Solano ──────────────────────────────────
        solano_posts = [
            SocialPost(
                profile_id=solano_instagram.id,
                platform_post_id="ig_solano_001",
                content="Fin de semana en familia. A veces hay que desconectarse para reconectarse con lo que importa.",
                post_type=PostType.IMAGE,
                published_at=now - timedelta(days=2),
                likes=45,
                comments=8,
                shares=0,
                views=320,
                engagement_rate=11.76,
                sentiment_score=0.80,
                sentiment_label=SentimentLabel.POSITIVE,
                is_political=False,
            ),
        ]
        session.add_all(solano_posts)

        # ── Secciones Electorales (sample CDMX) ──────────────────
        # Note: real geometries would come from INE shapefiles via ora2pg/ogr2ogr
        # These are simplified representative points converted to tiny polygons
        secciones = [
            SeccionElectoral(
                seccion="0901-0001",
                estado="Ciudad de México",
                distrito_federal="1",
                distrito_local="1",
                municipio="Azcapotzalco",
            ),
            SeccionElectoral(
                seccion="0901-0050",
                estado="Ciudad de México",
                distrito_federal="3",
                distrito_local="5",
                municipio="Coyoacán",
            ),
            SeccionElectoral(
                seccion="0901-0100",
                estado="Ciudad de México",
                distrito_federal="5",
                distrito_local="10",
                municipio="Gustavo A. Madero",
            ),
            SeccionElectoral(
                seccion="0901-0200",
                estado="Ciudad de México",
                distrito_federal="8",
                distrito_local="15",
                municipio="Iztapalapa",
            ),
            SeccionElectoral(
                seccion="0901-0300",
                estado="Ciudad de México",
                distrito_federal="10",
                distrito_local="20",
                municipio="Tlalpan",
            ),
        ]
        session.add_all(secciones)
        await session.flush()

        # ── Intención de Voto (sample data) ───────────────────────
        for i, seccion in enumerate(secciones):
            iv = IntencionVoto(
                seccion_id=seccion.id,
                dirigente_id=pina.id,
                periodo="2026-Q1",
                muestra=150 + (i * 20),
                a_favor=35.0 + (i * 3),
                en_contra=25.0 - (i * 2),
                indeciso=30.0 - (i * 1),
                no_responde=10.0,
                fecha_encuesta=date(2026, 3, 15),
                capturado_por_id=analyst.id,
            )
            session.add(iv)

        # ── Competidores ──────────────────────────────────────────
        morena_cdmx = Competidor(
            nombre="Martí Batres Guadarrama",
            partido="MORENA",
            cargo="Jefe de Gobierno CDMX",
            es_rival=True,
        )
        pan_cdmx = Competidor(
            nombre="Santiago Taboada Cortina",
            partido="PAN",
            cargo="Candidato Jefe de Gobierno CDMX",
            es_rival=True,
        )
        session.add_all([morena_cdmx, pan_cdmx])
        await session.flush()

        comp_profile_morena_tw = CompetidorSocialProfile(
            competidor_id=morena_cdmx.id,
            platform=Platform.TWITTER,
            handle="@martlobo",
            url="https://x.com/martlobo",
            followers_count=285000,
            following_count=3200,
            posts_count=45000,
        )
        comp_profile_pan_tw = CompetidorSocialProfile(
            competidor_id=pan_cdmx.id,
            platform=Platform.TWITTER,
            handle="@Santiago_Taboada",
            url="https://x.com/Santiago_Taboada",
            followers_count=198000,
            following_count=2100,
            posts_count=32000,
        )
        comp_profile_pan_ig = CompetidorSocialProfile(
            competidor_id=pan_cdmx.id,
            platform=Platform.INSTAGRAM,
            handle="@santiagotaboadac",
            url="https://instagram.com/santiagotaboadac",
            followers_count=156000,
            following_count=1200,
            posts_count=2800,
        )
        session.add_all([comp_profile_morena_tw, comp_profile_pan_tw, comp_profile_pan_ig])

        # ── Sample AI Plan ────────────────────────────────────────
        plan = PlanIA(
            dirigente_id=pina.id,
            tipo=TipoPlan.CONSOLIDACION,
            contenido="""# Plan de Consolidación Digital — 90 Días
## Alejandro Piña Medina | MC CDMX

### Diagnóstico Actual
- IPD: 4.0/10 (bajo)
- Presencia en 3/6 plataformas
- Engagement promedio: 2.8% (aceptable en Twitter, bajo en Facebook)
- Sin presencia en TikTok ni YouTube

### Fase 1: Fundación (Días 1-30)
1. **Crear cuenta TikTok** con contenido corto sobre problemas CDMX
2. **Crear canal YouTube** con formato "Recorridos Ciudadanos" (3-5 min)
3. **Optimizar bio** en todas las plataformas con mensaje unificado
4. **Calendario editorial**: 5 posts/semana en Twitter, 3 en Instagram, 2 en TikTok

### Fase 2: Crecimiento (Días 31-60)
1. **Contenido reactivo**: responder a noticias de CDMX en < 2 horas
2. **Colaboraciones**: entrevistas cruzadas con otros dirigentes MC
3. **Hashtag propio**: #CDMXCiudadana para aglutinar comunidad
4. **Stories diarios** en Instagram mostrando trabajo de campo

### Fase 3: Consolidación (Días 61-90)
1. **Análisis de métricas** y ajuste de estrategia
2. **Campaña de engagement**: encuestas, preguntas, lives semanales
3. **Meta**: IPD 6.5/10, +2000 seguidores en TikTok, +500 en YouTube

### KPIs
| Métrica | Actual | Meta 90 días |
|---------|--------|-------------|
| IPD | 4.0 | 6.5 |
| Seguidores totales | ~7,131 | ~12,000 |
| Plataformas activas | 3 | 5 |
| Posts/semana | ~4 | ~12 |
| Engagement promedio | 2.8% | 4.5% |
""",
            modelo_ia="claude-sonnet-4-20250514",
            prompt_usado="Genera un plan de consolidación digital de 90 días para un dirigente político con IPD 4.0/10...",
            datos_entrada={
                "ipd_score": 4.0,
                "platforms": ["twitter", "instagram", "facebook"],
                "avg_engagement": 2.8,
                "followers_total": 7131,
            },
            generado_por_id=admin.id,
            aprobado=False,
        )
        session.add(plan)

        # ── Ciudadanos (sample CDMX) ─────────────────────────────
        ciudadanos_data = [
            Ciudadano(
                nombre="María",
                apellido_paterno="González",
                apellido_materno="López",
                seccion_id=secciones[0].id,
                direccion="Av. Azcapotzalco 123, Col. Centro",
                telefono="5551234567",
                email="maria.gonzalez@example.com",
                edad_rango=RangoEdad.E_36_45,
                genero=Genero.F,
                nivel_interes=NivelInteres.ALTO,
                es_simpatizante_mc=True,
                es_promotor=True,
                registrado_por_id=field_op.id,
            ),
            Ciudadano(
                nombre="José",
                apellido_paterno="Hernández",
                apellido_materno="Martínez",
                seccion_id=secciones[0].id,
                telefono="5559876543",
                edad_rango=RangoEdad.E_46_55,
                genero=Genero.M,
                nivel_interes=NivelInteres.MEDIO,
                es_simpatizante_mc=True,
                es_promotor=False,
                registrado_por_id=field_op.id,
            ),
            Ciudadano(
                nombre="Ana",
                apellido_paterno="Ramírez",
                seccion_id=secciones[1].id,
                email="ana.ramirez@example.com",
                edad_rango=RangoEdad.E_26_35,
                genero=Genero.F,
                nivel_interes=NivelInteres.ALTO,
                es_simpatizante_mc=False,
                es_promotor=False,
                registrado_por_id=analyst.id,
            ),
            Ciudadano(
                nombre="Pedro",
                apellido_paterno="Sánchez",
                apellido_materno="Díaz",
                seccion_id=secciones[2].id,
                direccion="Calle Industrias 456, GAM",
                edad_rango=RangoEdad.E_56_65,
                genero=Genero.M,
                nivel_interes=NivelInteres.BAJO,
                es_simpatizante_mc=False,
                es_promotor=False,
                registrado_por_id=field_op.id,
            ),
            Ciudadano(
                nombre="Luisa",
                apellido_paterno="Torres",
                apellido_materno="Vega",
                seccion_id=secciones[3].id,
                telefono="5553456789",
                email="luisa.torres@example.com",
                edad_rango=RangoEdad.E_18_25,
                genero=Genero.F,
                nivel_interes=NivelInteres.ALTO,
                es_simpatizante_mc=True,
                es_promotor=True,
                registrado_por_id=field_op.id,
            ),
        ]
        session.add_all(ciudadanos_data)
        await session.flush()

        # ── Eventos (sample CDMX) ────────────────────────────────
        evento_mitin = Evento(
            titulo="Mitin MC Azcapotzalco — Jornada ciudadana",
            descripcion="Jornada de afiliación y escucha ciudadana en la explanada de Azcapotzalco.",
            tipo=TipoEvento.MITIN,
            fecha_inicio=now + timedelta(days=7),
            fecha_fin=now + timedelta(days=7, hours=3),
            lugar="Explanada Azcapotzalco, CDMX",
            geometry="SRID=4326;POINT(-99.1847 19.4869)",
            seccion_id=secciones[0].id,
            dirigente_id=pina.id,
            organizador_id=admin.id,
            asistentes_esperados=150,
            estado=EstadoEvento.PROGRAMADO,
        )
        evento_reunion = Evento(
            titulo="Reunión de estructura — Coyoacán",
            descripcion="Reunión de coordinación con promotores de la sección.",
            tipo=TipoEvento.REUNION,
            fecha_inicio=now + timedelta(days=3),
            fecha_fin=now + timedelta(days=3, hours=2),
            lugar="Casa de Cultura Coyoacán",
            geometry="SRID=4326;POINT(-99.1626 19.3500)",
            seccion_id=secciones[1].id,
            dirigente_id=pina.id,
            organizador_id=analyst.id,
            asistentes_esperados=30,
            estado=EstadoEvento.PROGRAMADO,
        )
        evento_recorrido = Evento(
            titulo="Recorrido Iztapalapa — Escucha activa",
            descripcion="Recorrido puerta a puerta en colonias de Iztapalapa.",
            tipo=TipoEvento.RECORRIDO,
            fecha_inicio=now - timedelta(days=2),
            fecha_fin=now - timedelta(days=2, hours=-4),
            lugar="Central de Abasto, Iztapalapa",
            geometry="SRID=4326;POINT(-99.0870 19.3727)",
            seccion_id=secciones[3].id,
            dirigente_id=pina.id,
            organizador_id=field_op.id,
            asistentes_esperados=50,
            asistentes_reales=43,
            estado=EstadoEvento.COMPLETADO,
        )
        evento_capacitacion = Evento(
            titulo="Capacitación promotores — Tlalpan",
            tipo=TipoEvento.CAPACITACION,
            fecha_inicio=now + timedelta(days=14),
            lugar="Oficinas MC Tlalpan",
            seccion_id=secciones[4].id,
            organizador_id=admin.id,
            asistentes_esperados=25,
            estado=EstadoEvento.PROGRAMADO,
        )
        session.add_all([evento_mitin, evento_reunion, evento_recorrido, evento_capacitacion])
        await session.flush()

        # ── Evento Asistentes ─────────────────────────────────────
        asistentes_data = [
            EventoAsistente(
                evento_id=evento_recorrido.id,
                ciudadano_id=ciudadanos_data[0].id,
                confirmado=True,
                asistio=True,
            ),
            EventoAsistente(
                evento_id=evento_recorrido.id,
                ciudadano_id=ciudadanos_data[4].id,
                confirmado=True,
                asistio=True,
            ),
            EventoAsistente(
                evento_id=evento_mitin.id,
                ciudadano_id=ciudadanos_data[0].id,
                confirmado=True,
                asistio=False,
            ),
            EventoAsistente(
                evento_id=evento_mitin.id,
                ciudadano_id=ciudadanos_data[1].id,
                confirmado=False,
                asistio=False,
            ),
        ]
        session.add_all(asistentes_data)

        # ── Programas Sociales (SAMPLE DATA — not real government figures) ──
        # NOTE: These are CLEARLY LABELED sample records for development only.
        # Real data must come from CONEVAL, Bienestar, or official government sources.
        prog_bienestar = ProgramaSocial(
            nombre="[SAMPLE] Programa de Bienestar Social",
            descripcion="Dato de ejemplo para desarrollo. NO es un programa real. Los datos reales deben cargarse desde fuentes oficiales (CONEVAL, Bienestar).",
            dependencia="Secretaría de Bienestar (SAMPLE)",
            nivel_gobierno=NivelGobierno.FEDERAL,
            presupuesto_anual=None,  # No inventar cifras
        )
        prog_educacion = ProgramaSocial(
            nombre="[SAMPLE] Beca Educativa Municipal",
            descripcion="Dato de ejemplo para desarrollo. NO es un programa real. Los datos reales deben cargarse desde fuentes oficiales.",
            dependencia="Alcaldía (SAMPLE)",
            nivel_gobierno=NivelGobierno.MUNICIPAL,
            presupuesto_anual=None,
        )
        prog_salud = ProgramaSocial(
            nombre="[SAMPLE] Programa Estatal de Salud Comunitaria",
            descripcion="Dato de ejemplo para desarrollo. NO es un programa real.",
            dependencia="Secretaría de Salud CDMX (SAMPLE)",
            nivel_gobierno=NivelGobierno.ESTATAL,
            presupuesto_anual=None,
        )
        session.add_all([prog_bienestar, prog_educacion, prog_salud])
        await session.flush()

        # ── Programa Beneficiarios (SAMPLE — synthetic counts) ────
        for i, seccion in enumerate(secciones):
            session.add(ProgramaBeneficiario(
                programa_id=prog_bienestar.id,
                seccion_id=seccion.id,
                beneficiarios_count=100 + (i * 50),  # SAMPLE synthetic count
                periodo="2026-Q1",
                fecha_actualizacion=date(2026, 3, 1),
                fuente_datos="SAMPLE_DEV_DATA",
            ))
        # Only some sections for the other programs
        session.add(ProgramaBeneficiario(
            programa_id=prog_educacion.id,
            seccion_id=secciones[1].id,
            beneficiarios_count=45,
            periodo="2026-Q1",
            fecha_actualizacion=date(2026, 3, 1),
            fuente_datos="SAMPLE_DEV_DATA",
        ))
        session.add(ProgramaBeneficiario(
            programa_id=prog_salud.id,
            seccion_id=secciones[3].id,
            beneficiarios_count=200,
            periodo="2026-Q1",
            fecha_actualizacion=date(2026, 3, 1),
            fuente_datos="SAMPLE_DEV_DATA",
        ))

        await session.commit()
        print("\n✅ Seed completado exitosamente!")
        print("   - 3 organizaciones (MC-CDMX, GOB-OAXACA, CDMX-IND)")
        print("   - 9 usuarios (admin, analista, campo + 6 dirigentes)")
        print("   - 6 dirigentes (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto)")
        print("   - 15 perfiles sociales")
        print("   - 6 posts de ejemplo")
        print("   - 5 secciones electorales CDMX")
        print("   - 5 registros de intención de voto")
        print("   - 2 competidores (Batres, Taboada) con 3 perfiles sociales")
        print("   - 1 plan IA de ejemplo")
        print("   - 5 ciudadanos (2 promotores)")
        print("   - 4 eventos (1 completado, 3 programados)")
        print("   - 4 registros de asistencia")
        print("   - 3 programas sociales [SAMPLE]")
        print("   - 7 registros de beneficiarios [SAMPLE]")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
