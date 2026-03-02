import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeAll } from "vitest"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from "@/components/ui/select"

// Radix Select uses scrollIntoView which jsdom does not implement
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  // Radix also relies on hasPointerCapture / setPointerCapture / releasePointerCapture
  Element.prototype.hasPointerCapture = vi.fn().mockReturnValue(false)
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

describe("Select", () => {
  it("renders trigger with placeholder text", () => {
    render(
      <Select>
        <SelectTrigger>
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">Option A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByText("Pick one")).toBeInTheDocument()
  })

  it("trigger has combobox role", () => {
    render(
      <Select>
        <SelectTrigger>
          <SelectValue placeholder="Choose" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toBeInTheDocument()
  })

  it("applies custom className to trigger", () => {
    render(
      <Select>
        <SelectTrigger className="custom-trigger">
          <SelectValue placeholder="Test" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toHaveClass("custom-trigger")
  })

  it('trigger has data-slot="select-trigger"', () => {
    render(
      <Select>
        <SelectTrigger>
          <SelectValue placeholder="Slot" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toHaveAttribute(
      "data-slot",
      "select-trigger"
    )
  })

  it("applies data-size attribute to trigger", () => {
    render(
      <Select>
        <SelectTrigger size="sm">
          <SelectValue placeholder="Small" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toHaveAttribute("data-size", "sm")
  })

  it("renders content with options when open is controlled", () => {
    render(
      <Select open>
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value="alpha">Alpha</SelectItem>
          <SelectItem value="beta">Beta</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("option", { name: "Alpha" })).toBeInTheDocument()
    expect(screen.getByRole("option", { name: "Beta" })).toBeInTheDocument()
  })

  it("displays selected value when controlled with value prop", () => {
    render(
      <Select value="alpha">
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="alpha">Alpha</SelectItem>
          <SelectItem value="beta">Beta</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByText("Alpha")).toBeInTheDocument()
  })

  it("fires onValueChange when an option is selected", async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()
    render(
      <Select open onValueChange={handleChange}>
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value="alpha">Alpha</SelectItem>
          <SelectItem value="beta">Beta</SelectItem>
        </SelectContent>
      </Select>
    )
    await user.click(screen.getByRole("option", { name: "Alpha" }))
    expect(handleChange).toHaveBeenCalledWith("alpha")
  })

  it("renders group with label when open", () => {
    render(
      <Select open>
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectGroup>
            <SelectLabel>Fruits</SelectLabel>
            <SelectItem value="apple">Apple</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    )
    expect(screen.getByText("Fruits")).toBeInTheDocument()
    expect(screen.getByRole("option", { name: "Apple" })).toBeInTheDocument()
  })

  it("trigger shows aria-expanded false when closed", () => {
    render(
      <Select>
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toHaveAttribute("aria-expanded", "false")
  })

  it("disabled trigger has disabled attribute", () => {
    render(
      <Select disabled>
        <SelectTrigger>
          <SelectValue placeholder="Pick" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">A</SelectItem>
        </SelectContent>
      </Select>
    )
    expect(screen.getByRole("combobox")).toBeDisabled()
  })
})
