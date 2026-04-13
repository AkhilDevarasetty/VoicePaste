export const dashboardNavItems = [
  {
    label: "Dashboard",
    description: "Overview and activity",
    icon: "dashboard",
    href: "/",
  },
  {
    label: "Voice Shortcuts",
    description: "Future shortcut library",
    icon: "shortcuts",
    href: "/voice-shortcuts",
  },
  {
    label: "Settings",
    description: "Preferences and devices",
    icon: "settings",
    href: "/settings",
  },
] as const;

export const dashboardStats = [
  {
    label: "Total transcripts",
    value: "124",
    detail: "Across the last 14 days",
    change: "+18 this week",
    tint: "accent",
  },
  {
    label: "Average duration",
    value: "8m 12s",
    detail: "Per completed voice session",
    change: "Stable",
    tint: "warning",
  },
  {
    label: "Success rate",
    value: "97.8%",
    detail: "Captures completed without retry",
    change: "+2.3%",
    tint: "success",
  },
] as const;

export const transcriptRows = [
  {
    id: "t1",
    time: "10:44 AM",
    date: "Today",
    preview:
      "Draft a concise follow-up email for the design review, thanking the team and outlining the next three implementation steps for the dashboard rollout.",
    context: "Used in Mail. Final cleanup applied before paste.",
    duration: "00:42",
    status: "completed",
    statusLabel: "Completed",
  },
  {
    id: "t2",
    time: "10:18 AM",
    date: "Today",
    preview:
      "Turn the latest voice dashboard concept into a clean implementation plan and keep the scope limited to the first production-ready screen.",
    context: "Used in Notes. Ready to copy into planning doc.",
    duration: "01:11",
    status: "completed",
    statusLabel: "Completed",
  },
  {
    id: "t3",
    time: "08:48 AM",
    date: "Today",
    preview:
      "I need a shorter version of the previous message with a stronger executive summary and fewer implementation details.",
    context: "Waiting on final transcript post-processing.",
    duration: "00:19",
    status: "transcribing",
    statusLabel: "Transcribing",
  },
  {
    id: "t4",
    time: "08:37 AM",
    date: "Today",
    preview:
      "Improve this explanation so it sounds more professional, keeps the original meaning, and reads like a polished update to the team rather than rough dictation.",
    context: "Recorded in Slack. Suggested retry available.",
    duration: "00:56",
    status: "attention",
    statusLabel: "Needs review",
  },
  {
    id: "t5",
    time: "08:12 AM",
    date: "Today",
    preview:
      "Summarize the open questions from the last product sync and list which ones block the frontend dashboard implementation this week.",
    context: "No paste target detected. Transcript kept for manual reuse.",
    duration: "00:35",
    status: "failed",
    statusLabel: "Paste failed",
  },
] as const;

export const voiceShortcuts = [
  {
    id: "s1",
    trigger: "my Flow referral",
    output:
      "Hey, use my referral link to get 1 month off VoicePaste Pro: https://voicepaste.app/r/demo",
    visibility: "Personal",
  },
  {
    id: "s2",
    trigger: "my email address",
    output: "allinone.16.2024@gmail.com",
    visibility: "Personal",
  },
  {
    id: "s3",
    trigger: "organize thoughts prompt",
    output:
      "Organize these unstructured thoughts into a clear, polished version while keeping my intent intact and removing repetition.",
    visibility: "Shared with team",
  },
  {
    id: "s4",
    trigger: "my calendly link",
    output: "calendly.com/allinone/voicepaste-intro",
    visibility: "Personal",
  },
] as const;
