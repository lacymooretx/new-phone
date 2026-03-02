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
import { useExtensions } from "@/api/extensions"
import { useDispositionCodeLists } from "@/api/disposition-codes"
import { DestinationPicker, AudioPromptPicker } from "@/components/shared/destination-picker"
import { Plus, Trash2 } from "lucide-react"
import type { Queue, QueueCreate } from "@/api/queues"

const queueSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  queue_number: z.string().min(1, "Required").max(20),
  strategy: z.string().default("ring-all"),
  max_wait_time: z.coerce.number().min(0).max(3600).default(300),
  ring_timeout: z.coerce.number().min(1).max(300).default(15),
  wrapup_time: z.coerce.number().min(0).max(300).default(10),
  record_calls: z.boolean().default(false),
  enabled: z.boolean().default(true),
  disposition_required: z.boolean().default(false),
  disposition_code_list_id: z.string().optional().or(z.literal("")),
  overflow_destination_type: z.string().optional().or(z.literal("")),
  overflow_destination_id: z.string().optional().or(z.literal("")),
  moh_prompt_id: z.string().optional().or(z.literal("")),
  description: z.string().optional().or(z.literal("")),
  members: z.array(z.object({
    extension_id: z.string().min(1, "Required"),
    level: z.coerce.number().min(1).max(10).default(1),
    position: z.coerce.number().min(0).max(100).default(0),
  })).default([]),
})

type FormValues = z.infer<typeof queueSchema>

interface QueueFormProps {
  queue?: Queue | null
  onSubmit: (data: QueueCreate) => void
  isLoading: boolean
}

