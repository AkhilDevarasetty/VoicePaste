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
