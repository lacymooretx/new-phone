import { Link, useLocation } from "react-router"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/stores/auth-store"
import { hasPermission, isMspRole } from "@/lib/constants"
import { NAV_GROUPS } from "@/lib/nav-items"
import { X } from "lucide-react"
import { ConnectLogo } from "@/components/connect-logo"
import { Button } from "@/components/ui/button"

interface SidebarProps {
  open: boolean
  onToggle: () => void
}

export function Sidebar({ open, onToggle }: SidebarProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const role = useAuthStore((s) => s.user?.role)

  if (!role) return null

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onToggle}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-sidebar text-sidebar-foreground transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <ConnectLogo className="h-6 w-6" />
            <span>Connect</span>
          </Link>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 overflow-y-auto p-3">
          {NAV_GROUPS.map((group) => {
            if (group.mspOnly && !isMspRole(role)) return null

            const visibleItems = group.items.filter(
              (item) => item.permission === null || hasPermission(role, item.permission)
            )
            if (visibleItems.length === 0) return null

            return (
              <div key={group.labelKey || "top"} className={cn("mb-3", group.mspOnly && "border-t pt-3 mt-2")}>
                {group.labelKey && !group.mspOnly && (
                  <div className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                    {t(group.labelKey)}
                  </div>
                )}
                <div className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const isActive = item.path === "/"
                      ? location.pathname === "/"
                      : location.pathname.startsWith(item.path)
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                          isActive
                            ? "bg-sidebar-accent text-sidebar-accent-foreground"
                            : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                        )}
                      >
                        <item.icon className="h-4 w-4" />
                        {t(item.labelKey)}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </nav>
      </aside>
    </>
  )
}
