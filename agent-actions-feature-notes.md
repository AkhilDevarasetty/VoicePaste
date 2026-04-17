# Agent Actions Feature Notes

## Summary

This document captures the current VoicePaste agent-actions implementation, the major issues encountered during development, the fixes that were applied, and the UI polish items to revisit later.

The current v1 implementation supports:

- `take_screenshot`
- `open_app`

Review / verification status:

- review-driven production fixes from the senior-architect pass are implemented
- `test_agent_actions_review.py` passes fully
- the earlier `Control`-to-confirm screenshot safety risk is no longer part of the current flow because confirmation is UI-only

Current interaction model:

- Dictation: hold `Right Option`
- Action mode: hold `Control`
- Action confirmation:
  - `take_screenshot`: approve or cancel from the inline confirmation UI
  - `open_app`: edit the detected app name in the inline editor, then approve or cancel from that same inline UI

## Goals Of This Feature

- Add a separate action path without breaking the existing dictation flow
- Keep normal dictation and agent actions clearly separated
- Support natural-language action requests
- Fail safely when the resolver is unavailable or the action is ambiguous
- Start with a narrow local-first action set before expanding further

## Implementation Changes Made

### 1. Action-mode architecture

Added a dedicated action pipeline on top of the existing record/transcribe flow:

- `main.py`
  - added session-based routing for dictation vs action mode
  - added action confirmation state
  - added action execution worker path
- `actions.py`
  - added action registry
  - added `take_screenshot` handler
  - added `open_app` handler
- `action_resolver.py`
  - added LLM-backed resolver for a closed v1 action set
- `app_catalog.py`
  - added local app-catalog indexing and app-name resolution

### 2. Input/hotkey changes

The action trigger changed over time:

- Initial attempt:
  - double-tap / double-gesture on `Right Option`
- Final working trigger:
  - hold `Control` for action mode

Reason:

- `Right Option` conflicted with Codex/Claude desktop behavior and caused gesture collisions
- `Control` proved more reliable on the current setup

### 3. Screenshot action

Implemented `take_screenshot` using:

- `screencapture -c -x`

Behavior:

- captures screenshot to clipboard
- does not show the default macOS screenshot thumbnail
- does not use the standard screenshot save flow

### 4. Open app action

Implemented `open_app` with:

- natural-language intent resolution via the resolver
- local app-catalog search across:
  - `/Applications`
  - `/System/Applications`
  - `/System/Applications/Utilities`
  - `~/Applications`
- alias support in `config.py`
- local app launch using `open -a`

### 5. Editable app-name correction step

Added an inline editor for `open_app` so the user can correct ASR mistakes before launch.

The final version is:

- a compact pill-style inline editor near the overlay
- editable app-name text field
- approve button
- cancel button
- modal keyboard focus while editing
- auto-cancel timeout so abandoned prompts do not leave the session hanging

### 6. UI-only confirmation flow

Removed keyboard-driven action approval and standardized on inline UI confirmation.

The current confirmation model is:

- actions resolve first
- VoicePaste shows an inline confirmation/editor strip
- user approves or cancels directly in the UI
- no second hotkey press is used for confirmation

### 7. Structured action failures

Hardened action execution so shell/tool failures return structured `ActionResult` failures instead of falling through generic exception handling.

### 8. Review-driven contract hardening

Added targeted production fixes so the code now matches the review-test contracts around:

- immutable `ActionIntent.arguments`
- resolver JSON-mode request formatting
- larger resolver output budget
- failure-mode-aware resolver telemetry
- prompt-version changes when the effective action schema/catalog changes
- shallow app-catalog scanning

## Issues Encountered And Fixes Applied

### Issue 1. Action gesture collided with Codex/Claude UI

Problem:

- double `Right Option` triggered Codex/Claude search/UI behavior
- VoicePaste and Codex were both reacting to the same gesture

Fix:

- removed the double-`Right Option` action gesture
- moved action mode to `Control`

### Issue 2. Screenshot action seemed broken

Problem:

- screenshot action was actually succeeding, but it felt like nothing happened
- no default macOS screenshot sound or thumbnail appeared

Cause:

- implementation uses clipboard capture (`screencapture -c -x`) rather than native screenshot save UI

Fix:

- confirmed behavior through logs
- documented that the screenshot is copied to clipboard rather than shown in the standard macOS UI

### Issue 3. Open-app ASR errors

Problem:

- phrases like `open ChatGPT` were transcribed incorrectly
- app launch failed because the extracted app query was wrong

Fix:

- added a correction step before `open_app` execution
- user can now edit the detected app name before launch

### Issue 4. Native alert dialog took focus poorly

Problem:

- a separate AppKit alert appeared
- typing still went into the Codex app instead of the dialog field

Fix:

- removed the separate `NSAlert`-style confirmation flow
- replaced it with an inline editor in the VoicePaste overlay flow

### Issue 5. Inline editor looked focused but was not actually editable

Problem:

- the field showed selection/highlight
- user could not backspace, type, or replace text

Fixes applied:

- explicitly enabled:
  - `setEditable_(True)`
  - `setSelectable_(True)`
  - `setRefusesFirstResponder_(False)`
- set the text field as:
  - initial first responder
  - current first responder
- explicitly selected the field text on presentation

### Issue 6. Menu-bar app activation prevented real text focus

Problem:

