import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { useUsers } from "@/api/users"
import { useVoicemailBoxes } from "@/api/voicemail"
import { useDids } from "@/api/dids"
import type { Extension, ExtensionCreate } from "@/api/extensions"
import { useCreateVoicemailBox } from "@/api/voicemail"
import { SiteSelector } from "@/components/shared/site-selector"
import { AddressAutocomplete, type AddressFields } from "@/components/shared/address-autocomplete"

const extensionSchema = z.object({
  extension_number: z.string().min(1, "Required").max(20),
  user_id: z.string().optional().or(z.literal("")),
  voicemail_box_id: z.string().optional().or(z.literal("")),
  internal_cid_name: z.string().max(100).optional().or(z.literal("")),
  internal_cid_number: z.string().max(20).optional().or(z.literal("")),
  external_cid_name: z.string().max(100).optional().or(z.literal("")),
  external_cid_number: z.string().max(20).optional().or(z.literal("")),
  emergency_cid_number: z.string().max(20).optional().or(z.literal("")),
  call_forward_unconditional: z.string().max(50).optional().or(z.literal("")),
  call_forward_busy: z.string().max(50).optional().or(z.literal("")),
  call_forward_no_answer: z.string().max(50).optional().or(z.literal("")),
  call_forward_not_registered: z.string().max(50).optional().or(z.literal("")),
  call_forward_ring_time: z.coerce.number().min(5).max(120).default(25),
  e911_street: z.string().max(200).optional().or(z.literal("")),
  e911_city: z.string().max(100).optional().or(z.literal("")),
  e911_state: z.string().max(50).optional().or(z.literal("")),
  e911_zip: z.string().max(20).optional().or(z.literal("")),
  e911_country: z.string().max(50).optional().or(z.literal("")),
  dnd_enabled: z.boolean().default(false),
  call_waiting: z.boolean().default(true),
  max_registrations: z.coerce.number().min(1).max(10).default(3),
  outbound_cid_mode: z.string().default("external"),
  class_of_service: z.string().default("domestic"),
  recording_policy: z.string().default("never"),
  notes: z.string().optional().or(z.literal("")),
  pickup_group: z.string().max(20).optional().or(z.literal("")),
  site_id: z.string().optional().or(z.literal("")),
})

type FormValues = z.infer<typeof extensionSchema>

interface ExtensionFormProps {
  extension?: Extension | null
  onSubmit: (data: ExtensionCreate) => void
  isLoading: boolean
}

