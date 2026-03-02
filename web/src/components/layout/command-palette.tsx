import { useState, useEffect, useMemo, useCallback } from "react"
import { useNavigate } from "react-router"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/stores/auth-store"
import { hasPermission, isMspRole } from "@/lib/constants"
import { getAllNavItems } from "@/lib/nav-items"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Search, Keyboard } from "lucide-react"
import { cn } from "@/lib/utils"
import { KeyboardShortcutsDialog } from "./keyboard-shortcuts-dialog"

const NAV_ENTRIES = getAllNavItems()

export function CommandPalette() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const navigate = useNavigate()
  const role = useAuthStore((s) => s.user?.role)

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen((v) => !v)
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "/") {
        e.preventDefault()
        setShortcutsOpen(true)
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [])

  const filtered = useMemo(() => {
    if (!role) return []
    const items = NAV_ENTRIES.filter((entry) => {
      if (entry.group === "nav.msp" && !isMspRole(role)) return false
      if (entry.permission && !hasPermission(role, entry.permission)) return false
      if (!query) return true
      return t(entry.labelKey).toLowerCase().includes(query.toLowerCase())
    })
    return items
  }, [role, query, t])

  const handleQueryChange = useCallback((value: string) => {
    setQuery(value)
    setSelectedIndex(0)
  }, [])

  const handleSelect = (path: string) => {
    setOpen(false)
    setQuery("")
    navigate(path)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === "Enter" && filtered[selectedIndex]) {
      e.preventDefault()
      handleSelect(filtered[selectedIndex].path)
    }
  }

  return (
    <>
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setQuery("") }}>
      <DialogContent className="p-0 gap-0 max-w-lg">
        <div className="flex items-center border-b px-3">
          <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
          <Input
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('shortcuts.searchPages')}
            className="border-0 focus-visible:ring-0 shadow-none h-11"
            autoFocus
          />
          <kbd className="ml-2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">
            ESC
          </kbd>
        </div>
        <div className="max-h-72 overflow-y-auto p-1">
          {filtered.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">{t('common.noResultsFound')}</p>
          )}
          {filtered.map((entry, i) => (
            <button
              key={entry.path}
              onClick={() => handleSelect(entry.path)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-left transition-colors",
                i === selectedIndex
                  ? "bg-accent text-accent-foreground"
                  : "text-foreground/80 hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <entry.icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{t(entry.labelKey)}</span>
              {entry.group && (
                <span className="text-xs text-muted-foreground">{t(entry.group)}</span>
              )}
            </button>
          ))}
          {(!query || "keyboard shortcuts".includes(query.toLowerCase())) && (
            <button
              onClick={() => { setOpen(false); setQuery(""); setShortcutsOpen(true) }}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-left transition-colors text-foreground/80 hover:bg-accent hover:text-accent-foreground"
            >
              <Keyboard className="h-4 w-4 shrink-0" />
              <span className="flex-1">{t('shortcuts.keyboardShortcuts')}</span>
              <span className="text-xs text-muted-foreground">{"\u2318"}?</span>
            </button>
          )}
        </div>
      </DialogContent>
    </Dialog>
    <KeyboardShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </>
  )
}
