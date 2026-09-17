from maitri.config import Settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    config = Settings()
    assert config.app_name == "Maitri Backend"
    assert config.environment == "development"
    assert config.database_url == "sqlite:///./maitri.db"


def test_environment_variable_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Custom Maitri Test")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_custom.db")

    config = Settings()
    assert config.app_name == "Custom Maitri Test"
    assert config.environment == "staging"
    assert config.database_url == "sqlite:///./test_custom.db"
