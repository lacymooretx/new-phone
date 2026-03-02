import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { EmptyState } from "@/components/shared/empty-state"
import { Inbox, Users } from "lucide-react"

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState icon={Inbox} title="No items yet" />)
    expect(screen.getByText("No items yet")).toBeInTheDocument()
  })

  it("renders the icon", () => {
    const { container } = render(
      <EmptyState icon={Inbox} title="Empty" />
    )
    // lucide icons render as SVG elements
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })

  it("renders description when provided", () => {
    render(
      <EmptyState
        icon={Users}
        title="No users"
        description="Create your first user to get started"
      />
    )
    expect(
      screen.getByText("Create your first user to get started")
    ).toBeInTheDocument()
  })

  it("does not render description when not provided", () => {
    const { container } = render(
      <EmptyState icon={Inbox} title="Empty" />
    )
    const paragraphs = container.querySelectorAll("p")
    expect(paragraphs).toHaveLength(0)
  })

  it("renders action button when actionLabel and onAction are provided", () => {
    const handleAction = vi.fn()
    render(
      <EmptyState
        icon={Inbox}
        title="No items"
        actionLabel="Add Item"
        onAction={handleAction}
      />
    )
    expect(
      screen.getByRole("button", { name: /Add Item/ })
    ).toBeInTheDocument()
  })

  it("fires onAction callback when action button is clicked", async () => {
    const user = userEvent.setup()
    const handleAction = vi.fn()
    render(
      <EmptyState
        icon={Inbox}
        title="No items"
        actionLabel="Add Item"
        onAction={handleAction}
      />
    )
    await user.click(screen.getByRole("button", { name: /Add Item/ }))
    expect(handleAction).toHaveBeenCalledTimes(1)
  })

  it("does not render action button when only actionLabel is provided (no onAction)", () => {
    render(
      <EmptyState icon={Inbox} title="No items" actionLabel="Add Item" />
    )
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })

  it("does not render action button when only onAction is provided (no actionLabel)", () => {
    render(
      <EmptyState icon={Inbox} title="No items" onAction={vi.fn()} />
    )
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })
})
