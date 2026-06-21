import importlib


def test_agent_model_defaults_to_lower_cost_model(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MAX_TOKENS", raising=False)

    import agents.constants as constants

    constants = importlib.reload(constants)

    assert constants.REVIEW_MODEL_NAME == "gpt-4.1-mini"
    assert constants.MAX_TOKENS == 1200


def test_agent_model_can_be_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_REVIEW_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_MAX_TOKENS", "800")

    import agents.constants as constants

    constants = importlib.reload(constants)

    assert constants.REVIEW_MODEL_NAME == "gpt-5.4-mini"
    assert constants.MAX_TOKENS == 800
