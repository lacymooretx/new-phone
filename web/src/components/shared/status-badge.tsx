import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"

interface StatusBadgeProps {
  active: boolean
  activeLabel?: string
  inactiveLabel?: string
}

export function StatusBadge({ active, activeLabel, inactiveLabel }: StatusBadgeProps) {
  const { t } = useTranslation()
  const label = active ? (activeLabel ?? t('common.active')) : (inactiveLabel ?? t('common.inactive'))
  return (
    <Badge variant={active ? "default" : "secondary"}>
      {label}
    </Badge>
  )
}
