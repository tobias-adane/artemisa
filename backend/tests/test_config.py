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


def test_cors_allowed_origins_defaults_to_localhost_3000(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    get_settings.cache_clear()
    assert get_settings().cors_allowed_origins == ["http://localhost:3000"]


def test_cors_allowed_origins_reads_comma_separated_list(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.artemisa.ar, https://beta.artemisa.ar")
    get_settings.cache_clear()
    assert get_settings().cors_allowed_origins == ["https://app.artemisa.ar", "https://beta.artemisa.ar"]
