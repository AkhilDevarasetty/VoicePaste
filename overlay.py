"""Bottom-center floating pill overlay for VoicePaste."""

from __future__ import annotations

import math
import threading
import time
from typing import Final, Literal, Optional

import AppKit
import objc
from PyObjCTools import AppHelper

import config

# Replace the native selector with a thin Python wrapper so unittest.mock can
# patch and restore it reliably in tests.
_NATIVE_RUN_MODAL_SELECTOR = AppKit.NSApplication.runModalForWindow_


def _run_modal_for_window(self, window):
    """Delegate to the native modal runner through a patchable Python method."""
    return _NATIVE_RUN_MODAL_SELECTOR(self, window)


AppKit.NSApplication.runModalForWindow_ = _run_modal_for_window

OverlayMode = Literal["idle", "recording", "processing", "confirming"]
IDLE_MODE: Final[OverlayMode] = "idle"
RECORDING_MODE: Final[OverlayMode] = "recording"
PROCESSING_MODE: Final[OverlayMode] = "processing"
CONFIRMING_MODE: Final[OverlayMode] = "confirming"


def _max_pill_width() -> float:
    """Return the widest pill width across all overlay states."""
    return max(
        config.OVERLAY_IDLE_WIDTH,
        config.OVERLAY_RECORDING_WIDTH,
        config.OVERLAY_PROCESSING_WIDTH,
        config.OVERLAY_CONFIRMING_WIDTH,
    )


def _max_pill_height() -> float:
    """Return the tallest pill height across all overlay states."""
    return max(
        config.OVERLAY_IDLE_HEIGHT,
        config.OVERLAY_RECORDING_HEIGHT,
        config.OVERLAY_PROCESSING_HEIGHT,
        config.OVERLAY_CONFIRMING_HEIGHT,
    )


def _canvas_width() -> float:
    """Return the transparent window width needed for pill plus glow."""
    return _max_pill_width() + (config.OVERLAY_CANVAS_PADDING_X * 2.0)


def _canvas_height() -> float:
    """Return the transparent window height needed for pill plus glow."""
    return _max_pill_height() + (config.OVERLAY_CANVAS_PADDING_Y * 2.0)


def _pill_size(mode: OverlayMode) -> tuple[float, float]:
    """Return the target pill size for a given overlay mode."""
    if mode == RECORDING_MODE:
        return config.OVERLAY_RECORDING_WIDTH, config.OVERLAY_RECORDING_HEIGHT
    if mode == PROCESSING_MODE:
        return config.OVERLAY_PROCESSING_WIDTH, config.OVERLAY_PROCESSING_HEIGHT
    if mode == CONFIRMING_MODE:
        return config.OVERLAY_CONFIRMING_WIDTH, config.OVERLAY_CONFIRMING_HEIGHT
    return config.OVERLAY_IDLE_WIDTH, config.OVERLAY_IDLE_HEIGHT


def _fixed_screen_frame() -> AppKit.NSRect:
    """Return the stable screen frame used for the floating pill."""
    main_screen = AppKit.NSScreen.mainScreen()
    if main_screen is not None:
        return main_screen.visibleFrame()
    # Defensive fallback for cases where AppKit cannot report displays yet.
    return AppKit.NSMakeRect(
        0.0,
        0.0,
        config.OVERLAY_FALLBACK_SCREEN_WIDTH,
        config.OVERLAY_FALLBACK_SCREEN_HEIGHT,
    )


def _color(red: float, green: float, blue: float, alpha: float) -> AppKit.NSColor:
    """Create an sRGB color for custom overlay drawing."""
    return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
        red,
        green,
        blue,
        alpha,
    )


