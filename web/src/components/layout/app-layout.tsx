import { useState, useEffect, startTransition } from "react"
import { Outlet, useLocation } from "react-router"
import { ThemeProvider } from "next-themes"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import { CommandPalette } from "./command-palette"
import { SoftphonePanel } from "@/components/softphone/softphone-panel"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { ErrorBoundary } from "@/components/shared/error-boundary"
import { useEventStream } from "@/hooks/use-event-stream"
import { onShortcut } from "@/lib/desktop-bridge"

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  // Real-time WebSocket event stream for push updates
  useEventStream()

  // Auto-close sidebar on mobile when route changes
  useEffect(() => {
    if (window.innerWidth < 1024) {
      startTransition(() => setSidebarOpen(false))
    }
  }, [location.pathname])

  // Listen for Electron global shortcuts
  useEffect(() => {
    return onShortcut((action) => {
      const store = useSoftphoneStore.getState()
      if (action === "toggle-softphone") store.togglePanel()
      if (action === "answer-call") store.answerCall()
      if (action === "hangup") store.hangup()
    })
  }, [])

  // Listen for click-to-call messages from browser extension
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === "NP_CLICK_TO_CALL" && typeof event.data.number === "string") {
        useSoftphoneStore.getState().makeCall(event.data.number)
      }
    }
    window.addEventListener("message", handler)
    return () => window.removeEventListener("message", handler)
  }, [])

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <TooltipProvider>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:outline-none"
        >
          Skip to content
        </a>
        <div className="flex h-screen overflow-hidden">
          <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          <div className="flex flex-1 flex-col overflow-hidden">
            <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
            <main id="main-content" className="flex-1 overflow-y-auto p-6">
              <ErrorBoundary>
                <Outlet />
              </ErrorBoundary>
            </main>
          </div>
        </div>
        <Toaster />
        <CommandPalette />
        <SoftphonePanel />
      </TooltipProvider>
    </ThemeProvider>
  )
}
