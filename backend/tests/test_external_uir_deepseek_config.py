from app.config import Settings


def test_external_uir_deepseek_settings_default_to_disabled() -> None:
    settings = Settings()

    assert settings.external_uir_llm_enabled is False
    assert settings.external_uir_llm_provider == "deepseek"
    assert settings.deepseek_api_key is None
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.deepseek_timeout_seconds == 20
    assert settings.deepseek_max_retries == 0
    assert settings.deepseek_max_suggestions_per_request == 20
    assert settings.deepseek_strict_json is True
