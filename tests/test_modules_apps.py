"""
Test per i moduli di pulizia applicazioni e browser in mac_optimizer.modules.apps.
"""

from mac_optimizer.modules.apps import (
    scan_spotify_cache, clean_spotify_cache,
    scan_browser_caches, clean_browser_caches,
    scan_discord_cache, clean_discord_cache,
)


def test_spotify_cache():
    res = clean_spotify_cache(dry_run=True)
    assert res.name == "Spotify Streaming Cache"
    assert isinstance(res.freed_bytes, int)


def test_browser_caches_safety():
    """Verifica che la pulizia browser espliciti la totale sicurezza su credenziali e cookie."""
    res = clean_browser_caches(dry_run=True)
    assert res.name == "Browser Web Caches (Brave, Chrome, Safari)"
    assert any("cookie" in d.lower() or "credenziali" in d.lower() for d in res.details)


def test_discord_cache_clean(tmp_path, monkeypatch):
    discord_dir = tmp_path / "discord" / "Cache"
    discord_dir.mkdir(parents=True)
    (discord_dir / "media.cache").write_text("media")

    monkeypatch.setattr(
        "mac_optimizer.modules.apps.DISCORD_CACHE_PATHS",
        [(str(discord_dir), "Cache media")]
    )

    assert scan_discord_cache() > 0
    res_dry = clean_discord_cache(dry_run=True)
    assert res_dry.freed_bytes > 0

    res_real = clean_discord_cache(dry_run=False)
    assert res_real.freed_bytes > 0
    assert not (discord_dir / "media.cache").exists()
