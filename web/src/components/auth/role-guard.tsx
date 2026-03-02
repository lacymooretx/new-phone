import { type ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/stores/auth-store"
import { hasPermission, type Permission } from "@/lib/constants"

interface RoleGuardProps {
  permission: Permission
  children: ReactNode
  fallback?: ReactNode
}

export function RoleGuard({ permission, children, fallback }: RoleGuardProps) {
  const { t } = useTranslation()
  const role = useAuthStore((s) => s.user?.role)

  if (!role || !hasPermission(role, permission)) {
    return fallback ?? (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold">{t('auth.accessDenied')}</h2>
          <p className="text-muted-foreground mt-2">{t('auth.noPermission')}</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