def _draw_centered_rounded_rect(
    rect: AppKit.NSRect,
    color: AppKit.NSColor,
    glow: bool,
    border_alpha: float,
) -> None:
    """Draw the pill body with a soft shadow and optional recording glow."""
    radius = rect.size.height * config.OVERLAY_CORNER_RADIUS_MULTIPLIER
    shadow = AppKit.NSShadow.alloc().init()
    shadow.setShadowBlurRadius_(config.OVERLAY_SHADOW_BLUR)
    shadow.setShadowOffset_(
        AppKit.NSMakeSize(
            config.OVERLAY_SHADOW_OFFSET_X,
            config.OVERLAY_SHADOW_OFFSET_Y,
        ),
    )
    shadow.setShadowColor_(
        _color(0.0, 0.0, 0.0, config.OVERLAY_SHADOW_ALPHA),
    )
    AppKit.NSGraphicsContext.saveGraphicsState()
    shadow.set()
    if glow:
        glow_rect = AppKit.NSInsetRect(
            rect,
            -config.OVERLAY_RECORDING_GLOW_PADDING_X,
            -config.OVERLAY_RECORDING_GLOW_PADDING_Y,
        )
        glow_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            glow_rect,
            glow_rect.size.height * config.OVERLAY_CORNER_RADIUS_MULTIPLIER,
            glow_rect.size.height * config.OVERLAY_CORNER_RADIUS_MULTIPLIER,
        )
        _color(
            config.OVERLAY_RECORDING_GLOW_RED,
            config.OVERLAY_RECORDING_GLOW_GREEN,
            config.OVERLAY_RECORDING_GLOW_BLUE,
            config.OVERLAY_RECORDING_GLOW_ALPHA,
        ).setFill()
        glow_path.fill()
    path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        rect,
        radius,
        radius,
    )
    color.setFill()
    path.fill()
    _color(1.0, 1.0, 1.0, border_alpha).setStroke()
    path.setLineWidth_(config.OVERLAY_BORDER_WIDTH)
    path.stroke()
    AppKit.NSGraphicsContext.restoreGraphicsState()


def _draw_recording_bars(rect: AppKit.NSRect, elapsed: float) -> None:
    """Draw animated waveform bars inside the recording pill."""
    total_width = (
        config.OVERLAY_RECORDING_BAR_COUNT * config.OVERLAY_RECORDING_BAR_WIDTH
        + (config.OVERLAY_RECORDING_BAR_COUNT - 1) * config.OVERLAY_RECORDING_BAR_GAP
    )
    left = rect.origin.x + ((rect.size.width - total_width) / 2.0)
    center_y = rect.origin.y + (rect.size.height / 2.0)
    bar_color = _color(
        config.OVERLAY_RECORDING_BAR_RED,
        config.OVERLAY_RECORDING_BAR_GREEN,
        config.OVERLAY_RECORDING_BAR_BLUE,
        config.OVERLAY_RECORDING_BAR_ALPHA,
    )
    for index in range(config.OVERLAY_RECORDING_BAR_COUNT):
        phase = (
            elapsed * config.OVERLAY_RECORDING_BAR_PHASE_SPEED
            + (index * config.OVERLAY_RECORDING_BAR_PHASE_STAGGER)
        )
        amplitude = 0.45 + (0.55 * ((math.sin(phase) + 1.0) / 2.0))
        bar_height = config.OVERLAY_RECORDING_BAR_MIN_HEIGHT + (
            (config.OVERLAY_RECORDING_BAR_MAX_HEIGHT - config.OVERLAY_RECORDING_BAR_MIN_HEIGHT)
            * amplitude
        )
        bar_rect = AppKit.NSMakeRect(
            left + index * (config.OVERLAY_RECORDING_BAR_WIDTH + config.OVERLAY_RECORDING_BAR_GAP),
            center_y - (bar_height / 2.0),
            config.OVERLAY_RECORDING_BAR_WIDTH,
            bar_height,
        )
        radius = config.OVERLAY_RECORDING_BAR_WIDTH / 2.0
        path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bar_rect,
            radius,
            radius,
        )
        bar_color.setFill()
        path.fill()


