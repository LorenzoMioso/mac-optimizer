"""
Test per i moduli di pulizia applicazioni e browser in mac_optimizer.modules.apps.
"""

from mac_optimizer.modules.apps import (
    scan_spotify_cache, clean_spotify_cache,
    scan_browser_caches, clean_browser_caches,
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
