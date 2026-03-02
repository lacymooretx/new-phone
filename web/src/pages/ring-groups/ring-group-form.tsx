import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ExtensionPicker } from "@/components/shared/extension-picker"
import { DestinationPicker, AudioPromptPicker } from "@/components/shared/destination-picker"
import type { RingGroup, RingGroupCreate } from "@/api/ring-groups"

const ringGroupSchema = z.object({
  group_number: z.string().min(1, "Required").max(20),
  name: z.string().min(1, "Required").max(100),
  ring_strategy: z.string().default("simultaneous"),
  ring_time: z.coerce.number().min(1).max(300).default(25),
  ring_time_per_member: z.coerce.number().min(1).max(300).default(15),
  skip_busy: z.boolean().default(false),
  cid_passthrough: z.boolean().default(true),
  confirm_calls: z.boolean().default(false),
  failover_dest_type: z.string().optional().or(z.literal("")),
  failover_dest_id: z.string().optional().or(z.literal("")),
  moh_prompt_id: z.string().optional().or(z.literal("")),
  member_extension_ids: z.array(z.string()).default([]),
})

type FormValues = z.infer<typeof ringGroupSchema>

interface RingGroupFormProps {
  ringGroup?: RingGroup | null
  onSubmit: (data: RingGroupCreate) => void
  isLoading: boolean
}

export function RingGroupForm({ ringGroup, onSubmit, isLoading }: RingGroupFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(ringGroupSchema) as any,
    defaultValues: {
      group_number: ringGroup?.group_number ?? "",
      name: ringGroup?.name ?? "",
      ring_strategy: ringGroup?.ring_strategy ?? "simultaneous",
      ring_time: ringGroup?.ring_time ?? 25,
      ring_time_per_member: ringGroup?.ring_time_per_member ?? 15,
      skip_busy: ringGroup?.skip_busy ?? false,
      cid_passthrough: ringGroup?.cid_passthrough ?? true,
      confirm_calls: ringGroup?.confirm_calls ?? false,
      failover_dest_type: ringGroup?.failover_dest_type ?? "",
      failover_dest_id: ringGroup?.failover_dest_id ?? "",
      moh_prompt_id: ringGroup?.moh_prompt_id ?? "",
      member_extension_ids: ringGroup?.member_extension_ids ?? [],
    },
  })

  const memberIds = watch("member_extension_ids")

  const submitHandler = (values: FormValues) => {
    onSubmit({
      ...values,
      failover_dest_type: values.failover_dest_type || null,
      failover_dest_id: values.failover_dest_id || null,
      moh_prompt_id: values.moh_prompt_id || null,
    })
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="group_number">{t('ringGroups.form.groupNumber')} *</Label>
          <Input id="group_number" placeholder={t('ringGroups.form.groupNumberPlaceholder')} {...register("group_number")} />
          {errors.group_number && <p className="text-xs text-destructive">{errors.group_number.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="name">{t('ringGroups.form.name')} *</Label>
          <Input id="name" placeholder={t('ringGroups.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label>{t('ringGroups.form.ringStrategy')}</Label>
        <Select value={watch("ring_strategy")} onValueChange={(v) => setValue("ring_strategy", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="simultaneous">{t('ringGroups.form.simultaneous')}</SelectItem>
            <SelectItem value="sequential">{t('ringGroups.form.sequential')}</SelectItem>
            <SelectItem value="random">{t('ringGroups.form.random')}</SelectItem>
            <SelectItem value="round_robin">{t('ringGroups.form.roundRobin')}</SelectItem>
            <SelectItem value="memory_hunt">{t('ringGroups.form.memoryHunt')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="ring_time">{t('ringGroups.form.ringTime')}</Label>
          <Input id="ring_time" type="number" min={1} max={300} placeholder="25" {...register("ring_time")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ring_time_per_member">{t('ringGroups.form.ringTimePerMember')}</Label>
          <Input id="ring_time_per_member" type="number" min={1} max={300} placeholder="15" {...register("ring_time_per_member")} />
        </div>
      </div>

      <div className="flex gap-6">
        <div className="flex items-center gap-2">
          <Switch id="skip_busy" checked={watch("skip_busy")} onCheckedChange={(v) => setValue("skip_busy", v)} />
          <Label htmlFor="skip_busy">{t('ringGroups.form.skipBusy')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="cid_passthrough" checked={watch("cid_passthrough")} onCheckedChange={(v) => setValue("cid_passthrough", v)} />
          <Label htmlFor="cid_passthrough">{t('ringGroups.form.cidPassthrough')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="confirm_calls" checked={watch("confirm_calls")} onCheckedChange={(v) => setValue("confirm_calls", v)} />
          <Label htmlFor="confirm_calls">{t('ringGroups.form.confirmCalls')}</Label>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('ringGroups.form.failoverDestType')}</Label>
          <Select value={watch("failover_dest_type") || ""} onValueChange={(v) => { setValue("failover_dest_type", v); setValue("failover_dest_id", "") }}>
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
          <Label>{t('ringGroups.form.failoverDest')}</Label>
          <DestinationPicker
            destinationType={watch("failover_dest_type") || ""}
            value={watch("failover_dest_id") ?? ""}
            onChange={(v) => setValue("failover_dest_id", v)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>{t('ringGroups.form.musicOnHold')}</Label>
        <AudioPromptPicker
          value={watch("moh_prompt_id") ?? ""}
          onChange={(v) => setValue("moh_prompt_id", v)}
          placeholder="Select hold music..."
        />
      </div>

      <ExtensionPicker
        value={memberIds}
        onChange={(ids) => setValue("member_extension_ids", ids)}
      />

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : ringGroup ? t('ringGroups.form.updateButton') : t('ringGroups.form.createButton')}
      </Button>
    </form>
  )
}
