import { useNavigate } from "react-router"
import { useTranslation } from "react-i18next"
import { useTheme } from "next-themes"
import { useAuthStore } from "@/stores/auth-store"
import { useUsers } from "@/api/users"
import { isMspRole } from "@/lib/constants"
import { Menu, LogOut, Moon, Sun, Monitor, Search, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { TenantPicker } from "./tenant-picker"

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { setTheme, theme } = useTheme()
  const { data: users } = useUsers()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  const currentUser = users?.find((u) => u.id === user?.id)
  const displayName = currentUser
    ? `${currentUser.first_name} ${currentUser.last_name}`.trim()
    : null
  const displayEmail = currentUser?.email ?? null
  const initials = currentUser
    ? `${currentUser.first_name?.[0] ?? ""}${currentUser.last_name?.[0] ?? ""}`.toUpperCase()
    : user?.role.slice(0, 2).toUpperCase() ?? "?"
  const roleLabel = user?.role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) ?? ""

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-background px-4">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick}>
        <Menu className="h-5 w-5" />
      </Button>

      <button
        onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
        className="hidden md:inline-flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted transition-colors"
      >
        <Search className="h-3.5 w-3.5" />
        <span>{t('header.search')}</span>
        <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-background px-1.5 font-mono text-[10px] font-medium">
          ⌘K
        </kbd>
      </button>

      <div className="flex-1" />

      {user && isMspRole(user.role) && <TenantPicker />}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative h-8 w-8 rounded-full">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              {displayName && <p className="text-sm font-medium">{displayName}</p>}
              {displayEmail && <p className="text-xs text-muted-foreground">{displayEmail}</p>}
              <Badge variant="secondary" className="w-fit text-xs">{roleLabel}</Badge>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/profile")}>
            <User className="mr-2 h-4 w-4" />
            {t('header.profile')}
          </DropdownMenuItem>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              {theme === "dark" ? (
                <Moon className="mr-2 h-4 w-4" />
              ) : theme === "light" ? (
                <Sun className="mr-2 h-4 w-4" />
              ) : (
                <Monitor className="mr-2 h-4 w-4" />
              )}
              {t('header.theme')}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuItem onClick={() => setTheme("light")}>
                <Sun className="mr-2 h-4 w-4" /> {t('header.themeLight')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("dark")}>
                <Moon className="mr-2 h-4 w-4" /> {t('header.themeDark')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("system")}>
                <Monitor className="mr-2 h-4 w-4" /> {t('header.themeSystem')}
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            {t('header.logOut')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
