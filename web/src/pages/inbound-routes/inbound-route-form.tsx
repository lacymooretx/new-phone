import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DestinationPicker } from "@/components/shared/destination-picker"
import type { InboundRoute, InboundRouteCreate } from "@/api/inbound-routes"

const inboundRouteSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  destination_type: z.string().min(1, "Required"),
  destination_id: z.string().optional().or(z.literal("")),
  cid_name_prefix: z.string().optional().or(z.literal("")),
  enabled: z.boolean().default(true),
})

type FormValues = z.infer<typeof inboundRouteSchema>

interface InboundRouteFormProps {
  inboundRoute?: InboundRoute | null
  onSubmit: (data: InboundRouteCreate) => void
  isLoading: boolean
}

export function InboundRouteForm({ inboundRoute, onSubmit, isLoading }: InboundRouteFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(inboundRouteSchema) as any,
    defaultValues: {
      name: inboundRoute?.name ?? "",
      destination_type: inboundRoute?.destination_type ?? "extension",
      destination_id: inboundRoute?.destination_id ?? "",
      cid_name_prefix: inboundRoute?.cid_name_prefix ?? "",
      enabled: inboundRoute?.enabled ?? true,
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: InboundRouteCreate = {
      ...values,
      destination_id: values.destination_id || undefined,
      cid_name_prefix: values.cid_name_prefix || undefined,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('inboundRoutes.form.name')} *</Label>
          <Input id="name" placeholder={t('inboundRoutes.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>{t('inboundRoutes.form.destinationType')} *</Label>
          <Select value={watch("destination_type")} onValueChange={(v) => { setValue("destination_type", v); setValue("destination_id", "") }}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="extension">{t('destination.extension')}</SelectItem>
              <SelectItem value="ring_group">{t('destination.ringGroup')}</SelectItem>
              <SelectItem value="voicemail">{t('destination.voicemail')}</SelectItem>
              <SelectItem value="ivr">{t('destination.ivr')}</SelectItem>
              <SelectItem value="time_condition">{t('destination.timeCondition')}</SelectItem>
              <SelectItem value="queue">{t('destination.queue')}</SelectItem>
              <SelectItem value="conference">{t('destination.conference')}</SelectItem>
              <SelectItem value="external">{t('destination.externalShort')}</SelectItem>
              <SelectItem value="terminate">{t('destination.terminate')}</SelectItem>
            </SelectContent>
          </Select>
          {errors.destination_type && <p className="text-xs text-destructive">{errors.destination_type.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('inboundRoutes.form.destination')}</Label>
          <DestinationPicker
            destinationType={watch("destination_type") || ""}
            value={watch("destination_id") ?? ""}
            onChange={(v) => setValue("destination_id", v)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cid_name_prefix">{t('inboundRoutes.form.cidNamePrefix', { defaultValue: 'CID Name Prefix' })}</Label>
          <Input id="cid_name_prefix" placeholder={t('inboundRoutes.form.cidNamePrefixPlaceholder', { defaultValue: 'e.g., Sales:' })} {...register("cid_name_prefix")} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
        <Label htmlFor="enabled">{t('common.enabled')}</Label>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : inboundRoute ? t('inboundRoutes.form.updateButton') : t('inboundRoutes.form.createButton')}
      </Button>
    </form>
  )
}
