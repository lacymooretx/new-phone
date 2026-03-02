import { useState, useMemo } from "react"
import { useExtensions } from "@/api/extensions"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"

interface ExtensionPickerProps {
  value: string[]
  onChange: (ids: string[]) => void
}

export function ExtensionPicker({ value, onChange }: ExtensionPickerProps) {
  const { data: extensions } = useExtensions()
  const [search, setSearch] = useState("")

  const filtered = useMemo(() => {
    if (!extensions) return []
    if (!search) return extensions
    const q = search.toLowerCase()
    return extensions.filter(
      (ext) =>
        ext.extension_number.toLowerCase().includes(q) ||
        (ext.internal_cid_name ?? "").toLowerCase().includes(q)
    )
  }, [extensions, search])

  const toggle = (id: string) => {
    if (value.includes(id)) {
      onChange(value.filter((v) => v !== id))
    } else {
      onChange([...value, id])
    }
  }

  return (
    <div className="space-y-2">
      <Label>Members</Label>
      <Input
        placeholder="Search extensions..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="max-h-48 overflow-y-auto rounded border p-2 space-y-1">
        {filtered.length === 0 && (
          <p className="text-xs text-muted-foreground py-2 text-center">No extensions found</p>
        )}
        {filtered.map((ext) => (
          <label key={ext.id} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-muted cursor-pointer">
            <Checkbox
              checked={value.includes(ext.id)}
              onCheckedChange={() => toggle(ext.id)}
            />
            <span className="text-sm font-medium">{ext.extension_number}</span>
            {ext.internal_cid_name && (
              <span className="text-xs text-muted-foreground">{ext.internal_cid_name}</span>
            )}
          </label>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{value.length} selected</p>
    </div>
  )
}
