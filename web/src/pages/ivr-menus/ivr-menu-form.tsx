import { useForm, useFieldArray } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, Trash2 } from "lucide-react"
import { DestinationPicker, AudioPromptPicker } from "@/components/shared/destination-picker"
import type { IVRMenu, IVRMenuCreate } from "@/api/ivr-menus"

const ACTION_TYPES = [
  { value: "extension", label: "Extension" },
  { value: "ring_group", label: "Ring Group" },
  { value: "voicemail", label: "Voicemail" },
  { value: "ivr", label: "IVR Sub-Menu" },
  { value: "queue", label: "Queue" },
  { value: "conference", label: "Conference" },
  { value: "external", label: "External Number" },
  { value: "hangup", label: "Hang Up" },
  { value: "repeat", label: "Repeat Greeting" },
]

const ivrMenuSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  description: z.string().optional().or(z.literal("")),
  greet_long_prompt_id: z.string().optional().or(z.literal("")),
  greet_short_prompt_id: z.string().optional().or(z.literal("")),
  invalid_sound_prompt_id: z.string().optional().or(z.literal("")),
  exit_sound_prompt_id: z.string().optional().or(z.literal("")),
  timeout: z.coerce.number().min(1).max(300).default(10),
  max_failures: z.coerce.number().min(1).max(10).default(3),
  max_timeouts: z.coerce.number().min(1).max(10).default(3),
  inter_digit_timeout: z.coerce.number().min(1).max(30).default(2),
  digit_len: z.coerce.number().min(1).max(10).default(1),
  exit_destination_type: z.string().optional().or(z.literal("")),
  exit_destination_id: z.string().optional().or(z.literal("")),
  enabled: z.boolean().default(true),
  options: z.array(z.object({
    digits: z.string().min(1, "Required").max(10),
    action_type: z.string().min(1, "Required"),
    action_target_id: z.string().optional().or(z.literal("")),
    action_target_value: z.string().optional().or(z.literal("")),
    label: z.string().optional().or(z.literal("")),
    position: z.coerce.number().min(0).default(0),
  })).default([]),
})

type FormValues = z.infer<typeof ivrMenuSchema>

interface IvrMenuFormProps {
  ivrMenu?: IVRMenu | null
  onSubmit: (data: IVRMenuCreate) => void
  isLoading: boolean
}

