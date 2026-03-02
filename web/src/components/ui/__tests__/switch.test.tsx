import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { Switch } from "@/components/ui/switch"

describe("Switch", () => {
  it("renders in unchecked state by default", () => {
    render(<Switch aria-label="Toggle" />)
    const toggle = screen.getByRole("switch")
    expect(toggle).toBeInTheDocument()
    expect(toggle).toHaveAttribute("data-state", "unchecked")
  })

  it("renders in checked state when defaultChecked", () => {
    render(<Switch aria-label="Toggle" defaultChecked />)
    expect(screen.getByRole("switch")).toHaveAttribute("data-state", "checked")
  })

  it("toggles on click", async () => {
    const user = userEvent.setup()
    render(<Switch aria-label="Toggle" />)
    const toggle = screen.getByRole("switch")
    expect(toggle).toHaveAttribute("data-state", "unchecked")
    await user.click(toggle)
    expect(toggle).toHaveAttribute("data-state", "checked")
  })

  it("toggles back to unchecked on second click", async () => {
    const user = userEvent.setup()
    render(<Switch aria-label="Toggle" />)
    const toggle = screen.getByRole("switch")
    await user.click(toggle)
    expect(toggle).toHaveAttribute("data-state", "checked")
    await user.click(toggle)
    expect(toggle).toHaveAttribute("data-state", "unchecked")
  })

  it("fires onCheckedChange callback", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<Switch aria-label="Toggle" onCheckedChange={handleChange} />)
    await user.click(screen.getByRole("switch"))
    expect(handleChange).toHaveBeenCalledWith(true)
  })

  it("is disabled when disabled prop is set", () => {
    render(<Switch aria-label="Toggle" disabled />)
    expect(screen.getByRole("switch")).toBeDisabled()
  })

  it("does not toggle when disabled", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(
      <Switch aria-label="Toggle" disabled onCheckedChange={handleChange} />
    )
    await user.click(screen.getByRole("switch"))
    expect(handleChange).not.toHaveBeenCalled()
    expect(screen.getByRole("switch")).toHaveAttribute("data-state", "unchecked")
  })

  it("applies custom className", () => {
    render(<Switch aria-label="Toggle" className="my-switch" />)
    expect(screen.getByRole("switch")).toHaveClass("my-switch")
  })

  it('has data-slot="switch"', () => {
    render(<Switch aria-label="Toggle" />)
    expect(screen.getByRole("switch")).toHaveAttribute("data-slot", "switch")
  })

  it("supports size prop with data-size attribute", () => {
    render(<Switch aria-label="Toggle" size="sm" />)
    expect(screen.getByRole("switch")).toHaveAttribute("data-size", "sm")
  })
})
