import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  TableFooter,
} from "@/components/ui/table"

describe("Table", () => {
  it("renders a table element", () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("table")).toBeInTheDocument()
  })

  it('has data-slot="table"', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("table")).toHaveAttribute("data-slot", "table")
  })

  it("applies custom className to table", () => {
    render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("table")).toHaveClass("custom-table")
  })

  it("wraps table in a scroll container", () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    const container = screen.getByRole("table").parentElement!
    expect(container).toHaveAttribute("data-slot", "table-container")
  })
})

describe("TableHeader", () => {
  it("renders thead element", () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>John</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument()
  })

  it('has data-slot="table-header"', () => {
    const { container } = render(
      <Table>
        <TableHeader data-testid="thead">
          <TableRow>
            <TableHead>H</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    )
    expect(container.querySelector("thead")).toHaveAttribute(
      "data-slot",
      "table-header"
    )
  })
})

describe("TableBody", () => {
  it('has data-slot="table-body"', () => {
    const { container } = render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>C</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(container.querySelector("tbody")).toHaveAttribute(
      "data-slot",
      "table-body"
    )
  })
})

describe("TableRow", () => {
  it("renders row with cells", () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>A</TableCell>
            <TableCell>B</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("row")).toBeInTheDocument()
    expect(screen.getByText("A")).toBeInTheDocument()
    expect(screen.getByText("B")).toBeInTheDocument()
  })

  it('has data-slot="table-row"', () => {
    render(
      <Table>
        <TableBody>
          <TableRow data-testid="row">
            <TableCell>C</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByTestId("row")).toHaveAttribute("data-slot", "table-row")
  })
})

describe("TableHead", () => {
  it("renders as <th>", () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Column</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    )
    expect(screen.getByRole("columnheader", { name: "Column" }).tagName).toBe("TH")
  })

  it('has data-slot="table-head"', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead data-testid="th">Col</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    )
    expect(screen.getByTestId("th")).toHaveAttribute("data-slot", "table-head")
  })
})

describe("TableCell", () => {
  it("renders as <td>", () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByRole("cell", { name: "Data" }).tagName).toBe("TD")
  })

  it('has data-slot="table-cell"', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell data-testid="td">D</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByTestId("td")).toHaveAttribute("data-slot", "table-cell")
  })
})

describe("TableCaption", () => {
  it("renders caption text", () => {
    render(
      <Table>
        <TableCaption>A list of users</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>John</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByText("A list of users")).toBeInTheDocument()
  })

  it('has data-slot="table-caption"', () => {
    render(
      <Table>
        <TableCaption data-testid="caption">Cap</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>C</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByTestId("caption")).toHaveAttribute(
      "data-slot",
      "table-caption"
    )
  })
})

describe("TableFooter", () => {
  it("renders footer content", () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>D</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Total</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    )
    expect(screen.getByText("Total")).toBeInTheDocument()
  })

  it('has data-slot="table-footer"', () => {
    const { container } = render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>D</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>T</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    )
    expect(container.querySelector("tfoot")).toHaveAttribute(
      "data-slot",
      "table-footer"
    )
  })
})

describe("Table composition", () => {
  it("renders a full table with header, body, footer, and caption", () => {
    render(
      <Table>
        <TableCaption>User table</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Role</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Alice</TableCell>
            <TableCell>Admin</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Bob</TableCell>
            <TableCell>User</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Total</TableCell>
            <TableCell>2</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    )
    expect(screen.getByText("User table")).toBeInTheDocument()
    expect(screen.getAllByRole("row")).toHaveLength(4) // header + 2 body + footer
    expect(screen.getByText("Alice")).toBeInTheDocument()
    expect(screen.getByText("Bob")).toBeInTheDocument()
  })
})
