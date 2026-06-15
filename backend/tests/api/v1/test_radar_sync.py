import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock
from app.core.security import Role, create_access_token
from app.models.dirigente import Dirigente
from app.models.ingest_job import IngestJob, IngestJobStatus
from tests.conftest import auth_headers

@pytest.mark.asyncio
async def test_sync_status_404(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/ingest/sync/status/9999", headers=auth_headers(admin_token))
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_sync_trigger_no_bundles(client: AsyncClient, db_session: AsyncSession, admin_token: str):
    # Seed dirigente
    d = Dirigente(full_name="Test Sync", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(d)
    await db_session.commit()
    
    with patch("app.services.radar_sync.get_s3_client") as mock_s3:
        # Mocking paginator for list_objects_v2
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = []
        mock_s3.return_value.get_paginator.return_value = mock_paginator
        
        resp = await client.post(f"/api/v1/ingest/sync/{d.id}", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert resp.json()["sin_novedades"] is True

@pytest.mark.asyncio
async def test_sync_trigger_existing_completed(client: AsyncClient, db_session: AsyncSession, admin_token: str):
    d = Dirigente(full_name="Test Sync 2", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(d)
    await db_session.flush()
    
    # Existing job
    job = IngestJob(
        task_uuid="uuid123",
        schema_version="d041-v1",
        slug="test",
        dirigente_id=d.id,
        status=IngestJobStatus.COMPLETED,
        manifest={}
    )
    db_session.add(job)
    await db_session.commit()
    
    with patch("app.services.radar_sync.get_s3_client") as mock_s3:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'CommonPrefixes': [{'Prefix': 'radar-handoffs/test/uuid123/'}]}]
        mock_s3.return_value.get_paginator.return_value = mock_paginator
        mock_s3.return_value.list_objects_v2.return_value = {'Contents': [{'LastModified': '2026-06-13T00:00:00Z'}]}
        
        resp = await client.post(f"/api/v1/ingest/sync/{d.id}", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert resp.json()["sin_novedades"] is True
        assert resp.json()["task_uuid"] == "uuid123"

@pytest.mark.asyncio
async def test_sync_trigger_discovery(client: AsyncClient, db_session: AsyncSession, admin_token: str):
    d = Dirigente(full_name="Test Sync 3", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(d)
    await db_session.flush()
    await db_session.commit()
    
    with patch("app.services.radar_sync.get_s3_client") as mock_s3, \
         patch("app.workers.ingest_tasks.process_radar_handoff.delay") as mock_delay:
        
        # Latest in MinIO is uuidDiscovery
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'CommonPrefixes': [{'Prefix': 'radar-handoffs/test/uuidDiscovery/'}]}]
        mock_s3.return_value.get_paginator.return_value = mock_paginator
        mock_s3.return_value.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'radar-handoffs/test/uuidDiscovery/followers.json', 'LastModified': '2026-06-13T00:00:00Z'}
            ]
        }
        
        # Mock discover_manifest to return a fake manifest
        with patch("app.services.radar_sync.discover_manifest") as mock_discover:
            mock_discover.return_value = {
                "task_uuid": "uuidDiscovery",
                "schema_version": "d041-v1",
                "slug": "test",
                "dirigente_id": d.id,
                "window": {"from": "2026-01-01T00:00:00Z", "to": "2026-06-13T00:00:00Z"},
                "files": [{"name": "followers.json", "sha256": "hash", "record_count": 5}],
                "minio_path": "radar-handoffs/test/uuidDiscovery"
            }
            
            resp = await client.post(f"/api/v1/ingest/sync/{d.id}", headers=auth_headers(admin_token))
            assert resp.status_code == 200
            assert resp.json()["status"] == "RECEIVED"
            assert resp.json()["task_uuid"] == "uuidDiscovery"
            mock_delay.assert_called_once()