def _draw_processing_dots(rect: AppKit.NSRect, elapsed: float) -> None:
    """Draw looping amber dots inside the processing pill."""
    total_width = (
        config.OVERLAY_PROCESSING_DOT_COUNT * config.OVERLAY_PROCESSING_DOT_SIZE
        + (config.OVERLAY_PROCESSING_DOT_COUNT - 1) * config.OVERLAY_PROCESSING_DOT_GAP
    )
    left = rect.origin.x + ((rect.size.width - total_width) / 2.0)
    base_y = rect.origin.y + ((rect.size.height - config.OVERLAY_PROCESSING_DOT_SIZE) / 2.0)
    for index in range(config.OVERLAY_PROCESSING_DOT_COUNT):
        phase = (
            elapsed / config.OVERLAY_PROCESSING_CYCLE_SECONDS
            - (index * config.OVERLAY_PROCESSING_DOT_PHASE_STAGGER)
        )
        intensity = 0.35 + (0.65 * ((math.sin(phase * math.tau) + 1.0) / 2.0))
        dot_rect = AppKit.NSMakeRect(
            left + index * (config.OVERLAY_PROCESSING_DOT_SIZE + config.OVERLAY_PROCESSING_DOT_GAP),
            base_y - (config.OVERLAY_PROCESSING_DOT_BOUNCE_DISTANCE * intensity),
            config.OVERLAY_PROCESSING_DOT_SIZE,
            config.OVERLAY_PROCESSING_DOT_SIZE,
        )
        path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(dot_rect)
        _color(
            config.OVERLAY_PROCESSING_DOT_RED,
            config.OVERLAY_PROCESSING_DOT_GREEN,
            config.OVERLAY_PROCESSING_DOT_BLUE,
            config.OVERLAY_PROCESSING_DOT_ALPHA_BASE
            + (config.OVERLAY_PROCESSING_DOT_ALPHA_RANGE * intensity),
        ).setFill()
        path.fill()


def _truncate_message(message: str) -> str:
    """Trim long overlay labels so the pill stays compact and readable."""
    cleaned = " ".join(message.split())
    limit = config.OVERLAY_CONFIRMING_MESSAGE_MAX_CHARS
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _draw_centered_text(rect: AppKit.NSRect, message: str) -> None:
    """Draw one centered confirmation label inside the pill."""
    paragraph_style = AppKit.NSParagraphStyle.defaultParagraphStyle().mutableCopy()
    paragraph_style.setAlignment_(AppKit.NSTextAlignmentCenter)
    attributes = {
        AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_weight_(
            config.OVERLAY_CONFIRMING_FONT_SIZE,
            AppKit.NSFontWeightMedium,
        ),
        AppKit.NSForegroundColorAttributeName: _color(
            config.OVERLAY_CONFIRMING_TEXT_RED,
            config.OVERLAY_CONFIRMING_TEXT_GREEN,
            config.OVERLAY_CONFIRMING_TEXT_BLUE,
            config.OVERLAY_CONFIRMING_TEXT_ALPHA,
        ),
        AppKit.NSParagraphStyleAttributeName: paragraph_style,
    }
    attributed_string = AppKit.NSAttributedString.alloc().initWithString_attributes_(
        _truncate_message(message),
        attributes,
    )
    text_size = attributed_string.size()
    text_rect = AppKit.NSMakeRect(
        rect.origin.x + ((rect.size.width - text_size.width) / 2.0),
        rect.origin.y + ((rect.size.height - text_size.height) / 2.0),
        text_size.width,
        text_size.height,
    )
    attributed_string.drawInRect_(text_rect)


