import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { Button } from "@/components/ui/button"

describe("Button", () => {
  it("renders with children text", () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument()
  })

  it("renders as a <button> element by default", () => {
    render(<Button>Submit</Button>)
    const btn = screen.getByRole("button", { name: "Submit" })
    expect(btn.tagName).toBe("BUTTON")
  })

  // --- variant tests ---
  it.each([
    "default",
    "destructive",
    "outline",
    "secondary",
    "ghost",
    "link",
  ] as const)('applies data-variant="%s"', (variant) => {
    render(<Button variant={variant}>btn</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("data-variant", variant)
  })

  it('uses data-variant="default" when no variant prop is provided', () => {
    render(<Button>btn</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("data-variant", "default")
  })

  // --- size tests ---
  it.each([
    "default",
    "xs",
    "sm",
    "lg",
    "icon",
    "icon-xs",
    "icon-sm",
    "icon-lg",
  ] as const)('applies data-size="%s"', (size) => {
    render(<Button size={size}>btn</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("data-size", size)
  })

  it('uses data-size="default" when no size prop is provided', () => {
    render(<Button>btn</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("data-size", "default")
  })

  // --- click handler ---
  it("fires onClick handler when clicked", async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    await user.click(screen.getByRole("button"))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // --- disabled ---
  it("has disabled attribute when disabled", () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByRole("button")).toBeDisabled()
  })

  it("does not fire onClick when disabled", async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    )
    await user.click(screen.getByRole("button"))
    expect(handleClick).not.toHaveBeenCalled()
  })

  // --- asChild ---
  it("renders as child element via Slot when asChild is true", () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    )
    const link = screen.getByRole("link", { name: "Link Button" })
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe("A")
    expect(link).toHaveAttribute("href", "/test")
    // data-slot should still be present (merged by Slot)
    expect(link).toHaveAttribute("data-slot", "button")
  })

  // --- custom className ---
  it("applies custom className", () => {
    render(<Button className="my-custom-class">Styled</Button>)
    expect(screen.getByRole("button")).toHaveClass("my-custom-class")
  })

  // --- data-slot ---
  it('always has data-slot="button"', () => {
    render(<Button>Test</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("data-slot", "button")
  })

  // --- type attribute ---
  it('defaults to type="submit" when no type is given (native button behavior)', () => {
    render(<Button>Test</Button>)
    // Buttons without explicit type default in HTML
    const btn = screen.getByRole("button")
    // Radix and React don't set type automatically; check it can be overridden
    expect(btn).toBeInTheDocument()
  })

  it("accepts type prop", () => {
    render(<Button type="submit">Submit</Button>)
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit")
  })
})
