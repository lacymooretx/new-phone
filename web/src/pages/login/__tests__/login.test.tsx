import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { LoginPage } from "../login-page"

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  }
})

describe("LoginPage", () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    // Reset auth store
    localStorage.clear()
  })

  it("renders the app name heading", () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText("New Phone")).toBeInTheDocument()
  })

  it("renders the sign-in subtitle", () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText("Sign in to your account")).toBeInTheDocument()
  })

  it("renders an email input field", () => {
    renderWithProviders(<LoginPage />)
    const emailInput = screen.getByLabelText("Email")
    expect(emailInput).toBeInTheDocument()
    expect(emailInput).toHaveAttribute("type", "email")
  })

  it("renders a password input field", () => {
    renderWithProviders(<LoginPage />)
    const passwordInput = screen.getByLabelText("Password")
    expect(passwordInput).toBeInTheDocument()
    expect(passwordInput).toHaveAttribute("type", "password")
  })

  it("renders a sign-in button", () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument()
  })

  it("renders a forgot password link", () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText("Forgot password?")).toBeInTheDocument()
  })

  it("allows typing in the email field", async () => {
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)
    const emailInput = screen.getByLabelText("Email")
    await user.type(emailInput, "admin@test.com")
    expect(emailInput).toHaveValue("admin@test.com")
  })

  it("allows typing in the password field", async () => {
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)
    const passwordInput = screen.getByLabelText("Password")
    await user.type(passwordInput, "password123")
    expect(passwordInput).toHaveValue("password123")
  })

  it("shows error message on failed login", async () => {
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    await user.type(screen.getByLabelText("Email"), "bad@test.com")
    await user.type(screen.getByLabelText("Password"), "wrongpassword")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument()
    })
  })

  it("shows loading state during login submission", async () => {
    // Add a delay to the login handler so we can observe the loading state
    server.use(
      http.post("/api/v1/auth/login", async () => {
        await new Promise((resolve) => setTimeout(resolve, 200))
        return HttpResponse.json({ detail: "Invalid credentials" }, { status: 401 })
      })
    )

    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    await user.type(screen.getByLabelText("Email"), "admin@test.com")
    await user.type(screen.getByLabelText("Password"), "password123")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Signing in..." })).toBeInTheDocument()
    })
  })

  it("navigates after successful login", async () => {
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    await user.type(screen.getByLabelText("Email"), "admin@test.com")
    await user.type(screen.getByLabelText("Password"), "password123")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/")
    })
  })

  it("has the email field focused by default", () => {
    renderWithProviders(<LoginPage />)
    const emailInput = screen.getByLabelText("Email")
    expect(emailInput).toHaveFocus()
  })

  it("email field has correct placeholder", () => {
    renderWithProviders(<LoginPage />)
    const emailInput = screen.getByLabelText("Email")
    expect(emailInput).toHaveAttribute("placeholder", "admin@example.com")
  })
})
