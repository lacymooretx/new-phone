import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import type { ConferenceBridge, ConferenceBridgeCreate } from "@/api/conferences"

const conferenceSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  room_number: z.string().min(1, "Required").max(20),
  description: z.string().optional().or(z.literal("")),
  max_participants: z.coerce.number().min(1).max(500).default(50),
  participant_pin: z.string().max(20).optional().or(z.literal("")),
  moderator_pin: z.string().max(20).optional().or(z.literal("")),
  wait_for_moderator: z.boolean().default(false),
  announce_join_leave: z.boolean().default(true),
  record_conference: z.boolean().default(false),
  muted_on_join: z.boolean().default(false),
  enabled: z.boolean().default(true),
})

type FormValues = z.infer<typeof conferenceSchema>

interface ConferenceFormProps {
  conference?: ConferenceBridge | null
  onSubmit: (data: ConferenceBridgeCreate) => void
  isLoading: boolean
}

export function ConferenceForm({ conference, onSubmit, isLoading }: ConferenceFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(conferenceSchema) as any,
    defaultValues: {
      name: conference?.name ?? "",
      room_number: conference?.room_number ?? "",
      description: conference?.description ?? "",
      max_participants: conference?.max_participants ?? 50,
      participant_pin: conference?.participant_pin ?? "",
      moderator_pin: conference?.moderator_pin ?? "",
      wait_for_moderator: conference?.wait_for_moderator ?? false,
      announce_join_leave: conference?.announce_join_leave ?? true,
      record_conference: conference?.record_conference ?? false,
      muted_on_join: conference?.muted_on_join ?? false,
      enabled: conference?.enabled ?? true,
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: ConferenceBridgeCreate = {
      ...values,
      description: values.description || undefined,
      participant_pin: values.participant_pin || undefined,
      moderator_pin: values.moderator_pin || undefined,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('conferences.form.name')} *</Label>
          <Input id="name" placeholder={t('conferences.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="room_number">{t('conferences.form.roomNumber')} *</Label>
          <Input id="room_number" placeholder={t('conferences.form.roomNumberPlaceholder')} {...register("room_number")} />
          {errors.room_number && <p className="text-xs text-destructive">{errors.room_number.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('common.description')}</Label>
        <Textarea id="description" placeholder={t('common.optional')} {...register("description")} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max_participants">{t('conferences.form.maxMembers')}</Label>
          <Input id="max_participants" type="number" min={1} max={500} {...register("max_participants")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="participant_pin">{t('conferences.form.pin')}</Label>
          <Input id="participant_pin" placeholder={t('conferences.form.pinPlaceholder')} {...register("participant_pin")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="moderator_pin">{t('conferences.form.adminPin')}</Label>
          <Input id="moderator_pin" placeholder={t('conferences.form.adminPinPlaceholder')} {...register("moderator_pin")} />
        </div>
      </div>

      <div className="flex flex-wrap gap-6">
        <div className="flex items-center gap-2">
          <Switch id="wait_for_moderator" checked={watch("wait_for_moderator")} onCheckedChange={(v) => setValue("wait_for_moderator", v)} />
          <Label htmlFor="wait_for_moderator">{t('conferences.form.waitForAdmin')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="announce_join_leave" checked={watch("announce_join_leave")} onCheckedChange={(v) => setValue("announce_join_leave", v)} />
          <Label htmlFor="announce_join_leave">{t('conferences.form.announceJoinLeave')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="record_conference" checked={watch("record_conference")} onCheckedChange={(v) => setValue("record_conference", v)} />
          <Label htmlFor="record_conference">{t('conferences.form.recordConference')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="muted_on_join" checked={watch("muted_on_join")} onCheckedChange={(v) => setValue("muted_on_join", v)} />
          <Label htmlFor="muted_on_join">{t('conferences.form.muteOnJoin')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
          <Label htmlFor="enabled">{t('common.enabled')}</Label>
        </div>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : conference ? t('conferences.form.updateButton') : t('conferences.form.createButton')}
      </Button>
    </form>
  )
}
