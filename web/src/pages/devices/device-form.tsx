import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import type { Device, DeviceCreate } from "@/api/devices"
import { usePhoneModels } from "@/api/phone-models"
import { useExtensions } from "@/api/extensions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const deviceSchema = z.object({
  mac_address: z.string().min(12, "MAC address is required").max(17),
  phone_model_id: z.string().min(1, "Phone model is required"),
  extension_id: z.string().optional().or(z.literal("")),
  name: z.string().max(100).optional().or(z.literal("")),
  location: z.string().max(200).optional().or(z.literal("")),
  notes: z.string().optional().or(z.literal("")),
  provisioning_enabled: z.boolean(),
})

type FormValues = z.infer<typeof deviceSchema>

interface DeviceFormProps {
  device?: Device | null
  onSubmit: (data: DeviceCreate) => void
  isLoading: boolean
}

export function DeviceForm({ device, onSubmit, isLoading }: DeviceFormProps) {
  const { t } = useTranslation()
  const { data: phoneModels } = usePhoneModels()
  const { data: extensions } = useExtensions()

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(deviceSchema) as any,
    defaultValues: {
      mac_address: device?.mac_address ?? "",
      phone_model_id: device?.phone_model_id ?? "",
      extension_id: device?.extension_id ?? "",
      name: device?.name ?? "",
      location: device?.location ?? "",
      notes: device?.notes ?? "",
      provisioning_enabled: device?.provisioning_enabled ?? true,
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: DeviceCreate = {
      mac_address: values.mac_address,
      phone_model_id: values.phone_model_id,
      extension_id: values.extension_id || null,
      name: values.name || null,
      location: values.location || null,
      notes: values.notes || null,
      provisioning_enabled: values.provisioning_enabled,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="mac_address">{t('devices.form.macAddress')} *</Label>
          <Input id="mac_address" placeholder={t('devices.form.macAddressPlaceholder')} className="font-mono" {...register("mac_address")} />
          {errors.mac_address && <p className="text-xs text-destructive">{errors.mac_address.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone_model_id">{t('devices.form.model')} *</Label>
          <Select value={watch("phone_model_id") || "_none_"} onValueChange={(v) => setValue("phone_model_id", v === "_none_" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder={t('devices.form.selectModel')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none_">{t('devices.form.selectModel')}...</SelectItem>
              {(() => {
                const grouped = (phoneModels ?? []).reduce<Record<string, typeof phoneModels>>((acc, m) => {
                  const key = m.manufacturer
                  if (!acc[key]) acc[key] = []
                  acc[key]!.push(m)
                  return acc
                }, {})
                return Object.entries(grouped).map(([manufacturer, models]) => (
                  <div key={manufacturer}>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">{manufacturer}</div>
                    {models!.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.model_name}
                      </SelectItem>
                    ))}
                  </div>
                ))
              })()}
            </SelectContent>
          </Select>
          {errors.phone_model_id && <p className="text-xs text-destructive">{errors.phone_model_id.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="extension_id">{t('devices.form.extension')}</Label>
          <Select value={watch("extension_id") || "_none_"} onValueChange={(v) => setValue("extension_id", v === "_none_" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder={t('devices.form.selectExtension')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none_">{t('common.none')}</SelectItem>
              {extensions?.map((e) => (
                <SelectItem key={e.id} value={e.id}>
                  {e.extension_number} — {e.internal_cid_name || "No name"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="name">{t('devices.form.name')}</Label>
          <Input id="name" placeholder={t('devices.form.namePlaceholder')} {...register("name")} />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="location">Location</Label>
          <Input id="location" placeholder="e.g., Main Office, Room 101" {...register("location")} />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="notes">{t('common.notes')}</Label>
          <Textarea id="notes" placeholder={t('common.optional')} rows={2} {...register("notes")} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="provisioning_enabled"
          checked={watch("provisioning_enabled")}
          onCheckedChange={(v) => setValue("provisioning_enabled", v)}
        />
        <Label htmlFor="provisioning_enabled">{t('common.enabled')}</Label>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : device ? t('devices.form.updateButton') : t('devices.form.createButton')}
      </Button>
    </form>
  )
}
