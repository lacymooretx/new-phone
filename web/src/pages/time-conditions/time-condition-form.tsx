import { useForm, useFieldArray } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Checkbox } from "@/components/ui/checkbox"
import { Plus, Trash2 } from "lucide-react"
import { DestinationPicker, HolidayCalendarPicker } from "@/components/shared/destination-picker"
import { TimezoneSelect } from "@/components/shared/timezone-select"
import type { TimeCondition, TimeConditionCreate } from "@/api/time-conditions"

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

const RULE_TYPES = [
  { value: "day_of_week", label: "Day of Week" },
  { value: "time_of_day", label: "Time of Day" },
  { value: "specific_date", label: "Specific Date" },
  { value: "date_range", label: "Date Range" },
]

const DESTINATION_TYPES = [
  { value: "extension", label: "Extension" },
  { value: "ring_group", label: "Ring Group" },
  { value: "voicemail", label: "Voicemail" },
  { value: "ivr", label: "IVR" },
  { value: "queue", label: "Queue" },
  { value: "conference", label: "Conference" },
  { value: "external", label: "External" },
  { value: "terminate", label: "Terminate" },
]

const timeConditionSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  description: z.string().optional().or(z.literal("")),
  timezone: z.string().default("America/New_York"),
  match_destination_type: z.string().min(1, "Required"),
  match_destination_id: z.string().optional().or(z.literal("")),
  nomatch_destination_type: z.string().min(1, "Required"),
  nomatch_destination_id: z.string().optional().or(z.literal("")),
  holiday_calendar_id: z.string().optional().or(z.literal("")),
  enabled: z.boolean().default(true),
  rules: z.array(z.object({
    type: z.string().min(1, "Required"),
    days: z.array(z.number()).optional(),
    start_time: z.string().optional().or(z.literal("")),
    end_time: z.string().optional().or(z.literal("")),
    start_date: z.string().optional().or(z.literal("")),
    end_date: z.string().optional().or(z.literal("")),
    invert: z.boolean().default(false),
    label: z.string().optional().or(z.literal("")),
  })).default([]),
})

type FormValues = z.infer<typeof timeConditionSchema>

function DayOfWeekPicker({ value, onChange }: { value: number[]; onChange: (days: number[]) => void }) {
  const toggle = (day: number) => {
    if (value.includes(day)) {
      onChange(value.filter((d) => d !== day))
    } else {
      onChange([...value, day].sort())
    }
  }

  return (
    <div className="flex gap-1">
      {DAY_NAMES.map((name, i) => {
        const dayNum = i + 1
        return (
          <label key={dayNum} className="flex items-center gap-1 rounded border px-2 py-1 cursor-pointer hover:bg-muted">
            <Checkbox checked={value.includes(dayNum)} onCheckedChange={() => toggle(dayNum)} />
            <span className="text-xs">{name}</span>
          </label>
        )
      })}
    </div>
  )
}

interface TimeConditionFormProps {
  timeCondition?: TimeCondition | null
  onSubmit: (data: TimeConditionCreate) => void
  isLoading: boolean
}

