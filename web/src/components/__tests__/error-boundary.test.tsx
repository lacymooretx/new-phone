import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { ErrorBoundary } from "@/components/shared/error-boundary"

// A component that throws an error for testing
function ThrowingComponent({ error }: { error?: Error }) {
  if (error) throw error
  return <div>All good</div>
}

describe("ErrorBoundary", () => {
  // Suppress console.error for the tests that trigger errors
  const originalConsoleError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalConsoleError
  })

  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    )
    expect(screen.getByText("All good")).toBeInTheDocument()
  })

  it("renders error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error("Test crash")} />
      </ErrorBoundary>
    )
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
    expect(screen.getByText("Test crash")).toBeInTheDocument()
  })

  it("renders default error message when error has no message", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error("")} />
      </ErrorBoundary>
    )
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
    expect(
      screen.getByText("An unexpected error occurred.")
    ).toBeInTheDocument()
  })

  it("renders Reload Page and Go to Dashboard buttons", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error("Crash")} />
      </ErrorBoundary>
    )
    expect(
      screen.getByRole("button", { name: "Reload Page" })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: "Go to Dashboard" })
    ).toBeInTheDocument()
  })

  it("Go to Dashboard links to /", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error("Crash")} />
      </ErrorBoundary>
    )
    expect(screen.getByRole("link", { name: "Go to Dashboard" })).toHaveAttribute(
      "href",
      "/"
    )
  })
})
