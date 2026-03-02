import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ScheduleOverviewDay {
  date: string
  total_scheduled: number
  time_off_approved: number
  net_available: number
}

interface ScheduleWeekSummaryProps {
  overview: ScheduleOverviewDay[]
}

export function ScheduleWeekSummary({ overview }: ScheduleWeekSummaryProps) {
  const { t } = useTranslation()

  return (
    <div>
      <h3 className="text-sm font-medium mb-3">
        {t("wfm.schedule.weekSummary", "Week Summary")}
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {overview.map((day) => (
          <Card key={day.date} className="text-center">
            <CardHeader className="pb-1 pt-3 px-3">
              <CardTitle className="text-xs font-medium text-muted-foreground">
                {new Date(day.date + "T00:00:00").toLocaleDateString(undefined, {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                })}
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-3 px-3 space-y-1">
              <div className="text-lg font-bold">{day.net_available}</div>
              <div className="text-xs text-muted-foreground">
                {day.total_scheduled} {t("wfm.schedule.scheduled", "sched")} / {day.time_off_approved}{" "}
                {t("wfm.schedule.off", "off")}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
