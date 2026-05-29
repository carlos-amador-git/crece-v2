"""
Seed multi-tenant data: 2 new orgs + 4 new users + 4 new dirigentes + social profiles.
Idempotent — checks for existing slugs before inserting.

Run with: docker exec crece-backend python -m scripts.seed_multitenant
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion
from app.models.social import Platform, SocialProfile
from app.models.user import Role, User


async def seed_multitenant():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── Check existing orgs ───────────────────────────────────
        existing = (await session.execute(
            select(Organizacion.slug)
        )).scalars().all()
        existing_slugs = set(existing)

        # Ensure MC-CDMX exists and get its ID
        mc_result = await session.execute(
            select(Organizacion).where(Organizacion.slug == "mc-cdmx")
        )
        org_mc = mc_result.scalar_one_or_none()
        if not org_mc:
            print("ERROR: mc-cdmx org not found. Run base seed first.")
            return

        # ── Org: GOB-OAXACA ──────────────────────────────────────
        if "gob-oaxaca" not in existing_slugs:
            org_oaxaca = Organizacion(
                nombre="Gobierno Oaxaca",
                slug="gob-oaxaca",
                tipo="GOBIERNO",
                estado="Oaxaca",
                config={"is_demo": True, "has_synthetic_data": True},
            )
            session.add(org_oaxaca)
            await session.flush()
            print(f"  + Org GOB-OAXACA (id={org_oaxaca.id})")
        else:
            org_oaxaca = (await session.execute(
                select(Organizacion).where(Organizacion.slug == "gob-oaxaca")
            )).scalar_one()
            print(f"  = Org GOB-OAXACA ya existe (id={org_oaxaca.id})")

        # ── Org: CDMX-IND ────────────────────────────────────────
        if "cdmx-ind" not in existing_slugs:
            org_cdmx_ind = Organizacion(
                nombre="CDMX Independiente",
                slug="cdmx-ind",
                tipo="GOBIERNO",
                estado="Ciudad de México",
                config={"is_demo": True, "has_synthetic_data": True},
            )
            session.add(org_cdmx_ind)
            await session.flush()
            print(f"  + Org CDMX-IND (id={org_cdmx_ind.id})")
        else:
            org_cdmx_ind = (await session.execute(
                select(Organizacion).where(Organizacion.slug == "cdmx-ind")
            )).scalar_one()
            print(f"  = Org CDMX-IND ya existe (id={org_cdmx_ind.id})")

        # ── Fix existing dirigentes org_id if NULL ────────────────
        await session.execute(
            text("UPDATE dirigentes SET org_id = :org_id WHERE org_id IS NULL"),
            {"org_id": org_mc.id},
        )

        # ── Dirigentes + Users: GOB-OAXACA ────────────────────────
        async def ensure_dirigente_and_user(
            full_name: str,
            cargo: str,
            partido: str,
            estado: str,
            municipio: str,
            org_id: int,
            email: str,
            profiles: list[dict],
        ):
            """Create dirigente + user + social profiles if they don't exist."""
            existing_d = (await session.execute(
                select(Dirigente).where(Dirigente.full_name == full_name)
            )).scalar_one_or_none()

            if existing_d:
                print(f"  = Dirigente {full_name} ya existe (id={existing_d.id})")
                dirigente = existing_d
                # Ensure org_id is set
                if dirigente.org_id != org_id:
                    dirigente.org_id = org_id
            else:
                dirigente = Dirigente(
                    full_name=full_name,
                    cargo=cargo,
                    partido=partido,
                    estado=estado,
                    municipio=municipio,
                    org_id=org_id,
                )
                session.add(dirigente)
                await session.flush()
                print(f"  + Dirigente {full_name} (id={dirigente.id})")

            # User
            existing_u = (await session.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()

            if existing_u:
                print(f"  = User {email} ya existe (id={existing_u.id})")
                if existing_u.dirigente_id != dirigente.id:
                    existing_u.dirigente_id = dirigente.id
                if existing_u.org_id != org_id:
                    existing_u.org_id = org_id
            else:
                user = User(
                    email=email,
                    hashed_password=hash_password("demo2026!"),
                    full_name=full_name,
                    role=Role.VIEWER,
                    is_active=True,
                    org_id=org_id,
                    dirigente_id=dirigente.id,
                )
                session.add(user)
                await session.flush()
                print(f"  + User {email} (id={user.id})")

            # Social profiles
            existing_profiles = (await session.execute(
                select(SocialProfile.platform).where(
                    SocialProfile.dirigente_id == dirigente.id
                )
            )).scalars().all()
            existing_platforms = set(existing_profiles)

            for p in profiles:
                if p["platform"] not in existing_platforms:
                    sp = SocialProfile(dirigente_id=dirigente.id, **p)
                    session.add(sp)
                    print(f"    + Profile {p['platform'].value} @{p['handle']}")

            await session.flush()

        # ── Saymi Pineda Velasco ──────────────────────────────────
        await ensure_dirigente_and_user(
            full_name="Saymi Adriana Pineda Velasco",
            cargo="Secretaria de Turismo Oaxaca",
            partido="MORENA",
            estado="Oaxaca",
            municipio="Oaxaca de Juárez",
            org_id=org_oaxaca.id,
            email="pineda@crece.mx",
            profiles=[
                {
                    "platform": Platform.TWITTER,
                    "handle": "@saymipinedav",
                    "url": "https://x.com/saymipinedav",
                    "followers_count": 8800,
                    "following_count": 1500,
                    "posts_count": 3200,
                },
                {
                    "platform": Platform.INSTAGRAM,
                    "handle": "@saymipinedavelasco",
                    "url": "https://instagram.com/saymipinedavelasco",
                    "followers_count": 12000,
                    "following_count": 950,
                    "posts_count": 680,
                },
            ],
        )

        # ── Yesenia Nolasco Ramírez ──────────────────────────────
        await ensure_dirigente_and_user(
            full_name="Yesenia Nolasco Ramírez",
            cargo="Secretaria de Movilidad (SEMOVI) Oaxaca",
            partido="MORENA",
            estado="Oaxaca",
            municipio="Oaxaca de Juárez",
            org_id=org_oaxaca.id,
            email="nolasco@crece.mx",
            profiles=[
                {
                    "platform": Platform.TWITTER,
                    "handle": "@Yes_Nolasco",
                    "url": "https://x.com/Yes_Nolasco",
                    "followers_count": 5200,
                    "following_count": 890,
                    "posts_count": 2100,
                },
                {
                    "platform": Platform.FACEBOOK,
                    "handle": "YesNolasco",
                    "url": "https://facebook.com/YesNolasco",
                    "followers_count": 32000,
                    "following_count": 0,
                    "posts_count": 1500,
                },
            ],
        )

        # ── Gabriela Jiménez Godoy ───────────────────────────────
        await ensure_dirigente_and_user(
            full_name="Gabriela Jiménez Godoy",
            cargo="Diputada Federal, Vicecoordinadora",
            partido="MORENA",
            estado="Ciudad de México",
            municipio="CDMX",
            org_id=org_cdmx_ind.id,
            email="jimenez@crece.mx",
            profiles=[
                {
                    "platform": Platform.TWITTER,
                    "handle": "@GabyJimenezMX",
                    "url": "https://x.com/GabyJimenezMX",
                    "followers_count": 45000,
                    "following_count": 2300,
                    "posts_count": 18000,
                },
                {
                    "platform": Platform.INSTAGRAM,
                    "handle": "@gabyjimenezgo",
                    "url": "https://instagram.com/gabyjimenezgo",
                    "followers_count": 28000,
                    "following_count": 1200,
                    "posts_count": 950,
                },
                {
                    "platform": Platform.FACEBOOK,
                    "handle": "GabyJimenezGo",
                    "url": "https://facebook.com/GabyJimenezGo",
                    "followers_count": 92000,
                    "following_count": 0,
                    "posts_count": 4200,
                },
                {
                    "platform": Platform.TIKTOK,
                    "handle": "@gabyjimenezmx",
                    "url": "https://tiktok.com/@gabyjimenezmx",
                    "followers_count": 15000,
                    "following_count": 100,
                    "posts_count": 320,
                },
            ],
        )

        # ── César Cravioto Romero ─────────────────────────────────
        await ensure_dirigente_and_user(
            full_name="César Cravioto Romero",
            cargo="Secretario de Gobierno CDMX",
            partido="MORENA",
            estado="Ciudad de México",
            municipio="CDMX",
            org_id=org_cdmx_ind.id,
            email="cravioto@crece.mx",
            profiles=[
                {
                    "platform": Platform.TWITTER,
                    "handle": "@craviotocesar",
                    "url": "https://x.com/craviotocesar",
                    "followers_count": 67000,
                    "following_count": 3100,
                    "posts_count": 25000,
                },
                {
                    "platform": Platform.FACEBOOK,
                    "handle": "craviotocesar",
                    "url": "https://facebook.com/craviotocesar",
                    "followers_count": 48000,
                    "following_count": 0,
                    "posts_count": 3800,
                },
            ],
        )

        await session.commit()
        print("\n✅ Multi-tenant seed completado!")

        # ── Summary ───────────────────────────────────────────────
        org_count = (await session.execute(text("SELECT count(*) FROM organizaciones"))).scalar()
        user_count = (await session.execute(text("SELECT count(*) FROM users"))).scalar()
        dir_count = (await session.execute(text("SELECT count(*) FROM dirigentes"))).scalar()
        prof_count = (await session.execute(text("SELECT count(*) FROM social_profiles"))).scalar()

        print(f"   Orgs: {org_count}")
        print(f"   Users: {user_count}")
        print(f"   Dirigentes: {dir_count}")
        print(f"   Social Profiles: {prof_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_multitenant())
