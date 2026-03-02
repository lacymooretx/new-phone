import { useForm, useFieldArray } from "react-hook-form"
import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, Trash2 } from "lucide-react"
import type { FollowMe, FollowMeUpdate } from "@/api/follow-me"

const followMeSchema = z.object({
  enabled: z.boolean().default(false),
  strategy: z.string().default("ringall"),
  ring_extension_first: z.boolean().default(true),
  extension_ring_time: z.coerce.number().min(5).max(120).default(20),
  destinations: z.array(z.object({
    destination: z.string().min(1, "Required"),
    ring_time: z.coerce.number().min(1).max(300).default(25),
  })).default([]),
})

type FormValues = z.infer<typeof followMeSchema>

const STRATEGY_OPTIONS = [
  { value: "ringall", label: "Ring All" },
  { value: "enterprise", label: "Enterprise" },
  { value: "sequence", label: "Sequence" },
  { value: "simultaneous", label: "Simultaneous" },
]

interface FollowMeFormProps {
  initialData: FollowMe | null | undefined
  onSubmit: (data: FollowMeUpdate) => void
  isLoading: boolean
}

export function FollowMeForm({ initialData, onSubmit, isLoading }: FollowMeFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, control, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(followMeSchema) as any,
    defaultValues: {
      enabled: false,
      strategy: "ringall",
      ring_extension_first: true,
      extension_ring_time: 20,
      destinations: [],
    },
  })

  useEffect(() => {
    if (initialData) {
      reset({
        enabled: initialData.enabled,
        strategy: initialData.strategy || "ringall",
        ring_extension_first: initialData.ring_extension_first,
        extension_ring_time: initialData.extension_ring_time ?? 20,
        destinations: initialData.destinations?.map((d) => ({
          destination: d.destination,
          ring_time: d.ring_time,
        })) ?? [],
      })
    }
  }, [initialData, reset])

  const { fields, append, remove } = useFieldArray({ control, name: "destinations" })

  const submitHandler = (values: FormValues) => {
    onSubmit({
      enabled: values.enabled,
      strategy: values.strategy,
      ring_extension_first: values.ring_extension_first,
      extension_ring_time: values.extension_ring_time,
      destinations: values.destinations,
    })
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-6">
      <div className="flex items-center gap-2">
        <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
        <Label htmlFor="enabled">{t('extensions.followMe.enable')}</Label>
      </div>

      <div className="space-y-2">
        <Label htmlFor="strategy">{t('extensions.followMe.ringStrategy')}</Label>
        <Select value={watch("strategy")} onValueChange={(v) => setValue("strategy", v)}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STRATEGY_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="ring_extension_first"
          checked={watch("ring_extension_first")}
          onCheckedChange={(v) => setValue("ring_extension_first", v)}
        />
        <Label htmlFor="ring_extension_first">{t('extensions.followMe.ringStrategy')}</Label>
        <p className="text-xs text-muted-foreground">{t('extensions.followMe.initialRingTime')} </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="extension_ring_time">{t('extensions.followMe.initialRingTime')}</Label>
        <p className="text-xs text-muted-foreground">{t('extensions.followMe.timeoutLabel')}</p>
        <Input id="extension_ring_time" type="number" min={5} max={120} className="w-32" {...register("extension_ring_time")} />
        {errors.extension_ring_time && (
          <p className="text-xs text-destructive">{errors.extension_ring_time.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{t('extensions.followMe.title')}</Label>
          <Button type="button" variant="outline" size="sm" onClick={() => append({ destination: "", ring_time: 25 })}>
            <Plus className="mr-1 h-3 w-3" /> {t('extensions.followMe.addNumber')}
          </Button>
        </div>
        <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-2">
          {fields.length === 0 && (
            <p className="text-xs text-muted-foreground py-2 text-center">{t('extensions.followMe.noNumbersConfigured')}</p>
          )}
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <div className="flex-1 space-y-1">
                <Input
                  {...register(`destinations.${index}.destination`)}
                  placeholder="Extension number or external number"
                />
                {errors.destinations?.[index]?.destination && (
                  <p className="text-xs text-destructive">{errors.destinations[index].destination?.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Input
                  type="number"
                  min={1}
                  max={300}
                  className="w-24"
                  placeholder="Ring time"
                  {...register(`destinations.${index}.ring_time`)}
                />
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
        {fields.length > 0 && (
          <p className="text-xs text-muted-foreground">Destinations are rung in order. Enter extension numbers or external phone numbers.</p>
        )}
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : t('extensions.followMe.save')}
      </Button>
    </form>
  )
}
