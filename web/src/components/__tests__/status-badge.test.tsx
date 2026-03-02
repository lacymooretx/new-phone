import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { StatusBadge } from "@/components/shared/status-badge"

// Mock react-i18next to return the key as the translation
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "common.active": "Active",
        "common.inactive": "Inactive",
      }
      return translations[key] ?? key
    },
    i18n: { language: "en" },
  }),
}))

describe("StatusBadge", () => {
  it("renders Active text when active is true", () => {
    render(<StatusBadge active />)
    expect(screen.getByText("Active")).toBeInTheDocument()
  })

  it("renders Inactive text when active is false", () => {
    render(<StatusBadge active={false} />)
    expect(screen.getByText("Inactive")).toBeInTheDocument()
  })

  it("uses custom activeLabel when provided", () => {
    render(<StatusBadge active activeLabel="Enabled" />)
    expect(screen.getByText("Enabled")).toBeInTheDocument()
    expect(screen.queryByText("Active")).not.toBeInTheDocument()
  })

  it("uses custom inactiveLabel when provided", () => {
    render(<StatusBadge active={false} inactiveLabel="Disabled" />)
    expect(screen.getByText("Disabled")).toBeInTheDocument()
    expect(screen.queryByText("Inactive")).not.toBeInTheDocument()
  })

  it("renders a Badge component (has data-slot badge)", () => {
    render(<StatusBadge active />)
    const badge = screen.getByText("Active")
    expect(badge).toHaveAttribute("data-slot", "badge")
  })

  it('uses variant="default" for active state', () => {
    render(<StatusBadge active />)
    expect(screen.getByText("Active")).toHaveAttribute("data-variant", "default")
  })

  it('uses variant="secondary" for inactive state', () => {
    render(<StatusBadge active={false} />)
    expect(screen.getByText("Inactive")).toHaveAttribute(
      "data-variant",
      "secondary"
    )
  })
})
