from config import get_settings


def test_enable_911_autodial_defaults_false(monkeypatch):
    monkeypatch.delenv("ENABLE_911_AUTODIAL", raising=False)
    get_settings.cache_clear()
    assert get_settings().enable_911_autodial is False


def test_enable_911_autodial_reads_truthy_env_values(monkeypatch):
    for value in ("true", "True", "1", "yes"):
        monkeypatch.setenv("ENABLE_911_AUTODIAL", value)
        get_settings.cache_clear()
        assert get_settings().enable_911_autodial is True

    monkeypatch.setenv("ENABLE_911_AUTODIAL", "false")
    get_settings.cache_clear()
    assert get_settings().enable_911_autodial is False
