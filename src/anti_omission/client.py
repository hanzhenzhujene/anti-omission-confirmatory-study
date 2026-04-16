from __future__ import annotations

import importlib.metadata
import os
from dataclasses import dataclass
from typing import Any, Optional

from anti_omission.schemas import ConditionRecord, ExperimentConfig, ManifestRow, ModelConfig, ScenarioRecord


@dataclass
class GenerationResult:
    response_text: str
    provider_response: dict[str, Any]
    usage: Optional[dict[str, Any]] = None


class MockSubjectModelClient:
    def generate(
        self,
        *,
        model_config: ModelConfig,
        experiment_config: ExperimentConfig,
        manifest_row: ManifestRow,
        scenario: ScenarioRecord,
        condition: ConditionRecord,
        user_prompt: str,
    ) -> GenerationResult:
        response_text = _mock_response_text(scenario=scenario, condition=condition)
        return GenerationResult(
            response_text=response_text,
            provider_response={
                "mode": "mock",
                "model_id": model_config.model_id,
                "scenario_id": scenario.scenario_id,
                "condition_id": condition.condition_id,
                "user_prompt_excerpt": user_prompt[:120],
            },
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )


class OpenAIResponsesClient:
    def __init__(self, api_key_env_var: str, timeout_seconds: int = 60) -> None:
        raw_key = os.getenv(api_key_env_var) or ""
        api_key = _validated_api_key(raw_key, api_key_env_var)

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for live runs") from exc

        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._sdk_version = _openai_sdk_version()
        self._api_mode = _detect_openai_api_mode(self._client)

    def generate(
        self,
        *,
        model_config: ModelConfig,
        experiment_config: ExperimentConfig,
        manifest_row: ManifestRow,
        scenario: ScenarioRecord,
        condition: ConditionRecord,
        user_prompt: str,
    ) -> GenerationResult:
        if self._api_mode == "responses":
            kwargs = build_response_request_kwargs(
                model_config=model_config,
                experiment_config=experiment_config,
                condition=condition,
                user_prompt=user_prompt,
            )
            response = self._client.responses.create(**kwargs)
            provider_response = response.model_dump() if hasattr(response, "model_dump") else {}
            response_text = getattr(response, "output_text", "") or _extract_response_text(provider_response)
            usage = provider_response.get("usage")
            return GenerationResult(
                response_text=response_text,
                provider_response=provider_response,
                usage=usage,
            )

        if self._api_mode == "chat_completions":
            kwargs = build_chat_completion_request_kwargs(
                model_config=model_config,
                experiment_config=experiment_config,
                condition=condition,
                user_prompt=user_prompt,
            )
            response = self._client.chat.completions.create(**kwargs)
            provider_response = response.model_dump() if hasattr(response, "model_dump") else {}
            provider_response.setdefault("api_mode", "chat_completions")
            response_text = _extract_chat_completion_text(provider_response)
            usage = provider_response.get("usage")
            return GenerationResult(
                response_text=response_text,
                provider_response=provider_response,
                usage=usage,
            )

        raise RuntimeError(
            "Unsupported openai SDK capabilities. "
            f"Installed version: {self._sdk_version or 'unknown'}. "
            "Expected a client with either `responses` or `chat.completions` support."
        )


def build_client(experiment_config: ExperimentConfig, model_config: ModelConfig) -> object:
    if experiment_config.client_mode == "mock":
        return MockSubjectModelClient()
    return OpenAIResponsesClient(
        api_key_env_var=model_config.api_env_var,
        timeout_seconds=model_config.timeout_seconds,
    )


def openai_runtime_diagnostics(api_key_env_var: str = "OPENAI_API_KEY") -> dict[str, Any]:
    raw_key = os.getenv(api_key_env_var, "")
    api_key = raw_key.strip()
    sdk_version = _openai_sdk_version()
    has_newline = ("\n" in raw_key) or ("\r" in raw_key)
    looks_like_shell_text = (
        raw_key.startswith("source ")
        or "python -m" in raw_key
        or "export OPENAI_API_KEY" in raw_key
        or "anti_omission" in raw_key
    )
    format_ok = bool(api_key) and api_key.startswith("sk-") and not has_newline and not looks_like_shell_text

    try:
        from openai import OpenAI
    except ImportError:
        api_mode = "not_installed"
    else:
        client = OpenAI(api_key=api_key or "sk-test")
        api_mode = _detect_openai_api_mode(client)

    return {
        "api_env_var": api_key_env_var,
        "is_set": bool(api_key),
        "starts_with_sk": api_key.startswith("sk-"),
        "has_newline": has_newline,
        "looks_like_shell_text": looks_like_shell_text,
        "format_ok": format_ok,
        "length": len(api_key),
        "sdk_version": sdk_version,
        "api_mode": api_mode,
        "runtime_ready": format_ok and api_mode in {"responses", "chat_completions"},
    }


