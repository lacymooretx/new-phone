import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { Badge } from "@/components/ui/badge"

describe("Badge", () => {
  it("renders with text content", () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText("Active")).toBeInTheDocument()
  })

  it("renders as a <span> by default", () => {
    render(<Badge>Tag</Badge>)
    expect(screen.getByText("Tag").tagName).toBe("SPAN")
  })

  it.each([
    "default",
    "secondary",
    "destructive",
    "outline",
    "ghost",
    "link",
  ] as const)('applies data-variant="%s"', (variant) => {
    render(<Badge variant={variant}>test</Badge>)
    expect(screen.getByText("test")).toHaveAttribute("data-variant", variant)
  })

  it('uses data-variant="default" when no variant is specified', () => {
    render(<Badge>default</Badge>)
    expect(screen.getByText("default")).toHaveAttribute(
      "data-variant",
      "default"
    )
  })

  it("applies custom className", () => {
    render(<Badge className="my-badge">Styled</Badge>)
    expect(screen.getByText("Styled")).toHaveClass("my-badge")
  })

  it('has data-slot="badge"', () => {
    render(<Badge>slot</Badge>)
    expect(screen.getByText("slot")).toHaveAttribute("data-slot", "badge")
  })

  it("renders as child element via Slot when asChild is true", () => {
    render(
      <Badge asChild>
        <a href="/tags">Tag Link</a>
      </Badge>
    )
    const link = screen.getByRole("link", { name: "Tag Link" })
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe("A")
    expect(link).toHaveAttribute("data-slot", "badge")
  })
})
