"""VoicePaste entry point — wires dictation and action-mode flows together."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import rumps
from faster_whisper import WhisperModel
try:
    import AppKit
except ImportError:
    AppKit = None

import app_logger
import config
import enhancer
import overlay
import paster
import transcriber
from action_resolver import ActionIntentResolver, ResolverDecision
from actions import (
    ActionContext,
    ActionIntent,
    ActionMetadata,
    ActionRegistry,
    build_action_registry,
)
from app_catalog import AppCatalog
from hotkey import HotkeyListener
from recorder import (
    Recorder,
    describe_default_input_device,
    probe_microphone_access,
)


class Mode(Enum):
    """User-facing app modes with menubar icon and terminal status text."""

    IDLE = ("\U0001f399\ufe0f", "VoicePaste ready")
    RECORDING = ("\U0001f534", "\U0001f399\ufe0f Recording...")
    TRANSCRIBING = ("\u23f3", "\U0001f504 Transcribing...")
    ENHANCING = ("\u2728", "\u2728 Enhancing...")
    ACTION_RESOLVING = ("\u23f3", "\u2699\ufe0f Resolving action...")
    ACTION_CONFIRMING = ("\u2753", "Confirm action")
    ACTION_EXECUTING = ("\u2699\ufe0f", "\u2699\ufe0f Running action...")

    @property
    def icon(self) -> str:
        """Return the single-glyph menubar title for this mode."""
        return self.value[0]

    @property
    def message(self) -> str:
        """Return the terminal status line for this mode."""
        return self.value[1]


class InteractionMode(Enum):
    """High-level session type determined by the gesture state machine."""

    DICTATION = "dictation"
    ACTION = "action"


class GestureState(Enum):
    """Low-level session states for dictation and action hotkeys."""

    IDLE = "idle"
    DICTATION_RECORDING = "dictation_recording"
    ACTION_RECORDING = "action_recording"
    DICTATION_PROCESSING = "dictation_processing"
    ACTION_RESOLVING = "action_resolving"
    ACTION_EXECUTING = "action_executing"


@dataclass
class SessionState:
    """Mutable state for one dictation or action-mode gesture sequence."""

    session_id: int
    gesture_state: GestureState
    created_at: float
    interaction_mode: Optional[InteractionMode] = None
    recording_started_at: Optional[float] = None
    transcript: str = ""
    resolved_intent: Optional[ActionIntent] = None
    confirmation_started_at: Optional[float] = None


@dataclass
class AppState:
    """Shared state passed to event handlers and worker threads."""

    app: rumps.App
    logger: app_logger.SessionLogger
    model: WhisperModel
    recorder: Recorder
    app_catalog: AppCatalog
    action_registry: ActionRegistry
    action_resolver: ActionIntentResolver
    hotkey: Optional[HotkeyListener] = None
    overlay_controller: Optional[overlay.FloatingPillController] = None
    mode: Mode = Mode.IDLE
    state_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    current_session: Optional[SessionState] = None
    next_session_id: int = 0


def overlay_mode(mode: Mode) -> overlay.OverlayMode:
    """Map app modes to the simplified floating-pill overlay states."""
    if mode == Mode.RECORDING:
        return overlay.RECORDING_MODE
    if mode == Mode.ACTION_CONFIRMING:
        return overlay.CONFIRMING_MODE
    if mode in {
        Mode.TRANSCRIBING,
        Mode.ENHANCING,
        Mode.ACTION_RESOLVING,
        Mode.ACTION_EXECUTING,
    }:
        return overlay.PROCESSING_MODE
    return overlay.IDLE_MODE


def set_mode(
    state: AppState,
    mode: Mode,
    *,
    overlay_message: Optional[str] = None,
) -> None:
    """Update mode, menubar icon, overlay, and terminal status together."""
    with state.state_lock:
        previous_mode = state.mode
        state.mode = mode
    state.logger.debug(f"[state] mode transition {previous_mode.name} -> {mode.name}")
    state.app.title = mode.icon
    if state.overlay_controller is not None:
        state.overlay_controller.set_mode(overlay_mode(mode), overlay_message)
    if mode == Mode.ACTION_CONFIRMING and overlay_message:
        state.logger.info(f"{mode.message}: {overlay_message}")
    else:
        state.logger.info(mode.message)


def play_feedback_sound(logger: app_logger.SessionLogger, sound_name: str) -> None:
    """Play a short macOS-native feedback sound when enabled."""
    if not config.ENABLE_FEEDBACK_SOUNDS:
        return
    if AppKit is None:
        logger.debug(f"[sound] AppKit unavailable; skipped sound {sound_name!r}")
        return
    try:
        sound = AppKit.NSSound.soundNamed_(sound_name)
        if sound is None:
            logger.debug(f"[sound] sound {sound_name!r} not found")
            return
        played = sound.play()
        if not played:
            logger.debug(f"[sound] sound {sound_name!r} did not start playing")
    except Exception as exc:
        logger.debug(f"[sound] failed to play {sound_name!r}: {type(exc).__name__}: {exc}")


def _next_session(state: AppState, gesture_state: GestureState) -> SessionState:
    """Create and store a new current session under the state lock."""
    state.next_session_id += 1
    session = SessionState(
        session_id=state.next_session_id,
        gesture_state=gesture_state,
        created_at=time.perf_counter(),
    )
    state.current_session = session
    return session


def _clear_session_locked(state: AppState) -> None:
    """Clear session state and timers while holding the state lock."""
    state.current_session = None


def _reset_to_idle(state: AppState, session_id: Optional[int], reason: str) -> None:
    """Return the app to idle when the provided session is still current."""
    with state.state_lock:
        session = state.current_session
        if session_id is not None and (session is None or session.session_id != session_id):
            return
        _clear_session_locked(state)
    state.logger.debug(f"[session {session_id}] returning to idle ({reason})")
    set_mode(state, Mode.IDLE)


def _action_confirmation_message(intent: ActionIntent, metadata: Optional[ActionMetadata]) -> str:
    """Build the short overlay confirmation label for a resolved action."""
    if intent.action_id == "open_app":
        app_query = intent.arguments.get("app_query", "").strip()
        if app_query:
            return f"Open {app_query}?"
    if metadata is not None:
        return f"{metadata.display_name}?"
    return "Confirm action?"


def handle_press(state: AppState) -> None:
    """Start a dictation recording on Right Option press."""
    with state.state_lock:
        session = state.current_session
        if session is not None:
            state.logger.debug(
                f"[session {session.session_id}] ignored press while state={session.gesture_state.value}"
            )
            return
        session = _next_session(state, GestureState.DICTATION_RECORDING)
        session.interaction_mode = InteractionMode.DICTATION
        session.recording_started_at = time.perf_counter()
        session_id = session.session_id

    try:
        state.recorder.start(max_duration=config.MAX_DURATION)
    except Exception as exc:
        state.logger.exception(
            f"\u274c failed to start recording for session {session_id}",
            exc,
        )
        _reset_to_idle(state, session_id, "initial_record_start_failed")
        return
    state.logger.debug(f"[session {session_id}] dictation recording started")
    set_mode(state, Mode.RECORDING)
    play_feedback_sound(state.logger, config.RECORDING_START_SOUND_NAME)


def handle_action_press(state: AppState) -> None:
    """Start action recording on the action hotkey."""
    with state.state_lock:
        session = state.current_session
        if session is None:
            session = _next_session(state, GestureState.ACTION_RECORDING)
            session.interaction_mode = InteractionMode.ACTION
            session.recording_started_at = time.perf_counter()
            session_id = session.session_id
        else:
            state.logger.debug(
                f"[session {session.session_id}] ignored action press while state={session.gesture_state.value}"
            )
            return

    try:
        state.recorder.start(max_duration=config.MAX_ACTION_DURATION_SECONDS)
    except Exception as exc:
        state.logger.exception(
            f"\u274c failed to start action recording for session {session_id}",
            exc,
        )
        _reset_to_idle(state, session_id, "action_record_start_failed")
        return
    state.logger.debug(f"[session {session_id}] action recording started")
    set_mode(state, Mode.RECORDING)
    play_feedback_sound(state.logger, config.RECORDING_START_SOUND_NAME)


def handle_release(state: AppState) -> None:
    """Stop dictation recording on Right Option release."""
    session_id: Optional[int] = None
    with state.state_lock:
        session = state.current_session
        if session is None:
            return
        if session.gesture_state == GestureState.DICTATION_RECORDING:
            session.gesture_state = GestureState.DICTATION_PROCESSING
            session_id = session.session_id
        else:
            return
    threading.Thread(
        target=_process_recording_worker,
        args=(state, session_id, InteractionMode.DICTATION, "dictation_release"),
        name=f"pipeline-worker-{session_id}",
        daemon=True,
    ).start()


def handle_action_release(state: AppState) -> None:
    """Stop action recording on action-hotkey release."""
    with state.state_lock:
        session = state.current_session
        if session is None or session.gesture_state != GestureState.ACTION_RECORDING:
            return
        session.gesture_state = GestureState.ACTION_RESOLVING
        session_id = session.session_id
    threading.Thread(
        target=_process_recording_worker,
        args=(state, session_id, InteractionMode.ACTION, "action_release"),
        name=f"pipeline-worker-{session_id}",
        daemon=True,
    ).start()

def _handle_max_duration(state: AppState) -> None:
    """Kick off the correct processing path when the recorder auto-stops."""
    with state.state_lock:
        session = state.current_session
        if session is None:
            return
        if session.gesture_state == GestureState.DICTATION_RECORDING:
            session.gesture_state = GestureState.DICTATION_PROCESSING
            session_id = session.session_id
            mode = InteractionMode.DICTATION
            reason = "dictation_max_duration"
        elif session.gesture_state == GestureState.ACTION_RECORDING:
            session.gesture_state = GestureState.ACTION_RESOLVING
            session_id = session.session_id
            mode = InteractionMode.ACTION
            reason = "action_max_duration"
        else:
            return
    threading.Thread(
        target=_process_recording_worker,
        args=(state, session_id, mode, reason),
        name=f"max-duration-worker-{session_id}",
        daemon=True,
    ).start()


def _process_recording_worker(
    state: AppState,
    session_id: int,
    interaction_mode: InteractionMode,
    stop_reason: str,
) -> None:
    """Stop the recorder and route the result through dictation or action mode."""
    worker_started = time.perf_counter()
    try:
        stop_started = time.perf_counter()
        result = state.recorder.stop(reason=stop_reason)
        stop_elapsed = time.perf_counter() - stop_started
        audio = result.audio
        state.logger.debug(
            f"[session {session_id}] stop completed "
            f"(mode={interaction_mode.value}, stop_reason={result.stop_reason}, "
            f"previous_stop_reason={result.previous_stop_reason}, duration={result.duration_seconds:.2f}s, "
            f"samples={audio.size}, elapsed={stop_elapsed:.2f}s)"
        )
        if audio.size == 0:
            state.logger.warning("\u26a0\ufe0f  no audio captured \u2014 skipping")
            _reset_to_idle(state, session_id, "no_audio")
            return

        min_samples = int(config.MIN_RECORDING_SECONDS * config.SAMPLE_RATE)
        if audio.size < min_samples:
            seconds = audio.size / config.SAMPLE_RATE
            state.logger.warning(f"\u26a0\ufe0f  clip too short ({seconds:.2f}s) \u2014 skipping")
            _reset_to_idle(state, session_id, "clip_too_short")
            return

        if interaction_mode == InteractionMode.DICTATION:
            _run_dictation_pipeline(state, session_id, audio, stop_elapsed, worker_started)
            return
        _run_action_pipeline(state, session_id, audio, stop_elapsed, worker_started)
    except Exception as exc:
        state.logger.exception(f"\u274c worker error for session {session_id}", exc)
        _reset_to_idle(state, session_id, "worker_exception")


def _run_dictation_pipeline(
    state: AppState,
    session_id: int,
    audio,
    stop_elapsed: float,
    worker_started: float,
) -> None:
    """Run the existing dictation transcription/enhancement/paste flow."""
    set_mode(state, Mode.TRANSCRIBING)
    transcription_started = time.perf_counter()
    text = transcriber.transcribe(state.model, audio, logger=state.logger.debug)
    transcription_elapsed = time.perf_counter() - transcription_started
    if not text:
        state.logger.warning("\u26a0\ufe0f  empty transcription \u2014 skipping")
        _reset_to_idle(state, session_id, "empty_transcription")
        return

    enhancement_elapsed = 0.0
    if (
        config.READABILITY_MODE == "openai"
        and len(text.strip()) >= config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT
    ):
        set_mode(state, Mode.ENHANCING)
    enhancement_started = time.perf_counter()
    final_text = enhancer.enhance(text, logger=state.logger.debug)
    enhancement_elapsed = time.perf_counter() - enhancement_started
    state.logger.transcript(final_text)

    paste_started = time.perf_counter()
    paster.paste(final_text, logger=state.logger.debug)
    paste_elapsed = time.perf_counter() - paste_started
    play_feedback_sound(state.logger, config.PASTE_COMPLETE_SOUND_NAME)
    total_elapsed = time.perf_counter() - worker_started
    state.logger.debug(
        f"[session {session_id}] dictation pipeline completed "
        f"(stop={stop_elapsed:.2f}s, "
        f"transcribe={transcription_elapsed:.2f}s, enhance={enhancement_elapsed:.2f}s, "
        f"execute={paste_elapsed:.2f}s, total={total_elapsed:.2f}s)"
    )
    _reset_to_idle(state, session_id, "dictation_complete")


def _run_action_pipeline(
    state: AppState,
    session_id: int,
    audio,
    stop_elapsed: float,
    worker_started: float,
) -> None:
    """Transcribe and resolve a spoken action request, then wait for confirmation."""
    set_mode(state, Mode.ACTION_RESOLVING)
    transcription_started = time.perf_counter()
    transcript = transcriber.transcribe(state.model, audio, logger=state.logger.debug)
    transcription_elapsed = time.perf_counter() - transcription_started
    if not transcript:
        state.logger.warning("\u26a0\ufe0f  no action recognized")
        play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
        _reset_to_idle(state, session_id, "empty_action_transcript")
        return

    with state.state_lock:
        session = state.current_session
        if session is not None and session.session_id == session_id:
            session.transcript = transcript

    resolve_started = time.perf_counter()
    decision = state.action_resolver.resolve(transcript)
    resolve_elapsed = time.perf_counter() - resolve_started
    _log_resolver_decision(state, session_id, transcript, decision, stop_elapsed, transcription_elapsed, resolve_elapsed)

    if decision.decision != "MATCH" or decision.intent is None:
        if decision.decision == "UNAVAILABLE":
            state.logger.warning("\u26a0\ufe0f  action resolver unavailable")
        else:
            state.logger.warning("\u26a0\ufe0f  no supported action recognized")
        play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
        _reset_to_idle(state, session_id, decision.decision.lower())
        return

    metadata = state.action_registry.get_metadata(decision.intent.action_id)
    if decision.intent.action_id == "open_app":
        confirmation_started = time.perf_counter()
        set_mode(state, Mode.ACTION_CONFIRMING, overlay_message="Edit app name")
        play_feedback_sound(state.logger, config.ACTION_READY_SOUND_NAME)
        edited_query = overlay.prompt_for_inline_text_input(
            title="Open App",
            message="Edit the app name before opening it.",
            initial_value=decision.intent.arguments.get("app_query", "").strip(),
            confirm_title="Open",
            timeout_seconds=config.ACTION_CONFIRMATION_TIMEOUT_SECONDS,
        )
        if not edited_query:
            state.logger.info("\u26a0\ufe0f  app open canceled")
            play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
            _reset_to_idle(state, session_id, "open_app_prompt_canceled")
            return
        edited_intent = ActionIntent(
            action_id=decision.intent.action_id,
            arguments={"app_query": edited_query},
            rationale=decision.intent.rationale,
        )
        with state.state_lock:
            session = state.current_session
            if session is None or session.session_id != session_id:
                return
            session.gesture_state = GestureState.ACTION_EXECUTING
            session.resolved_intent = edited_intent
            session.confirmation_started_at = confirmation_started
        state.logger.debug(
            f"[session {session_id}] open-app prompt confirmed with query={edited_query!r}"
        )
        set_mode(state, Mode.ACTION_EXECUTING)
        threading.Thread(
            target=_execute_action_worker,
            args=(state, session_id, edited_intent),
            name=f"action-worker-{session_id}",
            daemon=True,
        ).start()
        return

    confirmation_message = _action_confirmation_message(decision.intent, metadata)
    state.logger.debug(
        f"[session {session_id}] action confirmation prompt opening "
        f"(resolve={resolve_elapsed:.2f}s, total={time.perf_counter() - worker_started:.2f}s)"
    )
    confirmation_started = time.perf_counter()
    set_mode(state, Mode.ACTION_CONFIRMING, overlay_message=confirmation_message)
    play_feedback_sound(state.logger, config.ACTION_READY_SOUND_NAME)
    approved = overlay.prompt_for_inline_confirmation(
        title=confirmation_message,
        message="Approve this action.",
        confirm_title="Run",
        timeout_seconds=config.ACTION_CONFIRMATION_TIMEOUT_SECONDS,
    )
    if not approved:
        state.logger.info("\u26a0\ufe0f  action canceled")
        play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
        _reset_to_idle(state, session_id, "action_confirmation_canceled")
        return
    with state.state_lock:
        session = state.current_session
        if session is None or session.session_id != session_id:
            return
        session.gesture_state = GestureState.ACTION_EXECUTING
        session.resolved_intent = decision.intent
        session.confirmation_started_at = confirmation_started
    set_mode(state, Mode.ACTION_EXECUTING)
    threading.Thread(
        target=_execute_action_worker,
        args=(state, session_id, decision.intent),
        name=f"action-worker-{session_id}",
        daemon=True,
    ).start()


def _log_resolver_decision(
    state: AppState,
    session_id: int,
    transcript: str,
    decision: ResolverDecision,
    stop_elapsed: float,
    transcription_elapsed: float,
    resolve_elapsed: float,
) -> None:
    """Write one resolver decision record with stable version metadata."""
    intent_id = decision.intent.action_id if decision.intent is not None else ""
    arguments = decision.intent.arguments if decision.intent is not None else {}
    telemetry = ", ".join(f"{key}={value}" for key, value in sorted(decision.telemetry.items()))
    summary = (
        f"[resolver] session={session_id} decision={decision.decision} "
        f"action_id={intent_id!r} arguments={arguments} rationale={decision.rationale!r} "
        f"{telemetry} stop={stop_elapsed:.2f}s "
        f"transcribe={transcription_elapsed:.2f}s resolve={resolve_elapsed:.2f}s"
    )
    state.logger.debug(
        f"{summary} transcript={transcript!r}",
        sensitive=True,
        summary=summary,
    )


def _execute_action_worker(state: AppState, session_id: int, intent: ActionIntent) -> None:
    """Execute one confirmed action through the registry."""
    execution_started = time.perf_counter()
    confirm_wait = 0.0
    with state.state_lock:
        session = state.current_session
        if (
            session is not None
            and session.session_id == session_id
            and session.confirmation_started_at is not None
        ):
            confirm_wait = execution_started - session.confirmation_started_at
    try:
        context = ActionContext(
            logger=state.logger.debug,
            app_catalog=state.app_catalog,
        )
        result = state.action_registry.run(context, intent)
        elapsed = time.perf_counter() - execution_started
        state.logger.debug(
            f"[session {session_id}] action execution finished "
            f"(action_id={intent.action_id}, status={result.status}, "
            f"confirm_wait={confirm_wait:.2f}s, execute={elapsed:.2f}s, "
            f"telemetry={result.telemetry})"
        )
        if result.status == "success":
            state.logger.info(result.user_message)
            play_feedback_sound(state.logger, config.PASTE_COMPLETE_SOUND_NAME)
        else:
            state.logger.warning(f"\u26a0\ufe0f  {result.user_message}")
            play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
    except Exception as exc:
        state.logger.exception(
            f"\u274c action execution failed for session {session_id}",
            exc,
        )
        play_feedback_sound(state.logger, config.ACTION_CANCEL_SOUND_NAME)
    finally:
        _reset_to_idle(state, session_id, "action_complete")


def check_accessibility(logger: app_logger.SessionLogger) -> None:
    """Verify macOS Accessibility permission for the running Python binary."""
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        logger.debug("[startup] ApplicationServices unavailable; skipping explicit Accessibility preflight")
        return
    logger.debug("[startup] checking Accessibility permission")
    if AXIsProcessTrusted():
        logger.debug("[startup] Accessibility permission confirmed")
        return
    logger.error("\u274c Accessibility permission not granted.")
    logger.info("")
    logger.info("   VoicePaste needs Accessibility access to listen for the global")
    logger.info("   hotkey and paste at the cursor (pynput).")
    logger.info("")
    logger.info("   Open System Settings \u2192 Privacy & Security \u2192 Accessibility")
    logger.info("   and enable the Python binary running VoicePaste:")
    logger.info(f"     {sys.executable}")
    logger.info("")
    logger.info("   Then restart VoicePaste.")
    sys.exit(1)


def check_microphone(logger: app_logger.SessionLogger) -> None:
    """Verify microphone access by briefly opening AVFoundation recording."""
    try:
        logger.debug(
            "[startup] default input device snapshot before probe: "
            f"{describe_default_input_device()}"
        )
        logger.debug(
            "[startup] checking microphone access before probe "
            f"(sample_rate={config.SAMPLE_RATE}, channels=1, dtype=float32)"
        )
        probe_microphone_access(logger.debug)
        logger.debug("[startup] microphone access confirmed")
    except Exception as exc:
        logger.exception("\u274c microphone access failed", exc)
        logger.info("")
        logger.info("   Open System Settings \u2192 Privacy & Security \u2192 Microphone")
        logger.info("   and enable the Python binary running VoicePaste:")
        logger.info(f"     {sys.executable}")
        logger.info("")
        logger.info("   Then restart VoicePaste.")
        sys.exit(1)


def main() -> None:
    """Entry point — permission checks, model load, wiring, and app loop."""
    logger = app_logger.SessionLogger(Path(__file__).resolve().parent)
    logger.info("VoicePaste starting\u2026")
    logger.info(f"Session log: {logger.log_path}")
    logger.debug(f"[session] cwd={Path.cwd()} executable={sys.executable}")
    logger.debug(
        "[session] config "
        f"(model={config.MODEL_SIZE}, sample_rate={config.SAMPLE_RATE}, "
        f"dictation_max_duration={config.MAX_DURATION}, "
        f"action_max_duration={config.MAX_ACTION_DURATION_SECONDS}, "
        f"readability_mode={config.READABILITY_MODE}, "
        f"sensitive_logging={config.LOG_SENSITIVE_CONTENT})"
    )

    check_accessibility(logger)
    check_microphone(logger)

    logger.info("Loading Whisper model\u2026")
    try:
        model = transcriber.load_model(logger=logger.debug)
    except Exception as exc:
        logger.exception("\u274c model load failed", exc)
        sys.exit(1)

    app_catalog = AppCatalog(logger.debug)
    action_registry = build_action_registry()
    action_resolver = ActionIntentResolver(action_registry, logger.debug)
    logger.debug(
        "[startup] action system "
        f"(catalog_version={app_catalog.version()}, "
        f"action_catalog_version={action_registry.catalog_version()}, "
        f"resolver_prompt_version={action_resolver.prompt_version}, "
        f"resolver_model={config.ACTION_RESOLVER_MODEL})"
    )

    app = rumps.App("VoicePaste", title=Mode.IDLE.icon, quit_button="Quit")
    state_ref: dict[str, AppState] = {}
    recorder = Recorder(
        logger=logger.debug,
        on_max_duration=lambda: _handle_max_duration(state_ref["state"]),
    )
    state = AppState(
        app=app,
        logger=logger,
        model=model,
        recorder=recorder,
        app_catalog=app_catalog,
        action_registry=action_registry,
        action_resolver=action_resolver,
    )
    state_ref["state"] = state
    try:
        state.overlay_controller = overlay.FloatingPillController()
    except Exception as exc:
        logger.exception("\u26a0\ufe0f  floating pill unavailable", exc)

    listener = HotkeyListener(
        on_press=lambda: handle_press(state),
        on_release=lambda: handle_release(state),
        on_action_press=lambda: handle_action_press(state),
        on_action_release=lambda: handle_action_release(state),
        logger=logger.debug,
    )
    state.hotkey = listener
    listener.start()

    logger.info(Mode.IDLE.message)
    logger.info(
        "Hold Right Option to dictate. Hold Control for actions. "
        "Approve or cancel actions from the inline UI."
    )

    try:
        app.run()
    finally:
        logger.debug("[shutdown] app.run exited; stopping listeners and closing overlay")
        listener.stop()
        recorder.close()
        if state.overlay_controller is not None:
            state.overlay_controller.close()
        logger.debug("[shutdown] cleanup complete")


if __name__ == "__main__":
    main()
