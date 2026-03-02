import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { SIPTrunk, SIPTrunkCreate } from "@/api/sip-trunks"

const sipTrunkSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  auth_type: z.string().min(1, "Required"),
  host: z.string().min(1, "Required"),
  port: z.coerce.number().min(1).max(65535).default(5061),
  username: z.string().optional().or(z.literal("")),
  password: z.string().optional().or(z.literal("")),
  ip_acl: z.string().optional().or(z.literal("")),
  max_channels: z.coerce.number().min(0).default(30),
  transport: z.string().default("tls"),
  inbound_cid_mode: z.string().default("passthrough"),
  notes: z.string().optional().or(z.literal("")),
})

type FormValues = z.infer<typeof sipTrunkSchema>

interface SipTrunkFormProps {
  sipTrunk?: SIPTrunk | null
  onSubmit: (data: SIPTrunkCreate) => void
  isLoading: boolean
}

export function SipTrunkForm({ sipTrunk, onSubmit, isLoading }: SipTrunkFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(sipTrunkSchema) as any,
    defaultValues: {
      name: sipTrunk?.name ?? "",
      auth_type: sipTrunk?.auth_type ?? "registration",
      host: sipTrunk?.host ?? "",
      port: sipTrunk?.port ?? 5061,
      username: sipTrunk?.username ?? "",
      password: "",
      ip_acl: sipTrunk?.ip_acl ?? "",
      max_channels: sipTrunk?.max_channels ?? 30,
      transport: sipTrunk?.transport ?? "tls",
      inbound_cid_mode: sipTrunk?.inbound_cid_mode ?? "passthrough",
      notes: sipTrunk?.notes ?? "",
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: SIPTrunkCreate = {
      ...values,
      username: values.username || undefined,
      password: values.password || undefined,
      ip_acl: values.ip_acl || undefined,
      notes: values.notes || undefined,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('sipTrunks.form.name')} *</Label>
          <Input id="name" placeholder={t('sipTrunks.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>{t('sipTrunks.form.authType', { defaultValue: 'Auth Type' })} *</Label>
          <Select value={watch("auth_type")} onValueChange={(v) => setValue("auth_type", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="registration">{t('sipTrunks.form.registration')}</SelectItem>
              <SelectItem value="ip_auth">{t('sipTrunks.form.ipAuth', { defaultValue: 'IP Auth' })}</SelectItem>
            </SelectContent>
          </Select>
          {errors.auth_type && <p className="text-xs text-destructive">{errors.auth_type.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="host">{t('sipTrunks.form.host')} *</Label>
          <Input id="host" placeholder={t('sipTrunks.form.hostPlaceholder')} {...register("host")} />
          {errors.host && <p className="text-xs text-destructive">{errors.host.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="port">{t('sipTrunks.form.port')}</Label>
          <Input id="port" type="number" min={1} max={65535} {...register("port")} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="username">{t('sipTrunks.form.username')}</Label>
          <Input id="username" placeholder={t('sipTrunks.form.usernamePlaceholder', { defaultValue: 'e.g., trunk_user' })} {...register("username")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">{t('sipTrunks.form.password')}</Label>
          <Input id="password" type="password" {...register("password")} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="ip_acl">{t('sipTrunks.form.ipAcl', { defaultValue: 'IP ACL' })}</Label>
        <Input id="ip_acl" placeholder={t('sipTrunks.form.ipAclPlaceholder', { defaultValue: 'e.g., 192.168.1.0/24' })} {...register("ip_acl")} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max_channels">{t('sipTrunks.form.maxChannels')}</Label>
          <Input id="max_channels" type="number" min={0} {...register("max_channels")} />
        </div>
        <div className="space-y-2">
          <Label>{t('sipTrunks.form.transport')}</Label>
          <Select value={watch("transport")} onValueChange={(v) => setValue("transport", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tls">TLS</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>{t('sipTrunks.form.inboundCidMode', { defaultValue: 'Inbound CID Mode' })}</Label>
          <Select value={watch("inbound_cid_mode")} onValueChange={(v) => setValue("inbound_cid_mode", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="passthrough">{t('sipTrunks.form.passthrough', { defaultValue: 'Passthrough' })}</SelectItem>
              <SelectItem value="rewrite">{t('sipTrunks.form.rewrite', { defaultValue: 'Rewrite' })}</SelectItem>
              <SelectItem value="block">{t('sipTrunks.form.block', { defaultValue: 'Block' })}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">{t('common.notes')}</Label>
        <Textarea id="notes" {...register("notes")} />
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : sipTrunk ? t('sipTrunks.form.updateButton') : t('sipTrunks.form.createButton')}
      </Button>
    </form>
  )
}
