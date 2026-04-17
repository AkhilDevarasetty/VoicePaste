"""Test cases that encode the V1 agent-actions code-review findings.

Each test is pinned to one finding from the review. The tests are written to
FAIL against the current implementation and PASS once the corresponding fix
is applied. Finding numbers match the review comment numbering.

Scope: non-hotkey findings only.

Run: python -m unittest test_agent_actions_review -v
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import config
from action_resolver import ActionIntentResolver, ResolverDecision
from actions import (
    ActionContext,
    ActionIntent,
    ActionMetadata,
    ActionRegistry,
    OpenAppActionHandler,
    ScreenshotActionHandler,
    build_action_registry,
)
from app_catalog import AppCatalog, AppResolution, AppTarget


# --------------------------------------------------------------------------- #
# Finding 3 — Shell failures must flow through ActionResult, not exceptions.
# --------------------------------------------------------------------------- #
class ShellFailureReturnsActionResultTests(unittest.TestCase):
    """Handlers must catch subprocess errors and return status='failed'."""

    def test_screenshot_returns_failed_on_nonzero_exit(self) -> None:
        """CalledProcessError from screencapture must not escape the handler."""
        handler = ScreenshotActionHandler()
        intent = ActionIntent(action_id="take_screenshot", arguments={}, rationale="test")
        context = ActionContext(logger=lambda _m: None, app_catalog=MagicMock())
        error = subprocess.CalledProcessError(returncode=1, cmd=["screencapture"])
        with patch("actions.subprocess.run", side_effect=error):
            result = handler.run(context, intent)
        self.assertEqual(result.status, "failed")
        self.assertIn("returncode", result.telemetry)

    def test_screenshot_returns_failed_on_timeout(self) -> None:
        """TimeoutExpired must not escape the handler."""
        handler = ScreenshotActionHandler()
        intent = ActionIntent(action_id="take_screenshot", arguments={}, rationale="test")
        context = ActionContext(logger=lambda _m: None, app_catalog=MagicMock())
        with patch(
            "actions.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="screencapture", timeout=10),
        ):
            result = handler.run(context, intent)
        self.assertEqual(result.status, "failed")

    def test_open_app_returns_failed_when_launch_errors(self) -> None:
        """`open -a` failure must return ActionResult('failed'), not raise."""
        handler = OpenAppActionHandler()
        target = AppTarget(display_name="Slack", path=Path("/Applications/Slack.app"), bundle_id=None)
        catalog = MagicMock()
        catalog.resolve.return_value = AppResolution(status="matched", query="slack", target=target)
        context = ActionContext(logger=lambda _m: None, app_catalog=catalog)
        intent = ActionIntent(action_id="open_app", arguments={"app_query": "Slack"}, rationale="t")
        error = subprocess.CalledProcessError(returncode=1, cmd=["open", "-a", "Slack"])
        with patch("actions.subprocess.run", side_effect=error):
            result = handler.run(context, intent)
        self.assertEqual(result.status, "failed")
        self.assertIn("returncode", result.telemetry)


# --------------------------------------------------------------------------- #
# Finding 7 — catalog_version must reflect DISABLED_ACTIONS.
# --------------------------------------------------------------------------- #
class CatalogVersionReflectsDisabledActionsTests(unittest.TestCase):
    """Two runs with different disabled-action sets must have different versions."""

    def setUp(self) -> None:
        self._original_disabled = config.DISABLED_ACTIONS

    def tearDown(self) -> None:
        config.DISABLED_ACTIONS = self._original_disabled

    def test_disabling_an_action_changes_catalog_version(self) -> None:
        registry = build_action_registry()
        config.DISABLED_ACTIONS = ()
        version_enabled = registry.catalog_version()
        config.DISABLED_ACTIONS = ("take_screenshot",)
        version_partly_disabled = registry.catalog_version()
        self.assertNotEqual(version_enabled, version_partly_disabled)


# --------------------------------------------------------------------------- #
# Finding 10 — OpenAI call must use response_format={"type":"json_object"}.
# --------------------------------------------------------------------------- #
class ResolverUsesJsonResponseFormatTests(unittest.TestCase):
    """The resolver must pin JSON-mode on the Chat Completions request."""

    def test_payload_includes_response_format_json_object(self) -> None:
        registry = build_action_registry()
        resolver = ActionIntentResolver(registry, logger=lambda _m: None)

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "decision": "NO_MATCH",
                                "action_id": "",
                                "arguments": {},
                                "rationale": "n/a",
                                "confidence_band": "low",
                            }
                        )
                    }
                }
            ]
        }

        with patch.dict("os.environ", {config.OPENAI_API_KEY_ENV: "sk-test"}):
            with patch("action_resolver.requests.post", return_value=fake_response) as post:
                resolver.resolve("hello")

        _args, kwargs = post.call_args
        payload = kwargs.get("json") or {}
        self.assertEqual(
            payload.get("response_format"),
            {"type": "json_object"},
            "resolver must pin response_format to json_object",
        )


# --------------------------------------------------------------------------- #
# Finding 9 — max_tokens must be generous enough to fit a rationale.
# --------------------------------------------------------------------------- #
class ResolverMaxTokensTests(unittest.TestCase):
    """max_tokens should be at least 300 so JSON output is not truncated."""

    def test_payload_max_tokens_at_least_300(self) -> None:
        registry = build_action_registry()
        resolver = ActionIntentResolver(registry, logger=lambda _m: None)
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "choices": [{"message": {"content": '{"decision":"NO_MATCH"}'}}]
        }
        with patch.dict("os.environ", {config.OPENAI_API_KEY_ENV: "sk-test"}):
            with patch("action_resolver.requests.post", return_value=fake_response) as post:
                resolver.resolve("hi")
        _args, kwargs = post.call_args
        payload = kwargs.get("json") or {}
        self.assertGreaterEqual(payload.get("max_tokens", 0), 300)


# --------------------------------------------------------------------------- #
# Finding 11 — resolver_prompt_version must change when the action argument
# schema changes, even if action ids stay the same.
# --------------------------------------------------------------------------- #
class ResolverPromptVersionCoversArgumentSchemaTests(unittest.TestCase):
    """Argument-signature changes must flip prompt_version."""

    def test_prompt_version_changes_when_arguments_change(self) -> None:
        # Two registries with identical ids but conceptually different argument
        # surfaces should produce different prompt_versions. The current
        # implementation only hashes ids, so this test fails today.
        registry_a = ActionRegistry()
        registry_a.register(
            ActionMetadata(id="open_app", display_name="Open App", risk_tier=1),
            OpenAppActionHandler(),
        )
        resolver_a = ActionIntentResolver(registry_a, logger=None)

        registry_b = ActionRegistry()
        registry_b.register(
            ActionMetadata(id="open_app", display_name="Open App", risk_tier=1),
            OpenAppActionHandler(),
        )
        # Simulate a future arg-schema change by attaching extra metadata.
        # The resolver must incorporate per-action argument signatures, not
        # just ids. This assertion documents the requirement.
        registry_b._metadata["open_app"] = ActionMetadata(  # type: ignore[attr-defined]
            id="open_app",
            display_name="Open App v2",
            risk_tier=1,
        )
        resolver_b = ActionIntentResolver(registry_b, logger=None)

        # Different display_name should be reflected in version OR argument
        # signature should be part of the hash. Either way the versions
        # should differ. Current code returns the same hash.
        self.assertNotEqual(
            resolver_a.prompt_version,
            resolver_b.prompt_version,
            "prompt_version must cover action schema, not just ids",
        )


# --------------------------------------------------------------------------- #
# Finding 5 / 6 — AppCatalog should not rglob and should not refresh twice
# on a cold miss inside a single resolve call.
# --------------------------------------------------------------------------- #
class AppCatalogScanEfficiencyTests(unittest.TestCase):
    """Catalog scanning must use shallow globs and must not double-walk."""

    def test_catalog_does_not_use_rglob(self) -> None:
        """Catalog must not recurse into nested .app bundles."""
        with patch("app_catalog.Path.rglob") as rglob, patch("app_catalog.Path.glob") as glob:
            rglob.return_value = iter([])
            glob.return_value = iter([])
            AppCatalog(logger=lambda _m: None)
        self.assertFalse(
            rglob.called,
            "AppCatalog must use shallow glob('*.app'), not rglob",
        )

    def test_resolve_miss_does_not_refresh_more_than_once(self) -> None:
        """A single resolve() call must trigger at most one refresh."""
        catalog = AppCatalog(logger=lambda _m: None)
        refresh_calls = {"n": 0}
        original_refresh = catalog.refresh

        def counting_refresh() -> None:
            refresh_calls["n"] += 1
            original_refresh()

        with patch.object(catalog, "refresh", side_effect=counting_refresh):
            catalog.resolve("definitely-not-an-app-xyz-12345")
        self.assertLessEqual(refresh_calls["n"], 1)


# --------------------------------------------------------------------------- #
# Finding 1 — Inline editor must have a timeout so a parked session cannot
# lock the action state machine forever.
# --------------------------------------------------------------------------- #
class InlineEditorTimeoutTests(unittest.TestCase):
    """Inline app-name editor must accept and honor a timeout."""

    def test_prompt_signature_exposes_timeout(self) -> None:
        import inspect

        import overlay

        sig = inspect.signature(overlay.prompt_for_inline_text_input)
        self.assertIn(
            "timeout_seconds",
            sig.parameters,
            "prompt_for_inline_text_input must accept timeout_seconds",
        )

    def test_prompt_returns_none_on_timeout(self) -> None:
        """If the editor times out without user input, it must return None."""
        import overlay

        if overlay.AppKit is None:  # Non-macOS CI path — skip the AppKit test.
            self.skipTest("AppKit unavailable; timeout path cannot run here")

        start = time.perf_counter()
        # Run the editor on a worker thread so the modal cannot block the test.
        result: dict[str, object] = {}

        def _call() -> None:
            result["value"] = overlay.prompt_for_inline_text_input(
                title="Open App",
                message="x",
                initial_value="Slack",
                confirm_title="Open",
                timeout_seconds=0.2,
            )

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()
        thread.join(timeout=3.0)
        elapsed = time.perf_counter() - start
        self.assertFalse(thread.is_alive(), "editor must return after timeout")
        self.assertIsNone(result.get("value"))
        self.assertLess(elapsed, 3.0)


# --------------------------------------------------------------------------- #
# Finding 2 — Activation-policy restore must be guarded against exceptions.
# --------------------------------------------------------------------------- #
class ActivationPolicyRestoreTests(unittest.TestCase):
    """Activation policy must be restored even if the modal raises."""

    def test_policy_restored_when_modal_raises(self) -> None:
        import overlay

        if overlay.AppKit is None:
            self.skipTest("AppKit unavailable")

        app = overlay.AppKit.NSApplication.sharedApplication()
        original_policy = app.activationPolicy()

        with patch.object(
            overlay.AppKit.NSApplication,
            "runModalForWindow_",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                overlay.prompt_for_inline_text_input(
                    title="t", message="m", initial_value="x", confirm_title="Open",
                )
        self.assertEqual(
            app.activationPolicy(),
            original_policy,
            "activation policy must be restored after modal raises",
        )


# --------------------------------------------------------------------------- #
# Finding 4 — Confirmation UX consistency: open_app must honor the shared
# confirmation-timeout contract. The editor path must not bypass the timeout
# that take_screenshot uses.
# --------------------------------------------------------------------------- #
class OpenAppConfirmationTimeoutTests(unittest.TestCase):
    """open_app editor must share the same timeout as other tier-1 actions."""

    def test_open_app_prompt_uses_confirmation_timeout_constant(self) -> None:
        """main.py must pass ACTION_CONFIRMATION_TIMEOUT_SECONDS (or a larger
        dedicated edit timeout constant) into the inline editor."""
        import inspect

        import main as main_module

        source = inspect.getsource(main_module._run_action_pipeline)
        self.assertIn(
            "timeout_seconds",
            source,
            "open_app path must pass timeout_seconds into the inline editor",
        )


# --------------------------------------------------------------------------- #
# Finding 17 — ActionIntent is frozen but exposes a mutable dict.
# --------------------------------------------------------------------------- #
class ActionIntentArgumentsImmutabilityTests(unittest.TestCase):
    """ActionIntent.arguments must be an immutable mapping."""

    def test_arguments_reject_mutation(self) -> None:
        intent = ActionIntent(action_id="open_app", arguments={"app_query": "Slack"}, rationale="t")
        with self.assertRaises((TypeError, AttributeError)):
            intent.arguments["app_query"] = "NotSlack"  # type: ignore[index]


# --------------------------------------------------------------------------- #
# Finding 13 — Dead handle_key_release wiring must be removed or given a job.
# --------------------------------------------------------------------------- #
class DeadKeyReleaseHandlerTests(unittest.TestCase):
    """handle_key_release must either be removed or do real work."""

    def test_handle_key_release_is_not_a_stub(self) -> None:
        import inspect

        import main as main_module

        if not hasattr(main_module, "handle_key_release"):
            return  # Removed — acceptable outcome.
        source = inspect.getsource(main_module.handle_key_release)
        # Strip decorators/docstring/whitespace and check there is a real body.
        meaningful_lines = [
            line.strip()
            for line in source.splitlines()
            if line.strip()
            and not line.strip().startswith(('"""', "#", "def ", "@"))
        ]
        self.assertTrue(
            meaningful_lines,
            "handle_key_release is a stub — remove it or implement it",
        )