class FloatingPillView(AppKit.NSView):
    """Transparent view that paints the VoicePaste pill states."""

    def initWithFrame_(self, frame: AppKit.NSRect) -> "FloatingPillView":
        """Initialize the overlay view with its first idle-state timing."""
        self = objc.super(FloatingPillView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._mode: OverlayMode = IDLE_MODE
        self._target_width, self._target_height = _pill_size(IDLE_MODE)
        self._previous_width, self._previous_height = self._target_width, self._target_height
        self._mode_started_at = time.monotonic()
        self._transition_started_at = self._mode_started_at
        self._timer = None
        self._message = ""
        return self

    def isOpaque(self) -> bool:
        """Declare the view transparent so the window can remain borderless."""
        return False

    def start_animation(self) -> None:
        """Start the redraw timer that powers recording and processing motion."""
        if self._timer is not None:
            return
        self._timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / config.OVERLAY_ANIMATION_FPS,
            self,
            "tick:",
            None,
            True,
        )

    def stop_animation(self) -> None:
        """Stop the redraw timer when the overlay is being torn down."""
        if self._timer is None:
            return
        self._timer.invalidate()
        self._timer = None

    def tick_(self, _timer: AppKit.NSTimer) -> None:
        """Redraw the overlay on every animation frame."""
        self.setNeedsDisplay_(True)

    def set_mode(self, mode: OverlayMode, message: Optional[str] = None) -> None:
        """Update the pill target state and begin a short size transition."""
        now = time.monotonic()
        current_width, current_height = self._interpolated_size(now)
        self._previous_width = current_width
        self._previous_height = current_height
        self._target_width, self._target_height = _pill_size(mode)
        self._mode = mode
        if message is not None:
            self._message = message
        elif mode != CONFIRMING_MODE:
            self._message = ""
        self._mode_started_at = now
        self._transition_started_at = now
        self.setNeedsDisplay_(True)

    def _interpolated_size(self, now: float) -> tuple[float, float]:
        """Return the in-flight pill size during a state transition."""
        progress = min(
            1.0,
            max(
                0.0,
                (now - self._transition_started_at) / config.OVERLAY_TRANSITION_SECONDS,
            ),
        )
        eased = 1.0 - ((1.0 - progress) ** 3)
        width = self._previous_width + ((self._target_width - self._previous_width) * eased)
        height = self._previous_height + ((self._target_height - self._previous_height) * eased)
        return width, height

    def drawRect_(self, _dirty_rect: AppKit.NSRect) -> None:
        """Paint the current pill state with custom animation."""
        bounds = self.bounds()
        now = time.monotonic()
        width, height = self._interpolated_size(now)
        rect = AppKit.NSMakeRect(
            (bounds.size.width - width) / 2.0,
            config.OVERLAY_CANVAS_PADDING_Y,
            width,
            height,
        )
        glow = False
        border_alpha = config.OVERLAY_BORDER_ALPHA_IDLE
        fill_color = _color(0.0, 0.0, 0.0, config.OVERLAY_PILL_ALPHA)
        if self._mode == RECORDING_MODE:
            pulse = 0.72 + (
                0.28
                * (
                    (
                        math.sin(
                            (now - self._mode_started_at)
                            * (math.tau / config.OVERLAY_RECORDING_PULSE_SECONDS)
                        )
                        + 1.0
                    )
                    / 2.0
                )
            )
            glow = True
            border_alpha = config.OVERLAY_BORDER_ALPHA_ACTIVE
            fill_color = _color(0.0, 0.0, 0.0, config.OVERLAY_PILL_ALPHA * pulse)
        elif self._mode == PROCESSING_MODE:
            border_alpha = config.OVERLAY_BORDER_ALPHA_ACTIVE
        elif self._mode == CONFIRMING_MODE:
            border_alpha = config.OVERLAY_BORDER_ALPHA_ACTIVE
        _draw_centered_rounded_rect(rect, fill_color, glow, border_alpha)
        elapsed = now - self._mode_started_at
        if self._mode == RECORDING_MODE:
            _draw_recording_bars(rect, elapsed)
        elif self._mode == PROCESSING_MODE:
            _draw_processing_dots(rect, elapsed)
        elif self._mode == CONFIRMING_MODE:
            _draw_centered_text(rect, self._message)


