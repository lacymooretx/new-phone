import { useState, useEffect, useCallback } from "react"

export interface AudioDevice {
  deviceId: string
  label: string
  kind: MediaDeviceKind
}

async function enumerateAudioDevices(): Promise<AudioDevice[]> {
  try {
    const allDevices = await navigator.mediaDevices.enumerateDevices()
    return allDevices
      .filter((d) => (d.kind === "audioinput" || d.kind === "audiooutput") && d.deviceId)
      .map((d) => ({
        deviceId: d.deviceId || "default",
        label: d.label || `${d.kind === "audioinput" ? "Microphone" : "Speaker"} ${d.deviceId.slice(0, 4) || "default"}`,
        kind: d.kind,
      }))
  } catch {
    return []
  }
}

export function useAudioDevices() {
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedMic, setSelectedMic] = useState<string>("")
  const [selectedSpeaker, setSelectedSpeaker] = useState<string>("")

  const handleDeviceChange = useCallback(async () => {
    const audioDevices = await enumerateAudioDevices()
    setDevices(audioDevices)

    // Set defaults if not already selected (use functional update to read current value)
    setSelectedMic((prev) => {
      if (prev) return prev
      const defaultMic = audioDevices.find((d) => d.kind === "audioinput")
      return defaultMic?.deviceId ?? ""
    })
    setSelectedSpeaker((prev) => {
      if (prev) return prev
      const defaultSpeaker = audioDevices.find((d) => d.kind === "audiooutput")
      return defaultSpeaker?.deviceId ?? ""
    })
  }, [])

  useEffect(() => {
    handleDeviceChange()
    navigator.mediaDevices.addEventListener("devicechange", handleDeviceChange)
    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", handleDeviceChange)
    }
  }, [handleDeviceChange])

  const microphones = devices.filter((d) => d.kind === "audioinput")
  const speakers = devices.filter((d) => d.kind === "audiooutput")

  return {
    microphones,
    speakers,
    selectedMic,
    selectedSpeaker,
    setSelectedMic,
    setSelectedSpeaker,
  }
}
