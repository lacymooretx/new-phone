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

const LS_MIC_KEY = "np_audio_mic"
const LS_SPEAKER_KEY = "np_audio_speaker"

export function useAudioDevices() {
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [selectedMic, setSelectedMic] = useState<string>(
    () => localStorage.getItem(LS_MIC_KEY) ?? ""
  )
  const [selectedSpeaker, setSelectedSpeaker] = useState<string>(
    () => localStorage.getItem(LS_SPEAKER_KEY) ?? ""
  )

  const persistMic = useCallback((deviceId: string) => {
    setSelectedMic(deviceId)
    localStorage.setItem(LS_MIC_KEY, deviceId)
  }, [])

  const persistSpeaker = useCallback((deviceId: string) => {
    setSelectedSpeaker(deviceId)
    localStorage.setItem(LS_SPEAKER_KEY, deviceId)
  }, [])

  const handleDeviceChange = useCallback(async () => {
    const audioDevices = await enumerateAudioDevices()
    setDevices(audioDevices)

    const mics = audioDevices.filter((d) => d.kind === "audioinput")
    const spkrs = audioDevices.filter((d) => d.kind === "audiooutput")

    // Validate stored mic still exists; fall back to first available
    setSelectedMic((prev) => {
      if (prev && mics.some((d) => d.deviceId === prev)) return prev
      const fallback = mics[0]?.deviceId ?? ""
      if (fallback) localStorage.setItem(LS_MIC_KEY, fallback)
      return fallback
    })
    // Validate stored speaker still exists; fall back to first available
    setSelectedSpeaker((prev) => {
      if (prev && spkrs.some((d) => d.deviceId === prev)) return prev
      const fallback = spkrs[0]?.deviceId ?? ""
      if (fallback) localStorage.setItem(LS_SPEAKER_KEY, fallback)
      return fallback
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
    setSelectedMic: persistMic,
    setSelectedSpeaker: persistSpeaker,
  }
}
