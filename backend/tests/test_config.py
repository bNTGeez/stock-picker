from backend.config import get_settings


def test_default_settings_are_available() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.llm_provider == "manual"
    assert settings.llm_api_key is None
    assert settings.llm_model
    assert settings.quote_match_threshold == 0.95
    assert str(settings.raw_data_dir).endswith("backend/data/raw")


def test_settings_can_be_configured_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("RESEARCH_LLM_PROVIDER", "openai")
    monkeypatch.setenv("RESEARCH_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RESEARCH_LLM_MODEL", "gpt-test")
    monkeypatch.setenv("RESEARCH_QUOTE_MATCH_THRESHOLD", "0.9")
    monkeypatch.setenv("RESEARCH_DATA_DIR", "/tmp/research-data")
    monkeypatch.setenv("RESEARCH_RAW_DATA_DIR", "/tmp/raw-data")
    monkeypatch.setenv("RESEARCH_PROCESSED_DATA_DIR", "/tmp/processed-data")

    settings = get_settings()

    assert settings.llm_provider == "openai"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "gpt-test"
    assert settings.quote_match_threshold == 0.9
    assert str(settings.data_dir) == "/tmp/research-data"
    assert str(settings.raw_data_dir) == "/tmp/raw-data"
    assert str(settings.processed_data_dir) == "/tmp/processed-data"

    get_settings.cache_clear()