export function QueueForm({ queue, onSubmit, isLoading }: QueueFormProps) {
  const { t } = useTranslation()
  const { data: extensions } = useExtensions()
  const { data: codeLists } = useDispositionCodeLists()

  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(queueSchema) as any,
    defaultValues: {
      name: queue?.name ?? "",
      queue_number: queue?.queue_number ?? "",
      strategy: queue?.strategy ?? "ring-all",
      max_wait_time: queue?.max_wait_time ?? 300,
      ring_timeout: queue?.ring_timeout ?? 15,
      wrapup_time: queue?.wrapup_time ?? 10,
      record_calls: queue?.record_calls ?? false,
      enabled: queue?.enabled ?? true,
      disposition_required: queue?.disposition_required ?? false,
      disposition_code_list_id: queue?.disposition_code_list_id ?? "",
      overflow_destination_type: queue?.overflow_destination_type ?? "",
      overflow_destination_id: queue?.overflow_destination_id ?? "",
      moh_prompt_id: queue?.moh_prompt_id ?? "",
      description: queue?.description ?? "",
      members: queue?.members?.map((m) => ({
        extension_id: m.extension_id,
        level: m.level,
        position: m.position,
      })) ?? [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: "members" })

  const submitHandler = (values: FormValues) => {
    const data: QueueCreate = {
      ...values,
      description: values.description || undefined,
      overflow_destination_type: values.overflow_destination_type || null,
      overflow_destination_id: values.overflow_destination_id || null,
      moh_prompt_id: values.moh_prompt_id || null,
      disposition_code_list_id: values.disposition_code_list_id || null,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name" required>{t('queues.form.name')}</Label>
          <Input id="name" placeholder={t('queues.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="queue_number" required>{t('queues.form.queueNumber')}</Label>
          <Input id="queue_number" placeholder={t('queues.form.queueNumberPlaceholder')} {...register("queue_number")} />
          {errors.queue_number && <p className="text-xs text-destructive">{errors.queue_number.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label>{t('queues.form.strategy')}</Label>
        <Select value={watch("strategy")} onValueChange={(v) => setValue("strategy", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ring-all">{t('queues.form.ringAll')}</SelectItem>
            <SelectItem value="longest-idle-agent">{t('queues.form.longestIdleAgent')}</SelectItem>
            <SelectItem value="round-robin">{t('queues.form.roundRobin')}</SelectItem>
            <SelectItem value="top-down">{t('queues.form.topDown')}</SelectItem>
            <SelectItem value="agent-with-least-talk-time">{t('queues.form.leastTalkTime')}</SelectItem>
            <SelectItem value="agent-with-fewest-calls">{t('queues.form.fewestCalls')}</SelectItem>
            <SelectItem value="sequentially-by-agent-order">{t('queues.form.sequentialByOrder')}</SelectItem>
            <SelectItem value="random">{t('queues.form.random')}</SelectItem>
            <SelectItem value="ring-progressively">{t('queues.form.ringProgressively')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max_wait_time">{t('queues.form.maxWaitTime')}</Label>
          <Input id="max_wait_time" type="number" min={0} max={3600} {...register("max_wait_time")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ring_timeout">{t('queues.form.ringTimeout')}</Label>
          <Input id="ring_timeout" type="number" min={1} max={300} {...register("ring_timeout")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="wrapup_time">{t('queues.form.wrapupTime')}</Label>
          <Input id="wrapup_time" type="number" min={0} max={300} {...register("wrapup_time")} />
        </div>
      </div>

      <div className="flex gap-6 flex-wrap">
        <div className="flex items-center gap-2">
          <Switch id="record_calls" checked={watch("record_calls")} onCheckedChange={(v) => setValue("record_calls", v)} />
          <Label htmlFor="record_calls">{t('queues.form.recordCalls')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
          <Label htmlFor="enabled">{t('queues.form.enabled')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="disposition_required" checked={watch("disposition_required")} onCheckedChange={(v) => setValue("disposition_required", v)} />
          <Label htmlFor="disposition_required">{t('queues.form.requireDisposition')}</Label>
        </div>
      </div>

      {watch("disposition_required") && (
        <div className="space-y-2">
          <Label>{t('queues.form.dispositionCodeList')}</Label>
          <Select value={watch("disposition_code_list_id") || ""} onValueChange={(v) => setValue("disposition_code_list_id", v)}>
            <SelectTrigger>
              <SelectValue placeholder={t('queues.form.selectCodeList')} />
            </SelectTrigger>
            <SelectContent>
              {codeLists?.map((cl) => (
                <SelectItem key={cl.id} value={cl.id}>
                  {cl.name} ({cl.codes.length} codes)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('queues.form.overflowDestType')}</Label>
          <Select value={watch("overflow_destination_type") || ""} onValueChange={(v) => { setValue("overflow_destination_type", v); setValue("overflow_destination_id", "") }}>
            <SelectTrigger>
              <SelectValue placeholder="None" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="extension">Extension</SelectItem>
              <SelectItem value="ring_group">Ring Group</SelectItem>
              <SelectItem value="voicemail">Voicemail</SelectItem>
              <SelectItem value="ivr">IVR</SelectItem>
              <SelectItem value="queue">Queue</SelectItem>
              <SelectItem value="external">External</SelectItem>
              <SelectItem value="terminate">Terminate</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>{t('queues.form.overflowDest')}</Label>
          <DestinationPicker
            destinationType={watch("overflow_destination_type") || ""}
            value={watch("overflow_destination_id") ?? ""}
            onChange={(v) => setValue("overflow_destination_id", v)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>{t('queues.form.musicOnHold')}</Label>
        <AudioPromptPicker
          value={watch("moh_prompt_id") ?? ""}
          onChange={(v) => setValue("moh_prompt_id", v)}
          placeholder="Select hold music..."
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('queues.form.description')}</Label>
        <Textarea id="description" placeholder={t('queues.form.descriptionPlaceholder')} {...register("description")} />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{t('queues.form.queueMembers')}</Label>
          <Button type="button" variant="outline" size="sm" onClick={() => append({ extension_id: "", level: 1, position: fields.length })}>
            <Plus className="mr-1 h-3 w-3" /> {t('queues.form.addMember')}
          </Button>
        </div>
        <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-2">
          {fields.length === 0 && (
            <p className="text-xs text-muted-foreground py-2 text-center">{t('queues.form.noMembers')}</p>
          )}
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <div className="flex-1">
                <Select
                  value={watch(`members.${index}.extension_id`)}
                  onValueChange={(v) => setValue(`members.${index}.extension_id`, v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('queues.form.selectExtension')} />
                  </SelectTrigger>
                  <SelectContent>
                    {extensions?.map((ext) => (
                      <SelectItem key={ext.id} value={ext.id}>
                        {ext.extension_number} {ext.internal_cid_name ? `- ${ext.internal_cid_name}` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Input
                type="number"
                min={1}
                max={10}
                className="w-20"
                placeholder="Level"
                {...register(`members.${index}.level`)}
              />
              <Input
                type="number"
                min={0}
                max={100}
                className="w-20"
                placeholder="Pos"
                {...register(`members.${index}.position`)}
              />
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : queue ? t('queues.form.updateButton') : t('queues.form.createButton')}
      </Button>
    </form>
  )
}
