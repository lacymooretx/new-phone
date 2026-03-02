import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect } from "vitest"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"

describe("Dialog", () => {
  it("does not render content when closed", () => {
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Title</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    expect(screen.queryByText("Title")).not.toBeInTheDocument()
  })

  it("opens when trigger is clicked", async () => {
    const user = userEvent.setup()
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>My Dialog</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    await user.click(screen.getByText("Open"))
    expect(screen.getByText("My Dialog")).toBeInTheDocument()
  })

  it("renders title and description", async () => {
    const user = userEvent.setup()
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dialog Title</DialogTitle>
            <DialogDescription>This is a description</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    await user.click(screen.getByText("Open"))
    expect(screen.getByText("Dialog Title")).toBeInTheDocument()
    expect(screen.getByText("This is a description")).toBeInTheDocument()
  })

  it("renders close button by default and closes dialog on click", async () => {
    const user = userEvent.setup()
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Closable</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    await user.click(screen.getByText("Open"))
    expect(screen.getByText("Closable")).toBeInTheDocument()

    // The close button has "Close" as sr-only text
    const closeBtn = screen.getByRole("button", { name: "Close" })
    await user.click(closeBtn)
    await waitFor(() => {
      expect(screen.queryByText("Closable")).not.toBeInTheDocument()
    })
  })

  it("hides close button when showCloseButton is false", async () => {
    const user = userEvent.setup()
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>No Close</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    await user.click(screen.getByText("Open"))
    expect(screen.getByText("No Close")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument()
  })

  it("renders footer content", async () => {
    const user = userEvent.setup()
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>With Footer</DialogTitle>
          </DialogHeader>
          <DialogFooter>
            <button>Save</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
    await user.click(screen.getByText("Open"))
    expect(screen.getByText("Save")).toBeInTheDocument()
  })

  it("works in controlled mode with open prop", () => {
    render(
      <Dialog open>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Controlled</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
    expect(screen.getByText("Controlled")).toBeInTheDocument()
  })
})