export function IvrMenuForm({ ivrMenu, onSubmit, isLoading }: IvrMenuFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(ivrMenuSchema) as any,
    defaultValues: {
      name: ivrMenu?.name ?? "",
      description: ivrMenu?.description ?? "",
      greet_long_prompt_id: ivrMenu?.greet_long_prompt_id ?? "",
      greet_short_prompt_id: ivrMenu?.greet_short_prompt_id ?? "",
      invalid_sound_prompt_id: ivrMenu?.invalid_sound_prompt_id ?? "",
      exit_sound_prompt_id: ivrMenu?.exit_sound_prompt_id ?? "",
      timeout: ivrMenu?.timeout ?? 10,
      max_failures: ivrMenu?.max_failures ?? 3,
      max_timeouts: ivrMenu?.max_timeouts ?? 3,
      inter_digit_timeout: ivrMenu?.inter_digit_timeout ?? 2,
      digit_len: ivrMenu?.digit_len ?? 1,
      exit_destination_type: ivrMenu?.exit_destination_type ?? "",
      exit_destination_id: ivrMenu?.exit_destination_id ?? "",
      enabled: ivrMenu?.enabled ?? true,
      options: ivrMenu?.options?.map((o) => ({
        digits: o.digits,
        action_type: o.action_type,
        action_target_id: o.action_target_id ?? "",
        action_target_value: o.action_target_value ?? "",
        label: o.label ?? "",
        position: o.position,
      })) ?? [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: "options" })

  const submitHandler = (values: FormValues) => {
    const data: IVRMenuCreate = {
      name: values.name,
      description: values.description || undefined,
      greet_long_prompt_id: values.greet_long_prompt_id || undefined,
      greet_short_prompt_id: values.greet_short_prompt_id || undefined,
      invalid_sound_prompt_id: values.invalid_sound_prompt_id || undefined,
      exit_sound_prompt_id: values.exit_sound_prompt_id || undefined,
      timeout: values.timeout,
      max_failures: values.max_failures,
      max_timeouts: values.max_timeouts,
      inter_digit_timeout: values.inter_digit_timeout,
      digit_len: values.digit_len,
      exit_destination_type: values.exit_destination_type || undefined,
      exit_destination_id: values.exit_destination_id || undefined,
      enabled: values.enabled,
      options: values.options.map((o, i) => ({
        digits: o.digits,
        action_type: o.action_type,
        action_target_id: o.action_target_id || undefined,
        action_target_value: o.action_target_value || undefined,
        label: o.label || undefined,
        position: i,
      })),
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">{t('ivrMenus.form.settingsTab')}</TabsTrigger>
          <TabsTrigger value="options">{t('ivrMenus.form.optionsTab')} ({fields.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="name">{t('ivrMenus.form.name')} *</Label>
            <Input id="name" placeholder={t('ivrMenus.form.namePlaceholder')} {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('ivrMenus.form.description')}</Label>
            <Textarea id="description" placeholder={t('ivrMenus.form.descriptionPlaceholder')} {...register("description")} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.greetLongPrompt')}</Label>
              <AudioPromptPicker
                value={watch("greet_long_prompt_id") ?? ""}
                onChange={(v) => setValue("greet_long_prompt_id", v)}
                placeholder={t('ivrMenus.form.greetLongPlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.greetShortPrompt')}</Label>
              <AudioPromptPicker
                value={watch("greet_short_prompt_id") ?? ""}
                onChange={(v) => setValue("greet_short_prompt_id", v)}
                placeholder={t('ivrMenus.form.greetShortPlaceholder')}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.invalidSoundPrompt')}</Label>
              <AudioPromptPicker
                value={watch("invalid_sound_prompt_id") ?? ""}
                onChange={(v) => setValue("invalid_sound_prompt_id", v)}
                placeholder={t('ivrMenus.form.invalidSoundPlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.exitSoundPrompt')}</Label>
              <AudioPromptPicker
                value={watch("exit_sound_prompt_id") ?? ""}
                onChange={(v) => setValue("exit_sound_prompt_id", v)}
                placeholder={t('ivrMenus.form.exitSoundPlaceholder')}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timeout">{t('ivrMenus.form.timeout')}</Label>
              <Input id="timeout" type="number" min={1} max={300} placeholder="10" {...register("timeout")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_failures">{t('ivrMenus.form.maxFailures')}</Label>
              <Input id="max_failures" type="number" min={1} max={10} {...register("max_failures")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_timeouts">{t('ivrMenus.form.maxTimeouts')}</Label>
              <Input id="max_timeouts" type="number" min={1} max={10} {...register("max_timeouts")} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="inter_digit_timeout">{t('ivrMenus.form.interDigitTimeout')}</Label>
              <Input id="inter_digit_timeout" type="number" min={1} max={30} {...register("inter_digit_timeout")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="digit_len">{t('ivrMenus.form.maxDigitLength')}</Label>
              <Input id="digit_len" type="number" min={1} max={10} {...register("digit_len")} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.exitDestType')}</Label>
              <Select value={watch("exit_destination_type") || ""} onValueChange={(v) => { setValue("exit_destination_type", v); setValue("exit_destination_id", "") }}>
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  {ACTION_TYPES.map((at) => (
                    <SelectItem key={at.value} value={at.value}>{at.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t('ivrMenus.form.exitDest')}</Label>
              <DestinationPicker
                destinationType={watch("exit_destination_type") || ""}
                value={watch("exit_destination_id") ?? ""}
                onChange={(v) => setValue("exit_destination_id", v)}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
            <Label htmlFor="enabled">{t('ivrMenus.form.enabled')}</Label>
          </div>
        </TabsContent>

        <TabsContent value="options" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <Label>{t('ivrMenus.form.menuOptions')}</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ digits: "", action_type: "", action_target_id: "", action_target_value: "", label: "", position: fields.length })}
            >
              <Plus className="mr-1 h-3 w-3" /> {t('ivrMenus.form.addOption')}
            </Button>
          </div>

          <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-3">
            {fields.length === 0 && (
              <p className="text-xs text-muted-foreground py-2 text-center">{t('ivrMenus.form.noOptions')}</p>
            )}
            {fields.map((field, index) => (
              <div key={field.id} className="rounded border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{t('ivrMenus.form.option', { index: index + 1 })}</span>
                  <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('ivrMenus.form.digits')} *</Label>
                    <Input {...register(`options.${index}.digits`)} placeholder="e.g. 1" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('ivrMenus.form.actionType')} *</Label>
                    <Select
                      value={watch(`options.${index}.action_type`)}
                      onValueChange={(v) => { setValue(`options.${index}.action_type`, v); setValue(`options.${index}.action_target_id`, "") }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {ACTION_TYPES.map((at) => (
                          <SelectItem key={at.value} value={at.value}>{at.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('ivrMenus.form.label')}</Label>
                    <Input {...register(`options.${index}.label`)} placeholder={t('common.optional')} />
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('ivrMenus.form.target')}</Label>
                    <DestinationPicker
                      destinationType={watch(`options.${index}.action_type`) || ""}
                      value={watch(`options.${index}.action_target_id`) ?? ""}
                      onChange={(v) => setValue(`options.${index}.action_target_id`, v)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('ivrMenus.form.targetValue')}</Label>
                    <Input {...register(`options.${index}.action_target_value`)} placeholder={t('ivrMenus.form.targetValuePlaceholder')} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : ivrMenu ? t('ivrMenus.form.updateButton') : t('ivrMenus.form.createButton')}
      </Button>
    </form>
  )
}
