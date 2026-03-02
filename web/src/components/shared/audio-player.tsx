import { useState, useRef, useEffect } from "react"
import { Play, Pause, Volume2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface AudioPlayerProps {
  fetchUrl: () => Promise<{ url: string }>
}

export function AudioPlayer({ fetchUrl }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [pendingPlay, setPendingPlay] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Play audio after URL is set and audio element is rendered
  useEffect(() => {
    if (pendingPlay && audioUrl && audioRef.current) {
      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(() => toast.error("Failed to play audio"))
      setPendingPlay(false)
    }
  }, [pendingPlay, audioUrl])

  const handlePlay = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
      return
    }

    if (!audioUrl) {
      setIsLoading(true)
      try {
        const { url } = await fetchUrl()
        setAudioUrl(url)
        setPendingPlay(true)
      } catch {
        toast.error("Failed to load audio")
      } finally {
        setIsLoading(false)
      }
      return
    }

    audioRef.current?.play()
      .then(() => setIsPlaying(true))
      .catch(() => toast.error("Failed to play audio"))
  }

  return (
    <div className="flex items-center gap-2">
      <Button variant="ghost" size="icon" onClick={handlePlay} disabled={isLoading}>
        {isLoading ? (
          <Volume2 className="h-4 w-4 animate-pulse" />
        ) : isPlaying ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4" />
        )}
      </Button>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onEnded={() => setIsPlaying(false)}
          onPause={() => setIsPlaying(false)}
        />
      )}
    </div>
  )
}
