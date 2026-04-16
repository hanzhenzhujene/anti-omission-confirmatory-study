from anti_omission.client import (
    _detect_openai_api_mode,
    _extract_chat_completion_text,
    _extract_response_text,
    build_chat_completion_request_kwargs,
    build_response_request_kwargs,
    openai_runtime_diagnostics,
    supports_temperature,
)
from anti_omission.schemas import ConditionRecord, ExperimentConfig, ModelConfig


def test_gpt5_family_omits_temperature_from_live_request_kwargs() -> None:
    model_config = ModelConfig(model_id="gpt-5-mini")
    experiment_config = ExperimentConfig(
        run_name="dev",
        model_config_path="configs/model/openai_subject.json",
        condition_paths=["configs/conditions/baseline.json"],
        scenario_paths=["scenarios/dev/dev_medical_assay_contamination_v1.json"],
        client_mode="live",
        temperature=0.7,
    )
    condition = ConditionRecord(
        condition_id="baseline",
        version="v1",
        instruction_text="Answer directly.",
    )

    kwargs = build_response_request_kwargs(
        model_config=model_config,
        experiment_config=experiment_config,
        condition=condition,
        user_prompt="Hello",
    )

    assert supports_temperature("gpt-5-mini") is False
    assert "temperature" not in kwargs


def test_non_gpt5_family_keeps_temperature_in_live_request_kwargs() -> None:
    model_config = ModelConfig(model_id="gpt-4.1-mini")
    experiment_config = ExperimentConfig(
        run_name="dev",
        model_config_path="configs/model/openai_subject.json",
        condition_paths=["configs/conditions/baseline.json"],
        scenario_paths=["scenarios/dev/dev_medical_assay_contamination_v1.json"],
        client_mode="live",
        temperature=0.7,
    )
    condition = ConditionRecord(
        condition_id="baseline",
        version="v1",
        instruction_text="Answer directly.",
    )

    kwargs = build_response_request_kwargs(
        model_config=model_config,
        experiment_config=experiment_config,
        condition=condition,
        user_prompt="Hello",
    )

    assert supports_temperature("gpt-4.1-mini") is True
    assert kwargs["temperature"] == 0.7


def test_extract_response_text_tolerates_null_content_items() -> None:
    provider_response = {
        "output": [
            {"id": "item_1", "type": "reasoning", "content": None},
            {
                "id": "item_2",
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "First line"},
                    {"type": "output_text", "text": "Second line"},
                ],
            },
        ]
    }

    assert _extract_response_text(provider_response) == "First line\nSecond line"


def test_build_chat_completion_request_kwargs_uses_messages_and_reasoning_effort() -> None:
    model_config = ModelConfig(model_id="gpt-5-mini", reasoning_effort="low")
    experiment_config = ExperimentConfig(
        run_name="dev",
        model_config_path="configs/model/openai_subject.json",
        condition_paths=["configs/conditions/baseline.json"],
        scenario_paths=["scenarios/dev/dev_medical_assay_contamination_v1.json"],
        client_mode="live",
        temperature=0.7,
        max_output_tokens=123,
    )
    condition = ConditionRecord(
        condition_id="baseline",
        version="v1",
        instruction_text="Answer directly.",
    )

    kwargs = build_chat_completion_request_kwargs(
        model_config=model_config,
        experiment_config=experiment_config,
        condition=condition,
        user_prompt="Hello",
    )

    assert kwargs["messages"] == [
        {"role": "system", "content": "Answer directly."},
        {"role": "user", "content": "Hello"},
    ]
    assert kwargs["max_completion_tokens"] == 123
    assert kwargs["reasoning_effort"] == "low"
    assert "temperature" not in kwargs


def test_extract_chat_completion_text_supports_string_and_list_content() -> None:
    provider_response = {
        "choices": [
            {"message": {"content": "First answer"}},
            {
                "message": {
                    "content": [
                        {"type": "output_text", "text": "Second answer"},
                        {"type": "output_text", "text": "Third answer"},
                    ]
                }
            },
        ]
    }

    assert _extract_chat_completion_text(provider_response) == (
        "First answer\nSecond answer\nThird answer"
    )


def test_detect_openai_api_mode_prefers_responses_then_chat_completions() -> None:
    class ResponsesClient:
        responses = object()

    class ChatNamespace:
        completions = object()

    class ChatClient:
        chat = ChatNamespace()

    class UnsupportedClient:
        pass

    assert _detect_openai_api_mode(ResponsesClient()) == "responses"
    assert _detect_openai_api_mode(ChatClient()) == "chat_completions"
    assert _detect_openai_api_mode(UnsupportedClient()) == "unsupported"


def test_openai_runtime_diagnostics_flags_shell_text(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "source .venv/bin/activate")

    diagnostics = openai_runtime_diagnostics()

    assert diagnostics["is_set"] is True
    assert diagnostics["starts_with_sk"] is False
    assert diagnostics["looks_like_shell_text"] is True
    assert diagnostics["format_ok"] is False
    assert diagnostics["runtime_ready"] is False
    assert diagnostics["api_mode"] in {"responses", "chat_completions", "unsupported", "not_installed"}
