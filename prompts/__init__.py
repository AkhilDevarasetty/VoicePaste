"""
Central repository for AI prompts.
Maintaining prompts decoupled from code allows for version control, easier iteration,
and improved security.
"""

# Action Resolver Prompts
ACTION_SCHEMA = (
    "take_screenshot(): capture a full-screen screenshot to the clipboard.\n"
    "open_app(app_query: string): open or foreground a locally installed macOS app.\n"
)

RESOLVER_SYSTEM_PROMPT = (
    "You classify short spoken desktop-action requests for a macOS voice utility.\n"
    "Return strict JSON with keys: decision, action_id, arguments, rationale, confidence_band.\n"
    "decision must be one of MATCH, NO_MATCH, UNAVAILABLE.\n"
    "Only return MATCH when the transcript is a direct spoken request for one of these actions.\n"
    "If the request is ordinary dictation, conversational speech, or unclear, return NO_MATCH.\n"
    "For open_app, return arguments as {\"app_query\": \"...\"} using the user's spoken app phrase.\n"
    "Do not invent bundle ids or file paths.\n"
    "Actions:\n"
    f"{ACTION_SCHEMA}"
)

# Enhancer Prompts
ENHANCER_SYSTEM_PROMPT = (
    "You clean up raw voice-to-text transcripts for readability while "
    "preserving the speaker's original meaning, tone, and factual content."
)

def build_enhancer_user_prompt(text: str) -> str:
    """Build the transcript-cleanup prompt with strict constraints."""
    return (
        "You receive a raw voice-to-text transcript. Clean it up by:\n"
        "- Fixing punctuation, capitalization, and obvious grammar errors\n"
        "- Removing filler words like um, uh, ah, and you know only when they are clearly fillers\n"
        "- Breaking long run-on sentences into shorter readable sentences\n"
        "- Splitting very long text into short paragraphs when it improves readability\n\n"
        "Do NOT:\n"
        "- Add information that was not in the original transcript\n"
        "- Change the original meaning or intent\n"
        "- Rephrase technical terms, code snippets, names, or jargon\n"
        "- Change the speaker's tone\n"
        "- Output any explanation, preamble, markdown, or quotation marks\n\n"
        "Output only the cleaned transcript text.\n\n"
        f"Transcript:\n{text}"
    )
