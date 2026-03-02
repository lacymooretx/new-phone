import { useEffect } from "react"
import { Navigate, Outlet } from "react-router"
import { useAuthStore } from "@/stores/auth-store"
import { Skeleton } from "@/components/ui/skeleton"

export function AuthGuard() {
  const { isAuthenticated, isBootstrapping, bootstrap } = useAuthStore()

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  if (isBootstrapping) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="space-y-4 w-64">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