# --------------------------------------------------------------------------- #
# Finding 8 — Indistinguishable UNAVAILABLE reasons: malformed-success vs.
# timeout must be distinguishable in telemetry.
# --------------------------------------------------------------------------- #
class ResolverTelemetryDistinguishesFailureModesTests(unittest.TestCase):
    """Different UNAVAILABLE causes must produce different telemetry/rationale."""

    def test_malformed_success_vs_timeout_differ(self) -> None:
        registry = build_action_registry()
        resolver = ActionIntentResolver(registry, logger=lambda _m: None)

        # Case A: malformed 200 response (empty content).
        malformed = MagicMock()
        malformed.raise_for_status = MagicMock()
        malformed.json.return_value = {"choices": [{"message": {"content": ""}}]}
        with patch.dict("os.environ", {config.OPENAI_API_KEY_ENV: "sk-test"}):
            with patch("action_resolver.requests.post", return_value=malformed):
                decision_malformed = resolver.resolve("hi")

        # Case B: network/timeout failure.
        import requests

        with patch.dict("os.environ", {config.OPENAI_API_KEY_ENV: "sk-test"}):
            with patch(
                "action_resolver.requests.post",
                side_effect=requests.Timeout("slow"),
            ):
                decision_timeout = resolver.resolve("hi")

        self.assertEqual(decision_malformed.decision, "UNAVAILABLE")
        self.assertEqual(decision_timeout.decision, "UNAVAILABLE")
        self.assertNotEqual(
            (decision_malformed.rationale, decision_malformed.telemetry.get("failure_mode")),
            (decision_timeout.rationale, decision_timeout.telemetry.get("failure_mode")),
            "telemetry must distinguish malformed-success from timeout/network",
        )


if __name__ == "__main__":
    unittest.main()
