import { useForm, useFieldArray } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Trash2 } from "lucide-react"
import type { HolidayCalendar, HolidayCalendarCreate } from "@/api/holiday-calendars"

const holidayCalendarSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  description: z.string().optional().or(z.literal("")),
  entries: z.array(z.object({
    name: z.string().min(1, "Required").max(100),
    date: z.string().min(1, "Required"),
    recur_annually: z.boolean().default(false),
    all_day: z.boolean().default(true),
    start_time: z.string().optional().or(z.literal("")),
    end_time: z.string().optional().or(z.literal("")),
  })).default([]),
})

type FormValues = z.infer<typeof holidayCalendarSchema>

interface HolidayCalendarFormProps {
  holidayCalendar?: HolidayCalendar | null
  onSubmit: (data: HolidayCalendarCreate) => void
  isLoading: boolean
}

export function HolidayCalendarForm({ holidayCalendar, onSubmit, isLoading }: HolidayCalendarFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(holidayCalendarSchema) as any,
    defaultValues: {
      name: holidayCalendar?.name ?? "",
      description: holidayCalendar?.description ?? "",
      entries: holidayCalendar?.entries?.map((e) => ({
        name: e.name,
        date: e.date,
        recur_annually: e.recur_annually,
        all_day: e.all_day,
        start_time: e.start_time ?? "",
        end_time: e.end_time ?? "",
      })) ?? [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: "entries" })

  const submitHandler = (values: FormValues) => {
    const data: HolidayCalendarCreate = {
      name: values.name,
      description: values.description || undefined,
      entries: values.entries.map((e) => ({
        name: e.name,
        date: e.date,
        recur_annually: e.recur_annually,
        all_day: e.all_day,
        start_time: e.all_day ? undefined : (e.start_time || undefined),
        end_time: e.all_day ? undefined : (e.end_time || undefined),
      })),
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">{t('holidayCalendars.form.name')} *</Label>
        <Input id="name" placeholder={t('holidayCalendars.form.namePlaceholder')} {...register("name")} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('common.description')}</Label>
        <Textarea id="description" placeholder={t('common.optional')} {...register("description")} />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{t('holidayCalendars.form.holidays')}</Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ name: "", date: "", recur_annually: false, all_day: true, start_time: "", end_time: "" })}
          >
            <Plus className="mr-1 h-3 w-3" /> {t('holidayCalendars.form.addHoliday')}
          </Button>
        </div>
        <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-3">
          {fields.length === 0 && (
            <p className="text-xs text-muted-foreground py-2 text-center">{t('holidayCalendars.form.noHolidays')}</p>
          )}
          {fields.map((field, index) => {
            const isAllDay = watch(`entries.${index}.all_day`)
            return (
              <div key={field.id} className="rounded border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Entry {index + 1}</span>
                  <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('holidayCalendars.form.holidayName')} *</Label>
                    <Input {...register(`entries.${index}.name`)} placeholder="e.g. Christmas Day" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('holidayCalendars.form.date')} *</Label>
                    <Input type="date" {...register(`entries.${index}.date`)} />
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={watch(`entries.${index}.recur_annually`)}
                      onCheckedChange={(v) => setValue(`entries.${index}.recur_annually`, !!v)}
                    />
                    <Label className="text-xs">{t('holidayCalendars.form.recurring')}</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={isAllDay}
                      onCheckedChange={(v) => setValue(`entries.${index}.all_day`, !!v)}
                    />
                    <Label className="text-xs">All Day</Label>
                  </div>
                </div>
                {!isAllDay && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs">Start Time</Label>
                      <Input type="time" {...register(`entries.${index}.start_time`)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">End Time</Label>
                      <Input type="time" {...register(`entries.${index}.end_time`)} />
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : holidayCalendar ? t('holidayCalendars.form.updateButton') : t('holidayCalendars.form.createButton')}
      </Button>
    </form>
  )
}