class FloatingPillController:
    """Manage the macOS overlay window and route cross-thread state changes."""

    def __init__(self) -> None:
        """Create and show the always-on-top VoicePaste pill window."""
        frame = _fixed_screen_frame()
        width = _canvas_width()
        height = _canvas_height()
        origin_x = frame.origin.x + ((frame.size.width - width) / 2.0)
        origin_y = frame.origin.y + config.OVERLAY_BOTTOM_MARGIN
        window_frame = AppKit.NSMakeRect(origin_x, origin_y, width, height)
        self._window = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            window_frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setIgnoresMouseEvents_(True)
        self._window.setMovable_(False)
        self._window.setHidesOnDeactivate_(False)
        self._window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle
        )
        self._window.setLevel_(AppKit.NSFloatingWindowLevel)
        self._view = FloatingPillView.alloc().initWithFrame_(AppKit.NSMakeRect(0.0, 0.0, width, height))
        self._window.setContentView_(self._view)
        self._view.start_animation()
        self._window.orderFrontRegardless()

    def set_mode(self, mode: OverlayMode, message: Optional[str] = None) -> None:
        """Schedule a thread-safe overlay mode update on the main loop."""
        AppHelper.callAfter(self._set_mode_on_main_thread, mode, message)

    def _set_mode_on_main_thread(
        self,
        mode: OverlayMode,
        message: Optional[str],
    ) -> None:
        """Apply the mode update and keep the overlay anchored in one place."""
        frame = _fixed_screen_frame()
        window_frame = self._window.frame()
        window_frame.origin.x = frame.origin.x + ((frame.size.width - window_frame.size.width) / 2.0)
        window_frame.origin.y = frame.origin.y + config.OVERLAY_BOTTOM_MARGIN
        self._window.setFrame_display_(window_frame, True)
        self._view.set_mode(mode, message)
        self._window.orderFrontRegardless()

    def close(self) -> None:
        """Stop animation and close the overlay window on the main loop."""
        AppHelper.callAfter(self._close_on_main_thread)

    def _close_on_main_thread(self) -> None:
        """Tear down native resources associated with the overlay."""
        self._view.stop_animation()
        self._window.close()


class _EditorPanel(AppKit.NSPanel):
    """Borderless floating panel that can still become the key window."""

    def canBecomeKeyWindow(self) -> bool:
        """Allow the inline editor panel to receive keyboard focus."""
        return True

    def canBecomeMainWindow(self) -> bool:
        """Allow the inline editor panel to act as the main window briefly."""
        return True


