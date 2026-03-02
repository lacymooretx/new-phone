import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useQueues } from "@/api/queues"
import type { DID, DIDCreate } from "@/api/dids"

const didSchema = z.object({
  number: z.string().min(1, "Required"),
  provider: z.string().min(1, "Required"),
  provider_sid: z.string().optional().or(z.literal("")),
  status: z.string().default("active"),
  is_emergency: z.boolean().default(false),
  sms_enabled: z.boolean().default(false),
  sms_queue_id: z.string().optional().or(z.literal("")),
})

type FormValues = z.infer<typeof didSchema>

interface DidFormProps {
  did?: DID | null
  onSubmit: (data: DIDCreate) => void
  isLoading: boolean
}

export function DidForm({ did, onSubmit, isLoading }: DidFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(didSchema) as any,
    defaultValues: {
      number: did?.number ?? "",
      provider: did?.provider ?? "clearlyip",
      provider_sid: did?.provider_sid ?? "",
      status: did?.status ?? "active",
      is_emergency: did?.is_emergency ?? false,
      sms_enabled: did?.sms_enabled ?? false,
      sms_queue_id: did?.sms_queue_id ?? "",
    },
  })

  const { data: queues } = useQueues()
  const smsEnabled = watch("sms_enabled")

  const submitHandler = (values: FormValues) => {
    const data: DIDCreate = {
      ...values,
      provider_sid: values.provider_sid || undefined,
      sms_queue_id: values.sms_queue_id || null,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="number">{t('dids.form.number')} *</Label>
          <Input id="number" placeholder={t('dids.form.numberPlaceholder')} {...register("number")} />
          {errors.number && <p className="text-xs text-destructive">{errors.number.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>{t('dids.form.provider', { defaultValue: 'Provider' })} *</Label>
          <Select value={watch("provider")} onValueChange={(v) => setValue("provider", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="clearlyip">ClearlyIP</SelectItem>
              <SelectItem value="twilio">Twilio</SelectItem>
              <SelectItem value="manual">{t('dids.form.manual', { defaultValue: 'Manual' })}</SelectItem>
            </SelectContent>
          </Select>
          {errors.provider && <p className="text-xs text-destructive">{errors.provider.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="provider_sid">{t('dids.form.providerSid', { defaultValue: 'Provider SID' })}</Label>
          <Input id="provider_sid" placeholder="e.g., PNXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" {...register("provider_sid")} />
        </div>
        <div className="space-y-2">
          <Label>{t('common.status')}</Label>
          <Select value={watch("status")} onValueChange={(v) => setValue("status", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">{t('common.active')}</SelectItem>
              <SelectItem value="porting">{t('dids.form.porting', { defaultValue: 'Porting' })}</SelectItem>
              <SelectItem value="reserved">{t('dids.form.reserved', { defaultValue: 'Reserved' })}</SelectItem>
              <SelectItem value="released">{t('dids.form.released', { defaultValue: 'Released' })}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch id="is_emergency" checked={watch("is_emergency")} onCheckedChange={(v) => setValue("is_emergency", v)} />
        <Label htmlFor="is_emergency">{t('dids.form.e911Enabled', { defaultValue: 'Emergency (E911)' })}</Label>
      </div>

      <div className="flex items-center gap-2">
        <Switch id="sms_enabled" checked={smsEnabled} onCheckedChange={(v) => setValue("sms_enabled", v)} />
        <Label htmlFor="sms_enabled">{t('dids.form.smsEnabled')}</Label>
      </div>

      {smsEnabled && (
        <div className="space-y-2 pl-6">
          <Label>{t('dids.form.smsQueue', { defaultValue: 'SMS Queue' })}</Label>
          <Select
            value={watch("sms_queue_id") || "none"}
            onValueChange={(v) => setValue("sms_queue_id", v === "none" ? "" : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('dids.form.noQueue', { defaultValue: 'No queue (personal DID)' })} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t('dids.form.noQueue', { defaultValue: 'No queue (personal DID)' })}</SelectItem>
              {queues?.map((q) => (
                <SelectItem key={q.id} value={q.id}>
                  {q.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('dids.form.smsQueueHelp', { defaultValue: 'Inbound SMS to this DID will be routed to the selected queue for shared inbox handling.' })}
          </p>
        </div>
      )}

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : did ? t('dids.form.updateButton') : t('dids.form.createButton')}
      </Button>
    </form>
  )
}
