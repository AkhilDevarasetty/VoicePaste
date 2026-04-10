"""Bottom-center floating pill overlay for VoicePaste."""

from __future__ import annotations

import math
import time
from typing import Final, Literal

import AppKit
import objc
from PyObjCTools import AppHelper

import config

OverlayMode = Literal["idle", "recording", "processing"]
IDLE_MODE: Final[OverlayMode] = "idle"
RECORDING_MODE: Final[OverlayMode] = "recording"
PROCESSING_MODE: Final[OverlayMode] = "processing"


def _max_pill_width() -> float:
    """Return the widest pill width across all overlay states."""
    return max(
        config.OVERLAY_IDLE_WIDTH,
        config.OVERLAY_RECORDING_WIDTH,
        config.OVERLAY_PROCESSING_WIDTH,
    )


def _max_pill_height() -> float:
    """Return the tallest pill height across all overlay states."""
    return max(
        config.OVERLAY_IDLE_HEIGHT,
        config.OVERLAY_RECORDING_HEIGHT,
        config.OVERLAY_PROCESSING_HEIGHT,
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
            -(rect.size.width * (config.OVERLAY_RECORDING_GLOW_SCALE - 1.0) / 2.0),
            -(rect.size.height * (config.OVERLAY_RECORDING_GLOW_SCALE - 1.0) / 2.0),
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
    _color(1.0, 1.0, 1.0, config.OVERLAY_BORDER_ALPHA).setStroke()
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

    def set_mode(self, mode: OverlayMode) -> None:
        """Update the pill target state and begin a short size transition."""
        now = time.monotonic()
        current_width, current_height = self._interpolated_size(now)
        self._previous_width = current_width
        self._previous_height = current_height
        self._target_width, self._target_height = _pill_size(mode)
        self._mode = mode
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
            fill_color = _color(0.0, 0.0, 0.0, config.OVERLAY_PILL_ALPHA * pulse)
        _draw_centered_rounded_rect(rect, fill_color, glow)
        elapsed = now - self._mode_started_at
        if self._mode == RECORDING_MODE:
            _draw_recording_bars(rect, elapsed)
        elif self._mode == PROCESSING_MODE:
            _draw_processing_dots(rect, elapsed)


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

    def set_mode(self, mode: OverlayMode) -> None:
        """Schedule a thread-safe overlay mode update on the main loop."""
        AppHelper.callAfter(self._set_mode_on_main_thread, mode)

    def _set_mode_on_main_thread(self, mode: OverlayMode) -> None:
        """Apply the mode update and keep the overlay anchored in one place."""
        frame = _fixed_screen_frame()
        window_frame = self._window.frame()
        window_frame.origin.x = frame.origin.x + ((frame.size.width - window_frame.size.width) / 2.0)
        window_frame.origin.y = frame.origin.y + config.OVERLAY_BOTTOM_MARGIN
        self._window.setFrame_display_(window_frame, True)
        self._view.set_mode(mode)

    def close(self) -> None:
        """Stop animation and close the overlay window on the main loop."""
        AppHelper.callAfter(self._close_on_main_thread)

    def _close_on_main_thread(self) -> None:
        """Tear down native resources associated with the overlay."""
        self._view.stop_animation()
        self._window.close()
