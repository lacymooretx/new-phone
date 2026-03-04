export type ExtStatus = "available" | "busy" | "ringing" | "dnd" | "offline"

export function getExtensionStatus(ext: {
  is_active: boolean
  dnd_enabled: boolean
  agent_status: string | null
}): ExtStatus {
  if (!ext.is_active) return "offline"
  if (ext.dnd_enabled) return "dnd"
  if (ext.agent_status === "On Break" || ext.agent_status === "Logged Out") return "offline"
  if (ext.agent_status === "On Call" || ext.agent_status === "In a Queue Call") return "busy"
  if (ext.agent_status === "Available" || ext.agent_status === "Waiting") return "available"
  // Default: if active and not DND, assume available
  return "available"
}

export const STATUS_CONFIG: Record<ExtStatus, { dot: string; border: string; bg: string; label: string }> = {
  available: {
    dot: "bg-emerald-400",
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/5 hover:bg-emerald-500/10",
    label: "Available",
  },
  busy: {
    dot: "bg-red-400",
    border: "border-red-500/30",
    bg: "bg-red-500/5 hover:bg-red-500/10",
    label: "On Call",
  },
  ringing: {
    dot: "bg-amber-400 animate-pulse",
    border: "border-amber-500/40",
    bg: "bg-amber-500/5 hover:bg-amber-500/10",
    label: "Ringing",
  },
  dnd: {
    dot: "bg-zinc-400",
    border: "border-zinc-500/20",
    bg: "bg-zinc-500/5 hover:bg-zinc-500/8 opacity-60",
    label: "DND",
  },
  offline: {
    dot: "bg-zinc-600",
    border: "border-zinc-700/20",
    bg: "bg-zinc-800/5 hover:bg-zinc-500/5 opacity-40",
    label: "Offline",
  },
}
