# Coolify Deployment — CRECE v2.0

## Prerequisites

- Coolify v4+ instance running
- Git repository accessible from Coolify server
- Domain name configured (DNS pointing to Coolify server)

## Deployment Steps

1. **Create Project**
   - In Coolify dashboard, create a new Project
   - Add a new Resource of type "Docker Compose"

2. **Connect Repository**
   - Point to your Git repository
   - Set compose file path: `docker/coolify/docker-compose.coolify.yml`

3. **Configure Environment Variables**
   All variables must be set in Coolify's Environment Variables section:

   ```
   POSTGRES_USER=crece
   POSTGRES_PASSWORD=<generate-strong-password>
   POSTGRES_DB=crece
   DATABASE_URL=postgresql+asyncpg://crece:<password>@db:5432/crece
   REDIS_URL=redis://:<redis-password>@redis:6379/0
   REDIS_PASSWORD=<generate-strong-password>
   MINIO_ROOT_USER=<generate-access-key>
   MINIO_ROOT_PASSWORD=<generate-secret-key>
   MINIO_ENDPOINT=minio:9000
   MINIO_BUCKET=crece-files
   JWT_SECRET=<openssl-rand-hex-64>
   CLAUDE_API_KEY=sk-ant-<your-key>
   CELERY_BROKER_URL=redis://:<redis-password>@redis:6379/1
   CELERY_RESULT_BACKEND=redis://:<redis-password>@redis:6379/2
   FLOWER_USER=admin
   FLOWER_PASSWORD=<generate-strong-password>
   NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1
   NEXT_PUBLIC_MAPLIBRE_STYLE=https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json
   CORS_ORIGINS=["https://your-domain.com"]
   ```

4. **Configure Domains**
   - Set primary domain for the `frontend` service
   - Coolify handles SSL via Let's Encrypt automatically

5. **Deploy**
   - Click Deploy in Coolify
   - Monitor build logs for any issues

6. **Post-Deploy**
   - Run migrations: Execute `alembic upgrade head` in the backend container
   - Verify all services are healthy in Coolify's dashboard

## Updating

Push to your configured branch. If auto-deploy is enabled, Coolify will
rebuild and redeploy automatically. Otherwise, trigger a manual deploy
from the Coolify dashboard.