class _InlineEditorController(AppKit.NSObject):
    """Manage one inline bottom-of-screen editable prompt."""

    def initWithTitle_message_initialValue_confirmTitle_editable_timeout_event_result_(
        self,
        title: str,
        message: str,
        initial_value: str,
        confirm_title: str,
        editable: bool,
        timeout_seconds: float,
        done_event: threading.Event,
        result_box: dict[str, Optional[str]],
    ) -> "_InlineEditorController":
        """Create the controller, build the panel, and wire actions."""
        self = objc.super(_InlineEditorController, self).init()
        if self is None:
            return None
        self._done_event = done_event
        self._result_box = result_box
        self._window = None
        self._text_field = None
        self._previous_activation_policy = None
        self._activation_policy_restored = False
        self._modal_running = False
        self._editable = editable
        self._timeout_seconds = timeout_seconds
        self._timeout_timer: Optional[threading.Timer] = None
        self._build_window(title, message, initial_value, confirm_title)
        return self

    def _build_window(
        self,
        title: str,
        message: str,
        initial_value: str,
        confirm_title: str,
    ) -> None:
        """Build the floating pill-style editor panel and its controls."""
        frame = _fixed_screen_frame()
        width = config.OVERLAY_EDITOR_WIDTH
        height = config.OVERLAY_EDITOR_HEIGHT
        origin_x = frame.origin.x + ((frame.size.width - width) / 2.0)
        origin_y = (
            frame.origin.y
            + config.OVERLAY_BOTTOM_MARGIN
            + _canvas_height()
            + config.OVERLAY_EDITOR_BOTTOM_SPACING
        )
        panel_frame = AppKit.NSMakeRect(origin_x, origin_y, width, height)
        window = _EditorPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            panel_frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        window.setReleasedWhenClosed_(False)
        window.setOpaque_(False)
        window.setBackgroundColor_(AppKit.NSColor.clearColor())
        window.setHasShadow_(True)
        window.setHidesOnDeactivate_(False)
        window.setIgnoresMouseEvents_(False)
        window.setAcceptsMouseMovedEvents_(True)
        window.setLevel_(AppKit.NSFloatingWindowLevel)
        window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle
        )

        content_view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0.0, 0.0, width, height))
        content_view.setWantsLayer_(True)
        layer = content_view.layer()
        layer.setCornerRadius_(height / 2.0)
        layer.setMasksToBounds_(True)
        layer.setBackgroundColor_(_color(0.02, 0.02, 0.03, 0.98).CGColor())
        layer.setBorderWidth_(1.2)
        layer.setBorderColor_(_color(1.0, 1.0, 1.0, 0.10).CGColor())

        text_field = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(20.0, 13.0, width - 120.0, 28.0)
        )
        text_field.setFont_(AppKit.NSFont.systemFontOfSize_(14.0))
        text_field.setStringValue_(initial_value)
        text_field.setPlaceholderString_(message or title)
        text_field.setFocusRingType_(AppKit.NSFocusRingTypeDefault)
        text_field.setEditable_(self._editable)
        text_field.setSelectable_(self._editable)
        text_field.setRefusesFirstResponder_(False)
        text_field.setBezeled_(False)
        text_field.setBordered_(False)
        text_field.setDrawsBackground_(False)
        text_field.setTextColor_(_color(1.0, 1.0, 1.0, 0.98))
        text_field.cell().setUsesSingleLineMode_(True)
        if not self._editable:
            text_field.setAlignment_(AppKit.NSTextAlignmentCenter)
        content_view.addSubview_(text_field)
        self._text_field = text_field

        cancel_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(width - 84.0, 11.0, 26.0, 30.0)
        )
        cancel_button.setTitle_("✕")
        cancel_button.setBordered_(False)
        cancel_button.setBezelStyle_(AppKit.NSBezelStyleShadowlessSquare)
        cancel_button.setFont_(AppKit.NSFont.systemFontOfSize_weight_(17.0, AppKit.NSFontWeightSemibold))
        cancel_button.setContentTintColor_(_color(1.0, 0.32, 0.24, 0.95))
        cancel_button.setTarget_(self)
        cancel_button.setAction_("cancel:")
        cancel_button.setKeyEquivalent_("\u001b")
        content_view.addSubview_(cancel_button)

        confirm_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(width - 52.0, 11.0, 26.0, 30.0)
        )
        confirm_button.setTitle_("✓")
        confirm_button.setBordered_(False)
        confirm_button.setBezelStyle_(AppKit.NSBezelStyleShadowlessSquare)
        confirm_button.setFont_(AppKit.NSFont.systemFontOfSize_weight_(18.0, AppKit.NSFontWeightBold))
        confirm_button.setContentTintColor_(_color(0.36, 0.86, 0.30, 0.98))
        confirm_button.setTarget_(self)
        confirm_button.setAction_("confirm:")
        confirm_button.setKeyEquivalent_("\r")
        content_view.addSubview_(confirm_button)

        window.setContentView_(content_view)
        window.setInitialFirstResponder_(text_field)
        self._window = window

    def present(self) -> None:
        """Show the editor panel and move keyboard focus into the text field."""
        app = AppKit.NSApplication.sharedApplication()
        self._previous_activation_policy = app.activationPolicy()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
        app.activateIgnoringOtherApps_(True)
        self._window.orderFrontRegardless()
        self._window.makeMainWindow()
        self._window.makeKeyWindow()
        self._window.makeFirstResponder_(self._text_field)
        if self._editable:
            self._text_field.selectText_(None)
        if self._timeout_seconds > 0:
            self._timeout_timer = threading.Timer(
                self._timeout_seconds,
                lambda: AppHelper.callAfter(self.cancel_, None),
            )
            self._timeout_timer.daemon = True
            self._timeout_timer.start()
        self._modal_running = True
        try:
            app.runModalForWindow_(self._window)
        finally:
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
                self._timeout_timer = None
            self._restore_activation_policy(app)
            if self._window is not None:
                self._window.orderOut_(None)
                self._window.close()
            self._done_event.set()

    def confirm_(self, _sender: object) -> None:
        """Accept the edited value and close the panel."""
        self._result_box["value"] = str(self._text_field.stringValue()).strip()
        self._finish()

    def cancel_(self, _sender: object) -> None:
        """Cancel editing and close the panel."""
        self._result_box["value"] = None
        self._finish()

    def _finish(self) -> None:
        """Close the panel and unblock the waiting worker."""
        app = AppKit.NSApplication.sharedApplication()
        if self._modal_running:
            app.stopModal()
            self._modal_running = False
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _restore_activation_policy(self, app: AppKit.NSApplication) -> None:
        """Restore the app activation policy exactly once."""
        if self._activation_policy_restored:
            return
        if self._previous_activation_policy is not None:
            app.setActivationPolicy_(self._previous_activation_policy)
        self._activation_policy_restored = True


