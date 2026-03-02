import { useTranslation } from "react-i18next"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface ScheduleToolbarProps {
  weekLabel: string
  weekOffset: number
  onPrevWeek: () => void
  onNextWeek: () => void
  onToday: () => void
  filterExtensionId: string
  onFilterChange: (value: string) => void
}

export function ScheduleToolbar({
  weekLabel,
  weekOffset,
  onPrevWeek,
  onNextWeek,
  onToday,
  filterExtensionId,
  onFilterChange,
}: ScheduleToolbarProps) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onPrevWeek}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-medium min-w-[220px] text-center">
          {weekLabel}
        </span>
        <Button variant="outline" size="sm" onClick={onNextWeek}>
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToday}
          disabled={weekOffset === 0}
        >
          {t("wfm.schedule.today", "Today")}
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <Label className="text-sm">{t("wfm.schedule.filterExtension", "Extension")}</Label>
        <Input
          placeholder={t("wfm.schedule.filterPlaceholder", "Filter by ID...")}
          value={filterExtensionId}
          onChange={(e) => onFilterChange(e.target.value)}
          className="w-40 h-8"
        />
      </div>
    </div>
  )
}
