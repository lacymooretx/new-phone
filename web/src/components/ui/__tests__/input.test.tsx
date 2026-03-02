import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { createRef } from "react"
import { Input } from "@/components/ui/input"

describe("Input", () => {
  it("renders with placeholder text", () => {
    render(<Input placeholder="Enter email" />)
    expect(screen.getByPlaceholderText("Enter email")).toBeInTheDocument()
  })

  it("renders as an <input> element", () => {
    render(<Input placeholder="test" />)
    expect(screen.getByPlaceholderText("test").tagName).toBe("INPUT")
  })

  it("accepts typed input", async () => {
    const user = userEvent.setup()
    render(<Input placeholder="Type here" />)
    const input = screen.getByPlaceholderText("Type here")
    await user.type(input, "hello world")
    expect(input).toHaveValue("hello world")
  })

  it("fires onChange when user types", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(<Input placeholder="test" onChange={handleChange} />)
    await user.type(screen.getByPlaceholderText("test"), "a")
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  it("is disabled when disabled prop is set", () => {
    render(<Input placeholder="test" disabled />)
    expect(screen.getByPlaceholderText("test")).toBeDisabled()
  })

  it("does not accept input when disabled", async () => {
    const user = userEvent.setup()
    render(<Input placeholder="test" disabled />)
    const input = screen.getByPlaceholderText("test")
    await user.type(input, "text")
    expect(input).toHaveValue("")
  })

  it("applies custom className", () => {
    render(<Input placeholder="test" className="custom-input" />)
    expect(screen.getByPlaceholderText("test")).toHaveClass("custom-input")
  })

  it.each(["text", "email", "password", "number", "tel"] as const)(
    'renders with type="%s"',
    (type) => {
      render(<Input type={type} placeholder="test" />)
      expect(screen.getByPlaceholderText("test")).toHaveAttribute("type", type)
    }
  )

  it("forwards ref to the input element", () => {
    const ref = createRef<HTMLInputElement>()
    render(<Input ref={ref} placeholder="ref-test" />)
    expect(ref.current).toBeInstanceOf(HTMLInputElement)
    expect(ref.current).toBe(screen.getByPlaceholderText("ref-test"))
  })

  it('has data-slot="input"', () => {
    render(<Input placeholder="slot" />)
    expect(screen.getByPlaceholderText("slot")).toHaveAttribute(
      "data-slot",
      "input"
    )
  })

  it("applies value prop for controlled usage", () => {
    render(<Input placeholder="ctrl" value="controlled" readOnly />)
    expect(screen.getByPlaceholderText("ctrl")).toHaveValue("controlled")
  })
})
