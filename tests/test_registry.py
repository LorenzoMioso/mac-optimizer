"""
Test per il registro dei moduli in mac_optimizer.registry.
"""

from mac_optimizer.registry import create_all_modules


def test_create_all_modules():
    modules = create_all_modules()
    assert len(modules) >= 20

    ids = [m.id for m in modules]
    assert len(ids) == len(set(ids)), "Tutti gli ID dei moduli devono essere univoci!"

    for m in modules:
        assert m.id, "L'ID non può essere vuoto"
        assert m.name, f"Il nome del modulo {m.id} non può essere vuoto"
        assert m.category, f"La categoria del modulo {m.id} non può essere vuota"
        assert m.description, f"La descrizione del modulo {m.id} non può essere vuota"
        assert m.risk_level in ("safe", "recommended", "caution")
        assert callable(m.scan_func)
        assert callable(m.clean_func)


def test_expected_categories():
    modules = create_all_modules()
    categories = {m.category for m in modules}
    expected = {
        "🍎 Sviluppo iOS & macOS",
        "📦 Package Managers & SDK",
        "💻 Editor & Strumenti",
        "🌐 Cache App & Browser",
        "⚙️ Sistema macOS & RAM",
        "⚠️ Operazioni Avanzate (Opt-in)",
    }
    assert expected.issubset(categories)


def test_simulators_module_custom_label():
    modules = create_all_modules()
    sim_mod = next(m for m in modules if m.id == "simulators")
    assert "Simulatori" in sim_mod.name
    # Verifica che la label contenga l'indicazione esplicita della versione mantenuta
    assert "Mantiene" in sim_mod.name