- VoicePaste is effectively a background/menu-bar app
- the inline editor still was not reliably receiving true keyboard ownership

Fix:

- temporarily switched the app activation policy to `NSApplicationActivationPolicyRegular`
- activated VoicePaste while the editor is open
- restored the previous activation policy after the editor closes

### Issue 7. Inline editor still leaked keyboard focus

Problem:

- even after focus improvements, the editor was not behaving like a true text destination

Fix:

- made the inline editor run as a true modal interaction while open
- this forces the text field to own keyboard input during editing

### Issue 8. Pill overlay disappeared after editing

Problem:

- after the edit interaction completed, the pill overlay no longer appeared even though actions still ran

Cause:

- after the editor’s temporary app/window activation changes, the main floating pill was not explicitly re-shown

Fix:

- updated overlay mode changes to call `orderFrontRegardless()` on the pill window so it reappears reliably

### Issue 9. Inline editor startup crash

Problem:

- startup failed with a PyObjC selector/prototype mismatch

Fix:

- corrected the selector-style initializer name so the Objective-C signature matched the Python method arguments

### Issue 10. Keyboard confirmation was still a safety risk

Problem:

- modifier-key confirmation was still too easy to trigger accidentally
- action approval should depend on an explicit visible UI decision, not another key press

Fix:

- removed the leftover keyboard-confirmation scaffolding from the action state machine
- made screenshot approval depend on the inline confirmation UI only

### Issue 11. Prompt lifecycle needed stronger cleanup guarantees

Problem:

- if the inline prompt failed during setup or presentation, the waiting worker could stall
- action sessions needed to clean up reliably even when AppKit prompt setup failed

Fix:

- wrapped prompt presentation with a shared safe helper
- ensured the waiting worker is always released even if prompt creation/presentation raises
- kept activation-policy restoration in the prompt `try/finally` path

### Issue 12. Shell failures bypassed structured action results

Problem:

- screenshot/open-app shell failures could still fall into generic exception handling

Fix:

- handlers now catch `CalledProcessError`, `TimeoutExpired`, and `OSError`
- failures return structured `ActionResult(status=\"failed\", ...)` values

## Current State

What works now:

- dictation still works on `Right Option`
- action mode works on `Control`
- `take_screenshot` executes successfully
- `take_screenshot` uses inline UI approval rather than keyboard confirmation
- the old `Control`-to-confirm accidental-execution risk is closed
- `open_app` executes successfully when the app name can be resolved
- app-name correction now works inline before app launch
- overlay returns correctly after the edit flow
- abandoned inline prompts time out and cancel safely
- action command failures now surface through structured action results
- review-driven unit tests for the action contracts pass fully

What is intentionally limited:

- only two actions are implemented
- screenshot capture still goes to clipboard, not standard macOS screenshot UI
- `open_app` handles straightforward app names better than fuzzy conversational descriptions

## Files Touched For This Feature

- [main.py](/Users/niharikainala/Documents/whisperflow/main.py)
- [config.py](/Users/niharikainala/Documents/whisperflow/config.py)
- [hotkey.py](/Users/niharikainala/Documents/whisperflow/hotkey.py)
- [overlay.py](/Users/niharikainala/Documents/whisperflow/overlay.py)
- [recorder.py](/Users/niharikainala/Documents/whisperflow/recorder.py)
- [actions.py](/Users/niharikainala/Documents/whisperflow/actions.py)
- [action_resolver.py](/Users/niharikainala/Documents/whisperflow/action_resolver.py)
- [app_catalog.py](/Users/niharikainala/Documents/whisperflow/app_catalog.py)

## Future UI Polish Notes

The behavior is now solid, but the inline editor still feels visually cheap compared to the rest of the product direction. Future polish should focus on:

- Make the inline editor feel like a true extension of the VoicePaste pill, not just a functional floating strip
- Improve the field styling so it feels more native/premium and less like a raw text box dropped into a dark capsule
- Refine spacing and proportions between text field, confirm, and cancel controls
- Improve hover affordances for approve/disapprove controls
- Improve cursor affordances so interactive elements feel obviously clickable
- Improve typography and icon balance inside the editor strip
- Make the approve/disapprove controls feel intentionally designed rather than placeholder glyphs
- Consider subtle animation for entering/exiting edit mode
- Consider visually separating:
  - detected action label
  - editable argument
  - confirm/cancel controls
- Revisit whether the editor should anchor more tightly to the main pill or fully merge into one unified component

## Future Product / UX Follow-Ups

- Consider native screenshot-style feedback for `take_screenshot`
- Consider richer feedback after successful action execution
- Expand `open_app` argument cleanup so phrases like `ChatGPT app` or similar variants resolve more reliably
- Add more local-first actions only after the current action UX is visually polished
- Revisit voice-first confirmation later if the product moves toward a stronger hands-free interaction model

## Quick Testing Checklist

- Hold `Right Option`, speak, release: dictation should paste normally
- Hold `Control`, say `take a screenshot`, release, confirm: screenshot should land in clipboard
- Hold `Control`, say `open ChatGPT`, release: inline editor should appear
- Edit the app name in the inline editor
- Approve: the app should open
- Cancel: action should not execute
- After the editor closes, the main pill should still appear on later actions
- Run `PYTHONPYCACHEPREFIX=/Users/niharikainala/Documents/whisperflow/.pycache ./venv/bin/python -m unittest test_agent_actions_review -v`: all tests should pass
