import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export interface DateRange {
  from: string
  to: string
}

interface DateRangePickerProps {
  value: DateRange
  onChange: (range: DateRange) => void
}

type Preset = "today" | "yesterday" | "this_week" | "last_week" | "this_month" | "last_month" | "last_7_days" | "last_30_days" | "custom"

function getPresetRange(preset: Preset): DateRange | null {
  const now = new Date()
  const today = now.toISOString().slice(0, 10)
  const yesterday = new Date(now.getTime() - 86400000).toISOString().slice(0, 10)
  const dayOfWeek = now.getDay()
  const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1

  switch (preset) {
    case "today":
      return { from: today, to: today }
    case "yesterday":
      return { from: yesterday, to: yesterday }
    case "this_week": {
      const monday = new Date(now.getTime() - mondayOffset * 86400000)
      return { from: monday.toISOString().slice(0, 10), to: today }
    }
    case "last_week": {
      const lastMonday = new Date(now.getTime() - (mondayOffset + 7) * 86400000)
      const lastSunday = new Date(lastMonday.getTime() + 6 * 86400000)
      return { from: lastMonday.toISOString().slice(0, 10), to: lastSunday.toISOString().slice(0, 10) }
    }
    case "this_month": {
      const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
      return { from: firstOfMonth.toISOString().slice(0, 10), to: today }
    }
    case "last_month": {
      const firstLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const lastDayLastMonth = new Date(now.getFullYear(), now.getMonth(), 0)
      return { from: firstLastMonth.toISOString().slice(0, 10), to: lastDayLastMonth.toISOString().slice(0, 10) }
    }
    case "last_7_days": {
      const sevenDaysAgo = new Date(now.getTime() - 7 * 86400000)
      return { from: sevenDaysAgo.toISOString().slice(0, 10), to: today }
    }
    case "last_30_days": {
      const thirtyDaysAgo = new Date(now.getTime() - 30 * 86400000)
      return { from: thirtyDaysAgo.toISOString().slice(0, 10), to: today }
    }
    case "custom":
      return null
  }
}

function detectPreset(range: DateRange): Preset {
  const presets: Preset[] = ["today", "yesterday", "this_week", "last_week", "this_month", "last_month", "last_7_days", "last_30_days"]
  for (const preset of presets) {
    const r = getPresetRange(preset)
    if (r && r.from === range.from && r.to === range.to) return preset
  }
  return "custom"
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const { t } = useTranslation()
  const activePreset = useMemo(() => detectPreset(value), [value])

  const handlePresetChange = (preset: string) => {
    const range = getPresetRange(preset as Preset)
    if (range) onChange(range)
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <Label className="text-xs text-muted-foreground mb-1 block">{t("analytics.preset")}</Label>
        <Select value={activePreset} onValueChange={handlePresetChange}>
          <SelectTrigger className="w-[160px]" size="sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">{t("analytics.presets.today")}</SelectItem>
            <SelectItem value="yesterday">{t("analytics.presets.yesterday")}</SelectItem>
            <SelectItem value="last_7_days">{t("analytics.presets.last7Days")}</SelectItem>
            <SelectItem value="last_30_days">{t("analytics.presets.last30Days")}</SelectItem>
            <SelectItem value="this_week">{t("analytics.presets.thisWeek")}</SelectItem>
            <SelectItem value="last_week">{t("analytics.presets.lastWeek")}</SelectItem>
            <SelectItem value="this_month">{t("analytics.presets.thisMonth")}</SelectItem>
            <SelectItem value="last_month">{t("analytics.presets.lastMonth")}</SelectItem>
            <SelectItem value="custom">{t("analytics.presets.custom")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-xs text-muted-foreground mb-1 block">{t("analytics.from")}</Label>
        <Input
          type="date"
          className="h-8 w-[150px] text-sm"
          value={value.from}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
        />
      </div>
      <div>
        <Label className="text-xs text-muted-foreground mb-1 block">{t("analytics.to")}</Label>
        <Input
          type="date"
          className="h-8 w-[150px] text-sm"
          value={value.to}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
        />
      </div>
    </div>
  )
}
