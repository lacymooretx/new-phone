import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { exportToCsv } from "../export-csv"

let capturedBlob: Blob | null = null
const mockClick = vi.fn()
const mockAnchor: { href: string; download: string; click: typeof mockClick } = {
  href: "",
  download: "",
  click: mockClick,
}

beforeEach(() => {
  capturedBlob = null
  mockAnchor.href = ""
  mockAnchor.download = ""
  mockClick.mockClear()

  vi.spyOn(document, "createElement").mockReturnValue(mockAnchor as unknown as HTMLElement)
  vi.spyOn(URL, "createObjectURL").mockImplementation((obj: Blob | MediaSource) => {
    capturedBlob = obj as Blob
    return "blob:test"
  })
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

const columns = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email" },
]

describe("exportToCsv()", () => {
  it("generates correct CSV content with headers and rows", async () => {
    const data = [
      { name: "Alice", email: "alice@example.com" },
      { name: "Bob", email: "bob@example.com" },
    ]

    exportToCsv(data, columns, "users")

    const text = await capturedBlob!.text()
    const lines = text.split("\n")
    expect(lines[0]).toBe("Name,Email")
    expect(lines[1]).toBe("Alice,alice@example.com")
    expect(lines[2]).toBe("Bob,bob@example.com")
    expect(lines).toHaveLength(3)
  })

  it("escapes values containing commas by wrapping in quotes", async () => {
    const data = [{ name: "Doe, Jane", email: "jane@example.com" }]

    exportToCsv(data, columns, "users")

    const text = await capturedBlob!.text()
    const lines = text.split("\n")
    expect(lines[1]).toBe('"Doe, Jane",jane@example.com')
  })

  it("escapes values containing double quotes by doubling them", async () => {
    const data = [{ name: 'She said "hi"', email: "test@example.com" }]

    exportToCsv(data, columns, "users")

    const text = await capturedBlob!.text()
    const lines = text.split("\n")
    expect(lines[1]).toBe('"She said ""hi""",test@example.com')
  })

  it("escapes values containing newlines", async () => {
    const data = [{ name: "Line1\nLine2", email: "test@example.com" }]

    exportToCsv(data, columns, "users")

    const text = await capturedBlob!.text()
    // The value with a newline should be wrapped in quotes
    expect(text).toContain('"Line1\nLine2"')
  })

  it("handles null and undefined values as empty strings", async () => {
    const data = [
      { name: null, email: undefined },
    ]

    exportToCsv(data, columns, "users")

    const text = await capturedBlob!.text()
    const lines = text.split("\n")
    expect(lines[1]).toBe(",")
  })

  it("creates download link with correct filename format including date", () => {
    const data = [{ name: "Alice", email: "alice@example.com" }]

    exportToCsv(data, columns, "report")

    expect(mockClick).toHaveBeenCalledOnce()
    expect(mockAnchor.href).toBe("blob:test")
    // Filename should match pattern: report-YYYY-MM-DD.csv
    expect(mockAnchor.download).toMatch(/^report-\d{4}-\d{2}-\d{2}\.csv$/)
  })

  it("works with empty data array producing headers only", async () => {
    exportToCsv([], columns, "empty")

    const text = await capturedBlob!.text()
    expect(text).toBe("Name,Email")
    expect(mockClick).toHaveBeenCalledOnce()
  })
})
