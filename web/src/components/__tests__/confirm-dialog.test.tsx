import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"

describe("ConfirmDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: "Are you sure?",
    onConfirm: vi.fn(),
  }

  it("renders title when open", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText("Are you sure?")).toBeInTheDocument()
  })

  it("renders description when provided", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        description="This action cannot be undone."
      />
    )
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument()
  })

  it("does not render description when not provided", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(
      screen.queryByText("This action cannot be undone.")
    ).not.toBeInTheDocument()
  })

  it("does not render content when closed", () => {
    render(<ConfirmDialog {...defaultProps} open={false} />)
    expect(screen.queryByText("Are you sure?")).not.toBeInTheDocument()
  })

  it("renders default confirm and cancel labels", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument()
  })

  it("renders custom confirm and cancel labels", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmLabel="Delete"
        cancelLabel="Nevermind"
      />
    )
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Nevermind" })
    ).toBeInTheDocument()
  })

  it("fires onConfirm when confirm button is clicked", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)
    await user.click(screen.getByRole("button", { name: "Confirm" }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it("fires onOpenChange when cancel button is clicked", async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(<ConfirmDialog {...defaultProps} onOpenChange={onOpenChange} />)
    await user.click(screen.getByRole("button", { name: "Cancel" }))
    expect(onOpenChange).toHaveBeenCalled()
  })

  it("shows warning icon when variant is destructive", () => {
    render(
      <ConfirmDialog {...defaultProps} variant="destructive" />
    )
    const iconArea = document.querySelector('[data-slot="confirm-icon"]')
    expect(iconArea).toBeInTheDocument()
    // Should contain the AlertTriangle SVG icon
    const svg = iconArea?.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })

  it("does not show icon area for default variant without icon prop", () => {
    render(
      <ConfirmDialog {...defaultProps} variant="default" />
    )
    const iconArea = document.querySelector('[data-slot="confirm-icon"]')
    expect(iconArea).not.toBeInTheDocument()
  })

  it("renders custom icon when icon prop is provided", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        icon={<span data-testid="custom-icon">!</span>}
      />
    )
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument()
  })

  it("renders icon area when custom icon is provided on default variant", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        variant="default"
        icon={<span data-testid="custom-icon">!</span>}
      />
    )
    const iconArea = document.querySelector('[data-slot="confirm-icon"]')
    expect(iconArea).toBeInTheDocument()
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument()
  })

  it("renders custom icon in icon area for destructive variant", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        variant="destructive"
        icon={<span data-testid="custom-icon">!</span>}
      />
    )
    const iconArea = document.querySelector('[data-slot="confirm-icon"]')
    expect(iconArea).toBeInTheDocument()
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument()
  })
})