export function ExtensionForm({ extension, onSubmit, isLoading }: ExtensionFormProps) {
  const { t } = useTranslation()
  const { data: users } = useUsers()
  const { data: voicemailBoxes } = useVoicemailBoxes()
  const { data: dids } = useDids()
  const createVoicemailBox = useCreateVoicemailBox()

  const isCreating = !extension
  const defaultDid = dids?.find((d) => d.is_active && d.status === "active")

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(extensionSchema) as any,
    defaultValues: {
      extension_number: extension?.extension_number ?? "",
      user_id: extension?.user_id ?? "",
      voicemail_box_id: extension?.voicemail_box_id ?? "",
      internal_cid_name: extension?.internal_cid_name ?? "",
      internal_cid_number: extension?.internal_cid_number ?? "",
      external_cid_name: extension?.external_cid_name ?? "",
      external_cid_number: extension?.external_cid_number ?? "",
      emergency_cid_number: extension?.emergency_cid_number ?? "",
      call_forward_unconditional: extension?.call_forward_unconditional ?? "",
      call_forward_busy: extension?.call_forward_busy ?? "",
      call_forward_no_answer: extension?.call_forward_no_answer ?? "",
      call_forward_not_registered: extension?.call_forward_not_registered ?? "",
      call_forward_ring_time: extension?.call_forward_ring_time ?? 25,
      e911_street: extension?.e911_street ?? "",
      e911_city: extension?.e911_city ?? "",
      e911_state: extension?.e911_state ?? "",
      e911_zip: extension?.e911_zip ?? "",
      e911_country: extension?.e911_country ?? "",
      dnd_enabled: extension?.dnd_enabled ?? false,
      call_waiting: extension?.call_waiting ?? true,
      max_registrations: extension?.max_registrations ?? 3,
      outbound_cid_mode: extension?.outbound_cid_mode ?? "external",
      class_of_service: extension?.class_of_service ?? "domestic",
      recording_policy: extension?.recording_policy ?? "never",
      notes: extension?.notes ?? "",
      pickup_group: extension?.pickup_group ?? "",
      site_id: extension?.site_id ?? "",
    },
  })

  // When creating a new extension, auto-default CID fields
  const extensionNumber = watch("extension_number")
  const internalCidNumber = watch("internal_cid_number")
  const externalCidNumber = watch("external_cid_number")

  // Auto-fill internal CID number to match extension number when creating
  useEffect(() => {
    if (isCreating && extensionNumber && !internalCidNumber) {
      setValue("internal_cid_number", extensionNumber)
    }
  }, [isCreating, extensionNumber, internalCidNumber, setValue])

  // Auto-fill external CID to default DID when creating and DID data loads
  useEffect(() => {
    if (isCreating && defaultDid && !externalCidNumber) {
      setValue("external_cid_number", defaultDid.number)
    }
  }, [isCreating, defaultDid, externalCidNumber, setValue])

  const submitHandler = (values: FormValues) => {
    const data: ExtensionCreate = {
      ...values,
      user_id: values.user_id || null,
      voicemail_box_id: values.voicemail_box_id || null,
      internal_cid_name: values.internal_cid_name || undefined,
      internal_cid_number: values.internal_cid_number || undefined,
      external_cid_name: values.external_cid_name || undefined,
      external_cid_number: values.external_cid_number || undefined,
      emergency_cid_number: values.emergency_cid_number || undefined,
      call_forward_unconditional: values.call_forward_unconditional || undefined,
      call_forward_busy: values.call_forward_busy || undefined,
      call_forward_no_answer: values.call_forward_no_answer || undefined,
      call_forward_not_registered: values.call_forward_not_registered || undefined,
      e911_street: values.e911_street || undefined,
      e911_city: values.e911_city || undefined,
      e911_state: values.e911_state || undefined,
      e911_zip: values.e911_zip || undefined,
      e911_country: values.e911_country || undefined,
      notes: values.notes || undefined,
      pickup_group: values.pickup_group || undefined,
      site_id: values.site_id || null,
    }
    onSubmit(data)
  }

  const e911Address: AddressFields = {
    street: watch("e911_street") || "",
    city: watch("e911_city") || "",
    state: watch("e911_state") || "",
    zip: watch("e911_zip") || "",
    country: watch("e911_country") || "",
  }

  const handleE911AddressChange = (fields: AddressFields) => {
    setValue("e911_street", fields.street)
    setValue("e911_city", fields.city)
    setValue("e911_state", fields.state)
    setValue("e911_zip", fields.zip)
    setValue("e911_country", fields.country)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      {/* General */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="extension_number" required>{t('extensions.form.extensionNumber')}</Label>
          <Input id="extension_number" placeholder={t('extensions.form.extensionNumberPlaceholder')} {...register("extension_number")} />
          {errors.extension_number && <p className="text-xs text-destructive">{errors.extension_number.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="internal_cid_name">{t('extensions.form.displayName')}</Label>
          <Input id="internal_cid_name" placeholder={t('extensions.form.displayNamePlaceholder')} {...register("internal_cid_name")} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SiteSelector
          value={watch("site_id")}
          onChange={(v) => setValue("site_id", v ?? "")}
          label={t("sites.form.site")}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('extensions.form.assignedUser')}</Label>
          <Select value={watch("user_id") || "_none_"} onValueChange={(v) => setValue("user_id", v === "_none_" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder={t('extensions.form.noUserAssigned')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none_">{t('common.none')}</SelectItem>
              {users?.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.first_name} {u.last_name} ({u.email})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>{t('extensions.form.voicemailBox')}</Label>
          <Select
            value={watch("voicemail_box_id") || "_none_"}
            onValueChange={(v) => {
              if (v === "_create_new_") {
                const extNum = watch("extension_number")
                const mailboxNum = extNum || String(Date.now()).slice(-6)
                const pin = String(Math.floor(1000 + Math.random() * 9000))
                createVoicemailBox.mutate(
                  { mailbox_number: mailboxNum, pin },
                  {
                    onSuccess: (box) => {
                      setValue("voicemail_box_id", box.id)
                    },
                  }
                )
              } else {
                setValue("voicemail_box_id", v === "_none_" ? "" : v)
              }
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('extensions.form.noVoicemail')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none_">{t('common.none')}</SelectItem>
              <SelectItem value="_create_new_">{t('extensions.form.createVoicemailBox')}</SelectItem>
              {voicemailBoxes?.map((vm) => (
                <SelectItem key={vm.id} value={vm.id}>
                  Mailbox {vm.mailbox_number}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="internal_cid_number">{t('extensions.form.internalCid')}</Label>
          <Input id="internal_cid_number" placeholder={t('extensions.form.internalCidPlaceholder')} {...register("internal_cid_number")} />
          <p className="text-xs text-muted-foreground">{t('extensions.form.internalCidHelp')}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="external_cid_number">{t('extensions.form.externalCid')}</Label>
          <Select
            value={watch("external_cid_number") || "_none_"}
            onValueChange={(v) => setValue("external_cid_number", v === "_none_" ? "" : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('extensions.form.externalCidPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none_">{t('common.none')}</SelectItem>
              {dids?.filter((d) => d.is_active).map((d) => (
                <SelectItem key={d.id} value={d.number}>
                  {d.number}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">Outbound caller ID shown to called party</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>{t('extensions.form.outboundCidMode')}</Label>
          <Select value={watch("outbound_cid_mode")} onValueChange={(v) => setValue("outbound_cid_mode", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="internal">{t('extensions.form.internalCidMode')}</SelectItem>
              <SelectItem value="external">{t('extensions.form.externalCidMode')}</SelectItem>
              <SelectItem value="custom">{t('extensions.form.customCidMode')}</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('extensions.form.outboundCidModeHelp')}</p>
        </div>
        <div className="space-y-2">
          <Label>{t('extensions.form.classOfService')}</Label>
          <Select value={watch("class_of_service")} onValueChange={(v) => setValue("class_of_service", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="internal">{t('extensions.form.cosInternal')}</SelectItem>
              <SelectItem value="local">{t('extensions.form.cosLocal')}</SelectItem>
              <SelectItem value="domestic">{t('extensions.form.cosDomestic')}</SelectItem>
              <SelectItem value="international">{t('extensions.form.cosInternational')}</SelectItem>
              <SelectItem value="unrestricted">{t('extensions.form.cosUnrestricted')}</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('extensions.form.classOfServiceHelp')}</p>
        </div>
        <div className="space-y-2">
          <Label>{t('extensions.form.recordingPolicy')}</Label>
          <Select value={watch("recording_policy")} onValueChange={(v) => setValue("recording_policy", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="never">{t('extensions.form.recordNever')}</SelectItem>
              <SelectItem value="always">{t('extensions.form.recordAlways')}</SelectItem>
              <SelectItem value="on_demand">{t('extensions.form.recordOnDemand')}</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('extensions.form.recordingPolicyHelp')}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max_registrations">{t('extensions.form.maxRegistrations')}</Label>
          <Input id="max_registrations" type="number" min={1} max={10} {...register("max_registrations")} />
          <p className="text-xs text-muted-foreground">{t('extensions.form.maxRegistrationsHelp')}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="pickup_group">{t('extensions.form.pickupGroup')}</Label>
          <Input id="pickup_group" placeholder={t('extensions.form.pickupGroupPlaceholder')} {...register("pickup_group")} />
          <p className="text-xs text-muted-foreground">{t('extensions.form.pickupGroupHelp')}</p>
        </div>
      </div>

      <div className="flex gap-6">
        <div className="flex items-center gap-2">
          <Switch id="dnd" checked={watch("dnd_enabled")} onCheckedChange={(v) => setValue("dnd_enabled", v)} />
          <Label htmlFor="dnd">{t('extensions.form.dnd')}</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="cw" checked={watch("call_waiting")} onCheckedChange={(v) => setValue("call_waiting", v)} />
          <Label htmlFor="cw">{t('extensions.form.callWaiting')}</Label>
        </div>
      </div>

      {/* Call Forwarding */}
      <Separator />
      <h3 className="text-sm font-medium">{t('extensions.form.callForwarding')}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="call_forward_unconditional">{t('extensions.form.forwardAllCalls')}</Label>
          <Input id="call_forward_unconditional" placeholder={t('extensions.form.forwardAllCallsPlaceholder')} {...register("call_forward_unconditional")} />
          <p className="text-xs text-muted-foreground">{t('extensions.form.forwardAllCallsHelp')}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="call_forward_busy">{t('extensions.form.forwardWhenBusy')}</Label>
          <Input id="call_forward_busy" placeholder={t('extensions.form.forwardAllCallsPlaceholder')} {...register("call_forward_busy")} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="call_forward_no_answer">{t('extensions.form.forwardOnNoAnswer')}</Label>
          <Input id="call_forward_no_answer" placeholder={t('extensions.form.forwardAllCallsPlaceholder')} {...register("call_forward_no_answer")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="call_forward_not_registered">{t('extensions.form.forwardNotRegistered')}</Label>
          <Input id="call_forward_not_registered" placeholder={t('extensions.form.forwardAllCallsPlaceholder')} {...register("call_forward_not_registered")} />
        </div>
      </div>

      <div className="max-w-xs space-y-2">
        <Label htmlFor="call_forward_ring_time">{t('extensions.form.ringTimeBeforeForward')}</Label>
        <Input id="call_forward_ring_time" type="number" min={5} max={120} {...register("call_forward_ring_time")} />
        <p className="text-xs text-muted-foreground">{t('extensions.form.ringTimeHelp')}</p>
      </div>

      {/* E911 */}
      <Separator />
      <h3 className="text-sm font-medium">{t('extensions.form.e911')}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="emergency_cid_number">{t('extensions.form.emergencyCidOverride')}</Label>
          <Input id="emergency_cid_number" placeholder={t('extensions.form.externalCidPlaceholder')} type="tel" {...register("emergency_cid_number")} />
          <p className="text-xs text-muted-foreground">{t('extensions.form.emergencyCidHelp')}</p>
        </div>
      </div>

      <AddressAutocomplete value={e911Address} onChange={handleE911AddressChange} />

      {/* Notes */}
      <Separator />

      <div className="space-y-2">
        <Label htmlFor="notes">{t('common.notes')}</Label>
        <Textarea id="notes" {...register("notes")} />
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : extension ? t('extensions.form.updateButton') : t('extensions.form.createButton')}
      </Button>
    </form>
  )
}
