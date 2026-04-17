"""LLM-backed intent resolver for VoicePaste action mode."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import requests

import config
from actions import ActionIntent, ActionRegistry

from prompts import RESOLVER_SYSTEM_PROMPT


@dataclass(frozen=True)
class ResolverDecision:
    """Structured outcome returned by the action resolver."""

    decision: str
    intent: Optional[ActionIntent]
    rationale: str
    telemetry: dict[str, str] = field(default_factory=dict)


class ActionIntentResolver:
    """Resolve spoken action transcripts against the closed v1 action catalog."""

    def __init__(
        self,
        registry: ActionRegistry,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Create the resolver with a stable prompt/version context."""
        self._registry = registry
        self._logger = logger
        self.prompt_version = hashlib.sha256(
            (RESOLVER_SYSTEM_PROMPT + registry.catalog_version()).encode("utf-8")
        ).hexdigest()[:12]

    def resolve(self, transcript: str) -> ResolverDecision:
        """Resolve a spoken transcript into one of the registered action ids."""
        api_key = os.getenv(config.OPENAI_API_KEY_ENV, "").strip()
        if not api_key:
            return ResolverDecision(
                decision="UNAVAILABLE",
                intent=None,
                rationale=f"missing {config.OPENAI_API_KEY_ENV}",
                telemetry=self._telemetry(
                    model=config.ACTION_RESOLVER_MODEL,
                    failure_mode="missing_api_key",
                ),
            )

        payload = {
            "model": config.ACTION_RESOLVER_MODEL,
            "temperature": 0,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": RESOLVER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Transcript:\n{transcript.strip()}"},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.ACTION_RESOLVER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            self._log(f"resolver unavailable: {type(exc).__name__}: {exc}")
            failure_mode = "request_error"
            if isinstance(exc, requests.Timeout):
                failure_mode = "timeout"
            return ResolverDecision(
                decision="UNAVAILABLE",
                intent=None,
                rationale=f"resolver request failed: {type(exc).__name__}",
                telemetry=self._telemetry(
                    model=config.ACTION_RESOLVER_MODEL,
                    failure_mode=failure_mode,
                ),
            )

        content = _extract_content(body)
        if not content:
            return ResolverDecision(
                decision="UNAVAILABLE",
                intent=None,
                rationale="empty resolver response",
                telemetry=self._telemetry(
                    model=config.ACTION_RESOLVER_MODEL,
                    failure_mode="empty_response",
                ),
            )
        parsed = _parse_json(content)
        if parsed is None:
            return ResolverDecision(
                decision="UNAVAILABLE",
                intent=None,
                rationale="invalid resolver json",
                telemetry=self._telemetry(
                    model=config.ACTION_RESOLVER_MODEL,
                    failure_mode="invalid_json",
                ),
            )

        decision = str(parsed.get("decision", "")).strip().upper()
        rationale = str(parsed.get("rationale", "")).strip() or "no rationale"
        confidence_band = str(parsed.get("confidence_band", "")).strip().lower() or "unknown"
        telemetry = self._telemetry(
            model=config.ACTION_RESOLVER_MODEL,
            confidence_band=confidence_band,
        )
        if decision != "MATCH":
            return ResolverDecision(
                decision=decision if decision in {"NO_MATCH", "UNAVAILABLE"} else "NO_MATCH",
                intent=None,
                rationale=rationale,
                telemetry=telemetry,
            )

        action_id = str(parsed.get("action_id", "")).strip()
        if self._registry.get_metadata(action_id) is None:
            return ResolverDecision(
                decision="NO_MATCH",
                intent=None,
                rationale=f"unknown action id {action_id!r}",
                telemetry=telemetry,
            )

        raw_arguments = parsed.get("arguments", {})
        arguments: dict[str, str] = {}
        if isinstance(raw_arguments, dict):
            for key, value in raw_arguments.items():
                if isinstance(key, str) and isinstance(value, str):
                    arguments[key] = value.strip()

        return ResolverDecision(
            decision="MATCH",
            intent=ActionIntent(
                action_id=action_id,
                arguments=arguments,
                rationale=rationale,
            ),
            rationale=rationale,
            telemetry=telemetry,
        )

    def _telemetry(self, **extra: str) -> dict[str, str]:
        """Build common resolver telemetry fields for each decision."""
        telemetry = {
            "resolver_model": config.ACTION_RESOLVER_MODEL,
            "resolver_prompt_version": self.prompt_version,
            "action_catalog_version": self._registry.catalog_version(),
        }
        telemetry.update(extra)
        return telemetry

    def _log(self, message: str) -> None:
        """Emit a resolver-scoped debug line when configured."""
        if self._logger is not None:
            self._logger(f"[action_resolver] {message}")


def _extract_content(body: object) -> str:
    """Extract the text response from a Chat Completions payload."""
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        return ""
    message = choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _parse_json(content: str) -> Optional[dict[str, object]]:
    """Parse a model response that may wrap JSON in a fenced block."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None
