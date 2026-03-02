import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { Checkbox } from "@/components/ui/checkbox"

describe("Checkbox", () => {
  it("renders in unchecked state by default", () => {
    render(<Checkbox aria-label="Accept" />)
    const checkbox = screen.getByRole("checkbox")
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).toHaveAttribute("data-state", "unchecked")
  })

  it("renders in checked state when defaultChecked", () => {
    render(<Checkbox aria-label="Accept" defaultChecked />)
    expect(screen.getByRole("checkbox")).toHaveAttribute("data-state", "checked")
  })

  it("toggles on click", async () => {
    const user = userEvent.setup()
    render(<Checkbox aria-label="Accept" />)
    const checkbox = screen.getByRole("checkbox")
    expect(checkbox).toHaveAttribute("data-state", "unchecked")
    await user.click(checkbox)
    expect(checkbox).toHaveAttribute("data-state", "checked")
  })

  it("toggles back to unchecked on second click", async () => {
    const user = userEvent.setup()
    render(<Checkbox aria-label="Accept" />)
    const checkbox = screen.getByRole("checkbox")
    await user.click(checkbox)
    expect(checkbox).toHaveAttribute("data-state", "checked")
    await user.click(checkbox)
    expect(checkbox).toHaveAttribute("data-state", "unchecked")
  })

  it("fires onCheckedChange callback", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<Checkbox aria-label="Accept" onCheckedChange={handleChange} />)
    await user.click(screen.getByRole("checkbox"))
    expect(handleChange).toHaveBeenCalledWith(true)
  })

  it("is disabled when disabled prop is set", () => {
    render(<Checkbox aria-label="Accept" disabled />)
    expect(screen.getByRole("checkbox")).toBeDisabled()
  })

  it("does not toggle when disabled", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(
      <Checkbox aria-label="Accept" disabled onCheckedChange={handleChange} />
    )
    await user.click(screen.getByRole("checkbox"))
    expect(handleChange).not.toHaveBeenCalled()
    expect(screen.getByRole("checkbox")).toHaveAttribute(
      "data-state",
      "unchecked"
    )
  })

  it("applies custom className", () => {
    render(<Checkbox aria-label="Accept" className="my-checkbox" />)
    expect(screen.getByRole("checkbox")).toHaveClass("my-checkbox")
  })

  it('has data-slot="checkbox"', () => {
    render(<Checkbox aria-label="Accept" />)
    expect(screen.getByRole("checkbox")).toHaveAttribute(
      "data-slot",
      "checkbox"
    )
  })
})
