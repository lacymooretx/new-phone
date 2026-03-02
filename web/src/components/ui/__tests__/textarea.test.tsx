import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { Textarea } from "@/components/ui/textarea"

describe("Textarea", () => {
  it("renders with placeholder text", () => {
    render(<Textarea placeholder="Enter message" />)
    expect(screen.getByPlaceholderText("Enter message")).toBeInTheDocument()
  })

  it("renders as a <textarea> element", () => {
    render(<Textarea placeholder="test" />)
    expect(screen.getByPlaceholderText("test").tagName).toBe("TEXTAREA")
  })

  it("accepts typed input", async () => {
    const user = userEvent.setup()
    render(<Textarea placeholder="Type here" />)
    const textarea = screen.getByPlaceholderText("Type here")
    await user.type(textarea, "Hello world")
    expect(textarea).toHaveValue("Hello world")
  })

  it("fires onChange when user types", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<Textarea placeholder="test" onChange={handleChange} />)
    await user.type(screen.getByPlaceholderText("test"), "a")
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  it("is disabled when disabled prop is set", () => {
    render(<Textarea placeholder="disabled" disabled />)
    expect(screen.getByPlaceholderText("disabled")).toBeDisabled()
  })

  it("does not accept input when disabled", async () => {
    const user = userEvent.setup()
    render(<Textarea placeholder="disabled" disabled />)
    const textarea = screen.getByPlaceholderText("disabled")
    await user.type(textarea, "text")
    expect(textarea).toHaveValue("")
  })

  it("applies rows attribute", () => {
    render(<Textarea placeholder="rows" rows={10} />)
    expect(screen.getByPlaceholderText("rows")).toHaveAttribute("rows", "10")
  })

  it("applies custom className", () => {
    render(<Textarea placeholder="styled" className="custom-textarea" />)
    expect(screen.getByPlaceholderText("styled")).toHaveClass("custom-textarea")
  })

  it('has data-slot="textarea"', () => {
    render(<Textarea placeholder="slot" />)
    expect(screen.getByPlaceholderText("slot")).toHaveAttribute(
      "data-slot",
      "textarea"
    )
  })

  it("applies value prop for controlled usage", () => {
    render(<Textarea placeholder="ctrl" value="controlled" readOnly />)
    expect(screen.getByPlaceholderText("ctrl")).toHaveValue("controlled")
  })
})