def prompt_for_inline_text_input(
    title: str,
    message: str,
    initial_value: str,
    confirm_title: str,
    timeout_seconds: float = config.ACTION_CONFIRMATION_TIMEOUT_SECONDS,
) -> Optional[str]:
    """Show a floating inline text editor near the pill and return the result."""
    if AppKit is None:
        cleaned = initial_value.strip()
        return cleaned or None
    return _run_inline_prompt(
        title=title,
        message=message,
        initial_value=initial_value,
        confirm_title=confirm_title,
        editable=True,
        timeout_seconds=timeout_seconds,
    )


def prompt_for_inline_confirmation(
    title: str,
    message: str,
    confirm_title: str,
    timeout_seconds: float = config.ACTION_CONFIRMATION_TIMEOUT_SECONDS,
) -> bool:
    """Show a compact inline confirmation strip and return whether it was approved."""
    if AppKit is None:
        return False
    result = _run_inline_prompt(
        title=title,
        message=message,
        initial_value=title,
        confirm_title=confirm_title,
        editable=False,
        timeout_seconds=timeout_seconds,
    )
    return result is not None


def _run_inline_prompt(
    *,
    title: str,
    message: str,
    initial_value: str,
    confirm_title: str,
    editable: bool,
    timeout_seconds: float,
) -> Optional[str]:
    """Present one inline prompt safely and always unblock the waiting worker."""
    done_event = threading.Event()
    result_box: dict[str, Optional[str]] = {"value": None}
    holder: dict[str, object] = {}
    wait_timeout = max(timeout_seconds, 0.0) + 1.0

    def _present_prompt() -> None:
        """Create and present the prompt on the AppKit main thread."""
        controller = _InlineEditorController.alloc().initWithTitle_message_initialValue_confirmTitle_editable_timeout_event_result_(
            title,
            message,
            initial_value,
            confirm_title,
            editable,
            timeout_seconds,
            done_event,
            result_box,
        )
        holder["controller"] = controller
        controller.present()

    def _show_prompt() -> None:
        """Create and present the prompt, swallowing failures for worker safety."""
        try:
            _present_prompt()
        except Exception:
            result_box["value"] = None
            done_event.set()

    if threading.current_thread() is threading.main_thread():
        _present_prompt()
        return result_box["value"]

    AppHelper.callAfter(_show_prompt)
    done_event.wait(timeout=wait_timeout)
    holder.clear()
    return result_box["value"]
