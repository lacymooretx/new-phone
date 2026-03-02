import type { LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ icon: Icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-3 mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>}
      {actionLabel && onAction && (
        <Button size="sm" className="mt-4" onClick={onAction}>
          <Plus className="mr-1 h-4 w-4" /> {actionLabel}
        </Button>
      )}
    </div>
  )
}
