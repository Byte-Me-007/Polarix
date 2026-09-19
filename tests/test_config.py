from maitri.config import Settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MQTT_BROKER_HOST", raising=False)
    monkeypatch.delenv("MQTT_BROKER_PORT", raising=False)
    monkeypatch.delenv("MQTT_TOPIC_PREFIX", raising=False)

    config = Settings()
    assert config.app_name == "Maitri Backend"
    assert config.environment == "development"
    assert config.database_url == "sqlite:///./maitri.db"
    assert config.mqtt_broker_host == "localhost"
    assert config.mqtt_broker_port == 1883
    assert config.mqtt_topic_prefix == "antarctic"


def test_environment_variable_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Custom Maitri Test")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_custom.db")
    monkeypatch.setenv("MQTT_BROKER_HOST", "mqtt.antarctica.local")
    monkeypatch.setenv("MQTT_BROKER_PORT", "8883")
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "polar_base")

    config = Settings()
    assert config.app_name == "Custom Maitri Test"
    assert config.environment == "staging"
    assert config.database_url == "sqlite:///./test_custom.db"
    assert config.mqtt_broker_host == "mqtt.antarctica.local"
    assert config.mqtt_broker_port == 8883
    assert config.mqtt_topic_prefix == "polar_base"

