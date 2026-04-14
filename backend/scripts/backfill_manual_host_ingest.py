"""Backfill: marca perfiles que Carlos ingestó host-side como manual_host_ingest.

Uso:
    docker exec crece-backend python scripts/backfill_manual_host_ingest.py

Qué hace:
- Marca ``data_source='manual_host_ingest'`` + ``last_manual_update=NOW()`` en:
  - Los 3 perfiles YouTube de Piña, Pineda y Cravioto (56 videos ingestados host-side).
  - Perfil TikTok de Piña (62 posts con engagement 4.47 pero followers_count=0
    porque el fallback Playwright de TikTokApi v7.3.3 es inestable en Docker).
- Backfill manual de followers_count TikTok de Piña basándose en el dato real
  más reciente conocido (ajustar CEO si lo tiene a mano antes de correr).

Idempotente: correr dos veces no duplica nada.
Requiere: migrations ds01 y ds02 aplicadas.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.social import DataSource, Platform, SocialProfile

# Followers TikTok conocidos (dato manual del CEO). TODO: actualizar con dato real.
KNOWN_TIKTOK_FOLLOWERS: dict[str, int] = {
    "pina": 0,  # reemplazar con dato real antes de correr
}


def main() -> int:
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    now = datetime.now(UTC)
    with Session(engine) as session:
        affected = 0

        # YouTube profiles ingestados host-side por Carlos
        yt_handles = ["pina", "pineda", "cravioto"]  # handles conocidos
        for handle_like in yt_handles:
            stmt = (
                select(SocialProfile)
                .where(SocialProfile.platform == Platform.YOUTUBE)
                .where(SocialProfile.handle.ilike(f"%{handle_like}%"))
            )
            for profile in session.scalars(stmt).all():
                profile.data_source = DataSource.MANUAL_HOST_INGEST
                profile.last_manual_update = now
                affected += 1
                print(f"YT  {profile.handle}: marked manual_host_ingest")

        # TikTok Piña — fallback Playwright inestable
        tt_stmt = (
            select(SocialProfile)
            .join(Dirigente, SocialProfile.dirigente_id == Dirigente.id)
            .where(SocialProfile.platform == Platform.TIKTOK)
            .where(Dirigente.full_name.ilike("%piña%"))
        )
        for profile in session.scalars(tt_stmt).all():
            profile.data_source = DataSource.MANUAL_HOST_INGEST
            profile.last_manual_update = now
            if profile.followers_count == 0 and KNOWN_TIKTOK_FOLLOWERS.get("pina", 0) > 0:
                profile.followers_count = KNOWN_TIKTOK_FOLLOWERS["pina"]
                print(
                    f"TT  {profile.handle}: followers backfilled to {profile.followers_count}"
                )
            affected += 1
            print(f"TT  {profile.handle}: marked manual_host_ingest")

        session.commit()
        print(f"\nDone. {affected} profiles updated.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
