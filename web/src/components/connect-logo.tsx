import { cn } from "@/lib/utils"

interface ConnectLogoProps {
  className?: string
}

export function ConnectLogo({ className }: ConnectLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="none"
      className={cn("h-6 w-6", className)}
    >
      <defs>
        <linearGradient id="cg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0ea5e9" />
          <stop offset="100%" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7" fill="url(#cg)" />
      <path
        d="M20 9.5a6.5 6.5 0 0 0-6.5 6.5 6.5 6.5 0 0 0 6.5 6.5"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
      <path
        d="M12 9.5a6.5 6.5 0 0 1 6.5 6.5 6.5 6.5 0 0 1-6.5 6.5"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="16" cy="16" r="2" fill="white" />
    </svg>
  )
}
