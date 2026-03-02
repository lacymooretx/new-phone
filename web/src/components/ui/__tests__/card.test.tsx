import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "@/components/ui/card"

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText("Card content")).toBeInTheDocument()
  })

  it('has data-slot="card"', () => {
    render(<Card data-testid="card">test</Card>)
    expect(screen.getByTestId("card")).toHaveAttribute("data-slot", "card")
  })

  it("applies custom className", () => {
    render(
      <Card data-testid="card" className="custom-card">
        test
      </Card>
    )
    expect(screen.getByTestId("card")).toHaveClass("custom-card")
  })
})

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>Header content</CardHeader>)
    expect(screen.getByText("Header content")).toBeInTheDocument()
  })

  it('has data-slot="card-header"', () => {
    render(<CardHeader data-testid="header">test</CardHeader>)
    expect(screen.getByTestId("header")).toHaveAttribute(
      "data-slot",
      "card-header"
    )
  })
})

describe("CardTitle", () => {
  it("renders title text", () => {
    render(<CardTitle>My Title</CardTitle>)
    expect(screen.getByText("My Title")).toBeInTheDocument()
  })

  it('has data-slot="card-title"', () => {
    render(<CardTitle data-testid="title">test</CardTitle>)
    expect(screen.getByTestId("title")).toHaveAttribute(
      "data-slot",
      "card-title"
    )
  })
})

describe("CardDescription", () => {
  it("renders description text", () => {
    render(<CardDescription>Some description</CardDescription>)
    expect(screen.getByText("Some description")).toBeInTheDocument()
  })

  it('has data-slot="card-description"', () => {
    render(<CardDescription data-testid="desc">test</CardDescription>)
    expect(screen.getByTestId("desc")).toHaveAttribute(
      "data-slot",
      "card-description"
    )
  })
})

describe("CardContent", () => {
  it("renders content", () => {
    render(<CardContent>Body content</CardContent>)
    expect(screen.getByText("Body content")).toBeInTheDocument()
  })

  it('has data-slot="card-content"', () => {
    render(<CardContent data-testid="content">test</CardContent>)
    expect(screen.getByTestId("content")).toHaveAttribute(
      "data-slot",
      "card-content"
    )
  })
})

describe("CardFooter", () => {
  it("renders footer content", () => {
    render(<CardFooter>Footer content</CardFooter>)
    expect(screen.getByText("Footer content")).toBeInTheDocument()
  })

  it('has data-slot="card-footer"', () => {
    render(<CardFooter data-testid="footer">test</CardFooter>)
    expect(screen.getByTestId("footer")).toHaveAttribute(
      "data-slot",
      "card-footer"
    )
  })
})

describe("CardAction", () => {
  it("renders action content", () => {
    render(<CardAction>Action</CardAction>)
    expect(screen.getByText("Action")).toBeInTheDocument()
  })

  it('has data-slot="card-action"', () => {
    render(<CardAction data-testid="action">test</CardAction>)
    expect(screen.getByTestId("action")).toHaveAttribute(
      "data-slot",
      "card-action"
    )
  })
})

describe("Card composition", () => {
  it("renders a full card with all sub-components", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
          <CardAction>
            <button>Edit</button>
          </CardAction>
        </CardHeader>
        <CardContent>Main body</CardContent>
        <CardFooter>
          <button>Save</button>
        </CardFooter>
      </Card>
    )
    expect(screen.getByText("Title")).toBeInTheDocument()
    expect(screen.getByText("Description")).toBeInTheDocument()
    expect(screen.getByText("Main body")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument()
  })
})
