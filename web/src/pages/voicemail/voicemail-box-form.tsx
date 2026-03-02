import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { VoicemailBox } from "@/api/voicemail"

const GREETING_TYPES = [
  { value: "default", label: "Default" },
  { value: "busy", label: "Busy" },
  { value: "unavailable", label: "Unavailable" },
  { value: "name", label: "Name" },
  { value: "custom", label: "Custom" },
]

const createSchema = z.object({
  mailbox_number: z.string().min(1, "Required").max(20),
  pin: z.string().min(4, "Min 4 digits").max(20),
  greeting_type: z.string().default("default"),
  email_notification: z.boolean().default(true),
  notification_email: z.string().email("Invalid email").or(z.literal("")).default(""),
  max_messages: z.coerce.number().min(1).max(9999).default(100),
})

const updateSchema = createSchema.omit({ pin: true })

type CreateFormValues = z.infer<typeof createSchema>
type UpdateFormValues = z.infer<typeof updateSchema>

interface VoicemailBoxFormProps {
  box: VoicemailBox | null
  onSubmit: (data: any) => void
  isLoading: boolean
}

export function VoicemailBoxForm({ box, onSubmit, isLoading }: VoicemailBoxFormProps) {
  const { t } = useTranslation()
  const isEdit = !!box
  const schema = isEdit ? updateSchema : createSchema

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<CreateFormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      mailbox_number: box?.mailbox_number ?? "",
      pin: "",
      greeting_type: box?.greeting_type ?? "default",
      email_notification: box?.email_notification ?? true,
      notification_email: box?.notification_email ?? "",
      max_messages: box?.max_messages ?? 100,
    },
  })

  const submitHandler = (values: CreateFormValues | UpdateFormValues) => {
    const data: Record<string, unknown> = { ...values }
    if (data.notification_email === "") data.notification_email = null
    if (isEdit) delete data.pin
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="space-y-2">
        <Label>{t('voicemail.form.mailboxNumber')} *</Label>
        <Input {...register("mailbox_number")} placeholder={t('voicemail.form.mailboxNumberPlaceholder')} />
        {errors.mailbox_number && <p className="text-xs text-destructive">{errors.mailbox_number.message}</p>}
      </div>

      {!isEdit && (
        <div className="space-y-2">
          <Label>{t('voicemail.form.pin')} *</Label>
          <Input type="password" {...register("pin")} placeholder={t('voicemail.form.pinPlaceholder')} />
          {errors.pin && <p className="text-xs text-destructive">{errors.pin.message}</p>}
        </div>
      )}

      <div className="space-y-2">
        <Label>{t('voicemail.form.greetingPrompt', { defaultValue: 'Greeting Type' })}</Label>
        <Select value={watch("greeting_type")} onValueChange={(v) => setValue("greeting_type", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {GREETING_TYPES.map((gt) => (
              <SelectItem key={gt.value} value={gt.value}>{gt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="email_notification"
          checked={watch("email_notification")}
          onCheckedChange={(v) => setValue("email_notification", v)}
        />
        <Label htmlFor="email_notification">{t('voicemail.form.emailNotification', { defaultValue: 'Email Notification' })}</Label>
      </div>

      <div className="space-y-2">
        <Label>{t('voicemail.form.email')}</Label>
        <Input type="email" {...register("notification_email")} placeholder={t('voicemail.form.emailPlaceholder')} />
        {errors.notification_email && <p className="text-xs text-destructive">{errors.notification_email.message}</p>}
      </div>

      <div className="space-y-2">
        <Label>{t('voicemail.form.maxMessages')}</Label>
        <Input type="number" min={1} max={9999} className="w-32" {...register("max_messages")} />
        {errors.max_messages && <p className="text-xs text-destructive">{errors.max_messages.message}</p>}
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : isEdit ? t('voicemail.form.updateButton') : t('voicemail.form.createButton')}
      </Button>
    </form>
  )
}