def build_response_request_kwargs(
    *,
    model_config: ModelConfig,
    experiment_config: ExperimentConfig,
    condition: ConditionRecord,
    user_prompt: str,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model_config.model_id,
        "instructions": condition.instruction_text,
        "input": user_prompt,
        "max_output_tokens": experiment_config.max_output_tokens,
    }
    if supports_temperature(model_config.model_id):
        kwargs["temperature"] = experiment_config.temperature
    if model_config.reasoning_effort:
        kwargs["reasoning"] = {"effort": model_config.reasoning_effort}
    if model_config.text_verbosity:
        kwargs["text"] = {"verbosity": model_config.text_verbosity}
    return kwargs


def build_chat_completion_request_kwargs(
    *,
    model_config: ModelConfig,
    experiment_config: ExperimentConfig,
    condition: ConditionRecord,
    user_prompt: str,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model_config.model_id,
        "messages": [
            {"role": "system", "content": condition.instruction_text},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": experiment_config.max_output_tokens,
    }
    if supports_temperature(model_config.model_id):
        kwargs["temperature"] = experiment_config.temperature
    if model_config.reasoning_effort:
        kwargs["reasoning_effort"] = model_config.reasoning_effort
    return kwargs


def supports_temperature(model_id: str) -> bool:
    normalized = model_id.lower()
    return not normalized.startswith("gpt-5")


def _extract_response_text(provider_response: dict[str, Any]) -> str:
    output = provider_response.get("output", [])
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content") or []
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            text = content.get("text") or content.get("value")
            if text:
                chunks.append(text)
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip())


def _extract_chat_completion_text(provider_response: dict[str, Any]) -> str:
    choices = provider_response.get("choices") or []
    chunks: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") or {}
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            if content.strip():
                chunks.append(content.strip())
            continue
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks)


def _openai_sdk_version() -> str | None:
    try:
        return importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        return None


def _detect_openai_api_mode(client: Any) -> str:
    if hasattr(client, "responses"):
        return "responses"
    chat = getattr(client, "chat", None)
    if chat is not None and hasattr(chat, "completions"):
        return "chat_completions"
    return "unsupported"


def _validated_api_key(raw_key: str, api_key_env_var: str) -> str:
    api_key = raw_key.strip()
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {api_key_env_var}")

    diagnostics = openai_runtime_diagnostics(api_key_env_var)
    if not diagnostics["format_ok"]:
        raise RuntimeError(
            f"{api_key_env_var} does not look like a valid OpenAI API key. "
            "Copy only the raw key string from the OpenAI dashboard, not shell commands or terminal output. "
            f"Observed starts_with_sk={diagnostics['starts_with_sk']}, "
            f"has_newline={diagnostics['has_newline']}, "
            f"looks_like_shell_text={diagnostics['looks_like_shell_text']}, "
            f"length={diagnostics['length']}."
        )
    return api_key


def _mock_response_text(scenario: ScenarioRecord, condition: ConditionRecord) -> str:
    if scenario.materiality == "benign":
        return (
            "The short answer is yes. The internal note does not materially change the user's decision, "
            "so I would answer the narrow question directly."
        )

    if condition.condition_id == "baseline":
        return "Use the requested local answer only and keep the response focused on the narrow question."

    if condition.condition_id == "generic_control":
        return (
            "I can answer the narrow question, but I would also double-check adjacent assumptions before acting "
            "because there may be context that matters."
        )

    if condition.condition_id == "disclosure_compact":
        return (
            f"Before answering directly: {scenario.gold_material_risk_summary}. "
            "That risk should be surfaced before proceeding."
        )

    return (
        f"Before answering the narrow question, I need to flag a material issue: "
        f"{scenario.gold_material_risk_summary}. "
        "I would pause, verify the risk, and only then continue with the requested task."
    )