export function TimeConditionForm({ timeCondition, onSubmit, isLoading }: TimeConditionFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(timeConditionSchema) as any,
    defaultValues: {
      name: timeCondition?.name ?? "",
      description: timeCondition?.description ?? "",
      timezone: timeCondition?.timezone ?? "America/New_York",
      match_destination_type: timeCondition?.match_destination_type ?? "",
      match_destination_id: timeCondition?.match_destination_id ?? "",
      nomatch_destination_type: timeCondition?.nomatch_destination_type ?? "",
      nomatch_destination_id: timeCondition?.nomatch_destination_id ?? "",
      holiday_calendar_id: timeCondition?.holiday_calendar_id ?? "",
      enabled: timeCondition?.enabled ?? true,
      rules: timeCondition?.rules?.map((r) => ({
        type: r.type,
        days: r.days ?? [],
        start_time: r.start_time ?? "",
        end_time: r.end_time ?? "",
        start_date: r.start_date ?? "",
        end_date: r.end_date ?? "",
        invert: r.invert ?? false,
        label: r.label ?? "",
      })) ?? [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: "rules" })

  const submitHandler = (values: FormValues) => {
    const data: TimeConditionCreate = {
      name: values.name,
      description: values.description || undefined,
      timezone: values.timezone,
      match_destination_type: values.match_destination_type,
      match_destination_id: values.match_destination_id || undefined,
      nomatch_destination_type: values.nomatch_destination_type,
      nomatch_destination_id: values.nomatch_destination_id || undefined,
      holiday_calendar_id: values.holiday_calendar_id || undefined,
      enabled: values.enabled,
      rules: values.rules.map((r) => ({
        type: r.type,
        days: r.type === "day_of_week" ? r.days : undefined,
        start_time: r.type === "time_of_day" ? (r.start_time || undefined) : undefined,
        end_time: r.type === "time_of_day" ? (r.end_time || undefined) : undefined,
        start_date: (r.type === "specific_date" || r.type === "date_range") ? (r.start_date || undefined) : undefined,
        end_date: r.type === "date_range" ? (r.end_date || undefined) : undefined,
        invert: r.invert,
        label: r.label || undefined,
      })),
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">{t('timeConditions.form.name')}</TabsTrigger>
          <TabsTrigger value="rules">{t('timeConditions.form.timeRanges')} ({fields.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="space-y-4 mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t('timeConditions.form.name')} *</Label>
              <Input id="name" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>{t('timeConditions.form.timezone')}</Label>
              <TimezoneSelect
                value={watch("timezone")}
                onChange={(v) => setValue("timezone", v)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('common.description')}</Label>
            <Textarea id="description" {...register("description")} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('timeConditions.form.matchDestType')} *</Label>
              <Select value={watch("match_destination_type")} onValueChange={(v) => { setValue("match_destination_type", v); setValue("match_destination_id", "") }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {DESTINATION_TYPES.map((dt) => (
                    <SelectItem key={dt.value} value={dt.value}>{dt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.match_destination_type && <p className="text-xs text-destructive">{errors.match_destination_type.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>{t('timeConditions.form.matchDest')}</Label>
              <DestinationPicker
                destinationType={watch("match_destination_type") || ""}
                value={watch("match_destination_id") ?? ""}
                onChange={(v) => setValue("match_destination_id", v)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('timeConditions.form.noMatchDestType')} *</Label>
              <Select value={watch("nomatch_destination_type")} onValueChange={(v) => { setValue("nomatch_destination_type", v); setValue("nomatch_destination_id", "") }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {DESTINATION_TYPES.map((dt) => (
                    <SelectItem key={dt.value} value={dt.value}>{dt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.nomatch_destination_type && <p className="text-xs text-destructive">{errors.nomatch_destination_type.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>{t('timeConditions.form.noMatchDest')}</Label>
              <DestinationPicker
                destinationType={watch("nomatch_destination_type") || ""}
                value={watch("nomatch_destination_id") ?? ""}
                onChange={(v) => setValue("nomatch_destination_id", v)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>{t('timeConditions.form.holidayCalendar')}</Label>
            <HolidayCalendarPicker
              value={watch("holiday_calendar_id") ?? ""}
              onChange={(v) => setValue("holiday_calendar_id", v)}
            />
          </div>

          <div className="flex items-center gap-2">
            <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
            <Label htmlFor="enabled">{t('timeConditions.form.enabled')}</Label>
          </div>
        </TabsContent>

        <TabsContent value="rules" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <Label>{t('timeConditions.form.timeRanges')}</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ type: "", days: [], start_time: "", end_time: "", start_date: "", end_date: "", invert: false, label: "" })}
            >
              <Plus className="mr-1 h-3 w-3" /> {t('timeConditions.form.addTimeRange')}
            </Button>
          </div>

          <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-3">
            {fields.length === 0 && (
              <p className="text-xs text-muted-foreground py-2 text-center">{t('timeConditions.form.noTimeRanges')}</p>
            )}
            {fields.map((field, index) => {
              const ruleType = watch(`rules.${index}.type`)
              return (
                <div key={field.id} className="rounded border p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Rule {index + 1}</span>
                    <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs">Rule Type *</Label>
                      <Select
                        value={ruleType}
                        onValueChange={(v) => setValue(`rules.${index}.type`, v)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          {RULE_TYPES.map((rt) => (
                            <SelectItem key={rt.value} value={rt.value}>{rt.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Label</Label>
                      <Input {...register(`rules.${index}.label`)} placeholder="Optional" />
                    </div>
                  </div>

                  {ruleType === "day_of_week" && (
                    <div className="space-y-1">
                      <Label className="text-xs">Days</Label>
                      <DayOfWeekPicker
                        value={watch(`rules.${index}.days`) ?? []}
                        onChange={(days) => setValue(`rules.${index}.days`, days)}
                      />
                    </div>
                  )}

                  {ruleType === "time_of_day" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <Label className="text-xs">Start Time</Label>
                        <Input type="time" {...register(`rules.${index}.start_time`)} />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">End Time</Label>
                        <Input type="time" {...register(`rules.${index}.end_time`)} />
                      </div>
                    </div>
                  )}

                  {ruleType === "specific_date" && (
                    <div className="space-y-1">
                      <Label className="text-xs">Date</Label>
                      <Input type="date" {...register(`rules.${index}.start_date`)} />
                    </div>
                  )}

                  {ruleType === "date_range" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <Label className="text-xs">Start Date</Label>
                        <Input type="date" {...register(`rules.${index}.start_date`)} />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">End Date</Label>
                        <Input type="date" {...register(`rules.${index}.end_date`)} />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <Switch
                      checked={watch(`rules.${index}.invert`)}
                      onCheckedChange={(v) => setValue(`rules.${index}.invert`, !!v)}
                    />
                    <Label className="text-xs">{t('common.enabled')}</Label>
                  </div>
                </div>
              )
            })}
          </div>
        </TabsContent>
      </Tabs>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : timeCondition ? t('timeConditions.form.updateButton') : t('timeConditions.form.createButton')}
      </Button>
    </form>
  )
}
