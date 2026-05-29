"""
One-shot patch · 2026-05-29
Inserta los 3 usuarios/dirigentes faltantes (ballesteros, pmonroy, martinez) en
una BD que ya tiene seed.py corrido. Idempotente: si el user/dirigente ya existe
por email/nombre, lo deja como está.

Uso (dentro del container backend):
    python -m scripts.patch_add_3_users_2026_05_29

Diseñado para deploys donde seed.py original (commit anterior a fecha) no
incluía estos 3 perfiles. seed.py nuevo (post-merge MarxCha + fix) sí los
incluye, pero correrlo en una BD existente falla con duplicate-key.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion
from app.models.user import Role, User


PERFILES = [
    {
        "dirigente_full_name": "Laura Ballesteros Mancilla",
        "dirigente_cargo": "Diputada Federal Plurinominal",
        "dirigente_partido": "MC",
        "user_email": "ballesteros@crece.mx",
        "user_password": "Ballesteros2026!",
    },
    {
        "dirigente_full_name": "Pepe Monroy",
        "dirigente_cargo": "[PENDIENTE] proyecto PAZ — actualizar desde admin UI",
        "dirigente_partido": "INDEPENDIENTE",
        "user_email": "pmonroy@paz.mx",
        "user_password": "demo2026!",
    },
    {
        "dirigente_full_name": "Felipe Martínez",
        "dirigente_cargo": "[PENDIENTE] actualizar desde admin UI",
        "dirigente_partido": "MC",
        "user_email": "martinez@crece.mx",
        "user_password": "demo2026!",
    },
]


async def patch() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        org_mc = await session.scalar(
            select(Organizacion).where(Organizacion.slug == "mc-cdmx")
        )
        if not org_mc:
            print("ERROR: org 'mc-cdmx' no existe. ¿Corriste seed.py antes?")
            sys.exit(1)

        for p in PERFILES:
            existing_user = await session.scalar(
                select(User).where(User.email == p["user_email"])
            )
            if existing_user:
                print(f"  skip user {p['user_email']} (ya existe id={existing_user.id})")
                continue

            existing_dir = await session.scalar(
                select(Dirigente).where(Dirigente.full_name == p["dirigente_full_name"])
            )
            if existing_dir:
                dirigente = existing_dir
                print(f"  reuse dirigente '{p['dirigente_full_name']}' id={dirigente.id}")
            else:
                dirigente = Dirigente(
                    full_name=p["dirigente_full_name"],
                    cargo=p["dirigente_cargo"],
                    partido=p["dirigente_partido"],
                    estado="Ciudad de México",
                    municipio="CDMX",
                    org_id=org_mc.id,
                )
                session.add(dirigente)
                await session.flush()
                print(f"  create dirigente '{p['dirigente_full_name']}' id={dirigente.id}")

            user = User(
                email=p["user_email"],
                hashed_password=hash_password(p["user_password"]),
                full_name=p["dirigente_full_name"],
                role=Role.VIEWER,
                is_active=True,
                org_id=org_mc.id,
                dirigente_id=dirigente.id,
            )
            session.add(user)
            await session.flush()
            print(f"  create user {p['user_email']} id={user.id} → dirigente_id={dirigente.id}")

        await session.commit()
        print("\nDone. Login con las 3 credenciales debería funcionar.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(patch())
