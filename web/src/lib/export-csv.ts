/**
 * Generic CSV export utility for DataTable data.
 * Takes an array of objects and exports specified fields as a CSV download.
 */

interface ExportColumn {
  key: string
  label: string
}

export function exportToCsv(
  data: object[],
  columns: ExportColumn[],
  filename: string
): void {
  const escape = (val: unknown): string => {
    const str = val == null ? "" : String(val)
    return str.includes(",") || str.includes('"') || str.includes("\n")
      ? `"${str.replace(/"/g, '""')}"`
      : str
  }

  const headers = columns.map((c) => escape(c.label)).join(",")
  const rows = data.map((row) =>
    columns.map((c) => escape((row as Record<string, unknown>)[c.key])).join(",")
  )
  const csv = [headers, ...rows].join("\n")

  const blob = new Blob([csv], { type: "text/csv" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${filename}-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
