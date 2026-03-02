import React from "react"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ErrorBoundaryProps {
  children: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="mx-auto max-w-md rounded-lg border bg-muted/50 p-8 text-center">
            <AlertTriangle className="mx-auto size-12 text-destructive" />
            <h2 className="mt-4 text-lg font-semibold">Something went wrong</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <div className="mt-6 flex items-center justify-center gap-3">
              <Button variant="outline" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
              <Button asChild>
                <a href="/">Go to Dashboard</a>
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
