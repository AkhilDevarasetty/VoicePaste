"""Action registry and local desktop action handlers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Mapping, Optional, Protocol

import config
from app_catalog import AppCatalog


@dataclass(frozen=True)
class ActionMetadata:
    """Static metadata describing one voice action."""

    id: str
    display_name: str
    risk_tier: int
    confirmation_required: bool = True
    enabled: bool = True


@dataclass(frozen=True)
class ActionIntent:
    """Resolved action id plus extracted arguments from the resolver."""

    action_id: str
    arguments: Mapping[str, str]
    rationale: str

    def __post_init__(self) -> None:
        """Freeze the argument mapping so intents stay immutable after creation."""
        frozen_arguments = MappingProxyType(dict(self.arguments))
        object.__setattr__(self, "arguments", frozen_arguments)


@dataclass(frozen=True)
class ActionContext:
    """Shared services needed by action handlers."""

    logger: Callable[[str], None]
    app_catalog: AppCatalog


@dataclass(frozen=True)
class ActionResult:
    """Structured action execution outcome for logs and UI feedback."""

    status: str
    user_message: str
    execution_summary: str
    telemetry: dict[str, str] = field(default_factory=dict)


class ActionHandler(Protocol):
    """Interface every action handler must follow."""

    def run(self, context: ActionContext, intent: ActionIntent) -> ActionResult:
        """Execute the resolved action."""


class ScreenshotActionHandler:
    """Capture a full-screen screenshot to the clipboard."""

    def run(self, context: ActionContext, intent: ActionIntent) -> ActionResult:
        """Execute the screenshot command through the macOS screencapture tool."""
        try:
            subprocess.run(
                ["screencapture", "-c", "-x"],
                check=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            telemetry = {"action_id": intent.action_id}
            if isinstance(exc, subprocess.CalledProcessError):
                telemetry["returncode"] = str(exc.returncode)
            elif isinstance(exc, subprocess.TimeoutExpired):
                telemetry["timeout_seconds"] = str(exc.timeout)
            elif isinstance(exc, OSError) and exc.errno is not None:
                telemetry["errno"] = str(exc.errno)
            return ActionResult(
                status="failed",
                user_message="Screenshot failed.",
                execution_summary=f"screencapture failed: {type(exc).__name__}",
                telemetry=telemetry,
            )
        return ActionResult(
            status="success",
            user_message="Screenshot copied to clipboard.",
            execution_summary="screencapture clipboard capture",
            telemetry={"action_id": intent.action_id},
        )


class OpenAppActionHandler:
    """Open or foreground a local macOS app bundle."""

    def run(self, context: ActionContext, intent: ActionIntent) -> ActionResult:
        """Resolve the requested app locally, then launch it via macOS open."""
        app_query = intent.arguments.get("app_query", "").strip()
        resolution = context.app_catalog.resolve(app_query)
        if resolution.status != "matched" or resolution.target is None:
            reason = resolution.reason or resolution.status
            return ActionResult(
                status="failed",
                user_message=f"Couldn't resolve app '{app_query}'.",
                execution_summary=f"open_app failed ({reason})",
                telemetry={
                    "action_id": intent.action_id,
                    "app_query": app_query,
                    "catalog_status": resolution.status,
                    "catalog_reason": reason,
                },
            )
        try:
            subprocess.run(
                ["open", "-a", str(resolution.target.path)],
                check=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            telemetry = {
                "action_id": intent.action_id,
                "app_query": app_query,
                "resolved_app": resolution.target.display_name,
            }
            if isinstance(exc, subprocess.CalledProcessError):
                telemetry["returncode"] = str(exc.returncode)
            elif isinstance(exc, subprocess.TimeoutExpired):
                telemetry["timeout_seconds"] = str(exc.timeout)
            elif isinstance(exc, OSError) and exc.errno is not None:
                telemetry["errno"] = str(exc.errno)
            return ActionResult(
                status="failed",
                user_message=f"Couldn't open {resolution.target.display_name}.",
                execution_summary=f"open_app subprocess failed: {type(exc).__name__}",
                telemetry=telemetry,
            )
        return ActionResult(
            status="success",
            user_message=f"Opened {resolution.target.display_name}.",
            execution_summary=f"open app {resolution.target.display_name}",
            telemetry={
                "action_id": intent.action_id,
                "app_query": app_query,
                "resolved_app": resolution.target.display_name,
            },
        )


class ActionRegistry:
    """Store action metadata and handlers behind stable action ids."""

    def __init__(self) -> None:
        """Create the v1 action registry."""
        self._metadata: dict[str, ActionMetadata] = {}
        self._handlers: dict[str, ActionHandler] = {}

    def register(
        self,
        metadata: ActionMetadata,
        handler: ActionHandler,
    ) -> None:
        """Register one action handler and its metadata."""
        self._metadata[metadata.id] = metadata
        self._handlers[metadata.id] = handler

    def get_metadata(self, action_id: str) -> Optional[ActionMetadata]:
        """Return metadata for an action id when registered."""
        metadata = self._metadata.get(action_id)
        if metadata is None:
            return None
        if action_id in config.DISABLED_ACTIONS:
            return ActionMetadata(
                id=metadata.id,
                display_name=metadata.display_name,
                risk_tier=metadata.risk_tier,
                confirmation_required=metadata.confirmation_required,
                enabled=False,
            )
        return metadata

    def run(self, context: ActionContext, intent: ActionIntent) -> ActionResult:
        """Execute the action handler for the provided intent."""
        metadata = self.get_metadata(intent.action_id)
        if metadata is None:
            return ActionResult(
                status="failed",
                user_message="Unknown action.",
                execution_summary=f"missing handler for {intent.action_id}",
                telemetry={"action_id": intent.action_id},
            )
        if not metadata.enabled:
            return ActionResult(
                status="failed",
                user_message="That action is disabled.",
                execution_summary=f"disabled action {intent.action_id}",
                telemetry={"action_id": intent.action_id},
            )
        handler = self._handlers[intent.action_id]
        return handler.run(context, intent)

    def catalog_version(self) -> str:
        """Return a stable version string for the registered action ids."""
        version_parts: list[str] = []
        for action_id in sorted(self._metadata):
            metadata = self.get_metadata(action_id)
            if metadata is None:
                continue
            version_parts.append(
                f"{metadata.id}:{metadata.display_name}:{int(metadata.enabled)}"
            )
        return "|".join(version_parts)


def build_action_registry() -> ActionRegistry:
    """Create the v1 action registry with its two local desktop actions."""
    registry = ActionRegistry()
    registry.register(
        ActionMetadata(
            id="take_screenshot",
            display_name="Take Screenshot",
            risk_tier=1,
        ),
        ScreenshotActionHandler(),
    )
    registry.register(
        ActionMetadata(
            id="open_app",
            display_name="Open App",
            risk_tier=1,
        ),
        OpenAppActionHandler(),
    )
    return registry
