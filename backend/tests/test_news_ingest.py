"""S4.7 — Tests del parser RSS (ingest side, sin red ni DB)."""

from __future__ import annotations

from app.services.news_ingest import RSS_SOURCES, _parse_feed, _platform_post_id

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample</title>
<item>
<title>Presidencia anuncia plan de seguridad CDMX</title>
<link>https://gob.mx/presidencia/prensa/plan-cdmx-001</link>
<guid>urn:gob.mx:plan-cdmx-001</guid>
<pubDate>Fri, 11 Apr 2026 09:00:00 GMT</pubDate>
<description><![CDATA[<p>El plan incluye <b>reforzamiento</b> en Cuauhtémoc.</p>]]></description>
</item>
<item>
<title>Alcaldesa recorre colonias de Benito Juárez</title>
<link>https://gob.mx/presidencia/prensa/recorrido-bj</link>
<description>Recorrido vecinal en Narvarte y Del Valle.</description>
</item>
</channel>
</rss>
""".encode()


def test_parse_feed_extracts_two_items() -> None:
    items = _parse_feed(SAMPLE_RSS, source="Test")
    assert len(items) == 2

    first = items[0]
    assert first.title.startswith("Presidencia anuncia")
    assert first.link.endswith("plan-cdmx-001")
    assert first.guid == "urn:gob.mx:plan-cdmx-001"
    assert "Cuauhtémoc" in first.summary
    assert "<p>" not in first.summary  # HTML stripped
    assert first.published is not None
    assert first.published.year == 2026
    assert first.source == "Test"


def test_parse_feed_handles_missing_pubdate_and_guid() -> None:
    items = _parse_feed(SAMPLE_RSS, source="Test")
    second = items[1]
    # No pubDate provided in sample
    assert second.published is None
    # No guid tag — falls back to link
    assert second.guid == "https://gob.mx/presidencia/prensa/recorrido-bj"


def test_platform_post_id_is_stable_and_unique() -> None:
    items = _parse_feed(SAMPLE_RSS, source="Test")
    id_a = _platform_post_id(items[0])
    id_b = _platform_post_id(items[1])
    assert id_a != id_b
    assert id_a.startswith("news:")
    assert len(id_a) == len("news:") + 24
    # Stable across calls
    assert _platform_post_id(items[0]) == id_a


def test_rss_sources_has_8_feeds_per_plan() -> None:
    assert len(RSS_SOURCES) == 8
    names = {f.name for f in RSS_SOURCES}
    # Sanity check: the 4 oficiales should be there
    required_official = {"Presidencia MX", "Gaceta CDMX", "Congreso CDMX", "IECM"}
    assert required_official.issubset(names)
