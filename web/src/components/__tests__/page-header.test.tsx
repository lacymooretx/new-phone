import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { PageHeader } from "@/components/shared/page-header"

describe("PageHeader", () => {
  it("renders the title as an h1", () => {
    render(<PageHeader title="Extensions" />)
    expect(
      screen.getByRole("heading", { level: 1, name: "Extensions" })
    ).toBeInTheDocument()
  })

  it("renders the description when provided", () => {
    render(
      <PageHeader title="Users" description="Manage your users" />
    )
    expect(screen.getByText("Manage your users")).toBeInTheDocument()
  })

  it("does not render description when not provided", () => {
    const { container } = render(<PageHeader title="Users" />)
    const paragraphs = container.querySelectorAll("p")
    expect(paragraphs).toHaveLength(0)
  })

  it("renders children in the actions area", () => {
    render(
      <PageHeader title="Queues">
        <button>Add Queue</button>
      </PageHeader>
    )
    expect(screen.getByRole("button", { name: "Add Queue" })).toBeInTheDocument()
  })

  it("does not render the actions container when no children", () => {
    const { container } = render(<PageHeader title="Test" />)
    // The outer div has two children: the title div and (if present) the actions div
    const outerDiv = container.firstElementChild!
    // Only the title div should be present
    expect(outerDiv.children).toHaveLength(1)
  })

  it("renders title, description, and children together", () => {
    render(
      <PageHeader title="Sites" description="All office locations">
        <button>New Site</button>
      </PageHeader>
    )
    expect(
      screen.getByRole("heading", { level: 1, name: "Sites" })
    ).toBeInTheDocument()
    expect(screen.getByText("All office locations")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "New Site" })
    ).toBeInTheDocument()
  })
})
