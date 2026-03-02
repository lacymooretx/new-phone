import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { CallerIdRule, CallerIdRuleCreate } from "@/api/caller-id-rules"

const callerIdRuleSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  rule_type: z.string().min(1, "Required"),
  match_pattern: z.string().min(1, "Required"),
  action: z.string().min(1, "Required"),
  priority: z.coerce.number().min(0).default(0),
  notes: z.string().optional().or(z.literal("")),
})

type FormValues = z.infer<typeof callerIdRuleSchema>

interface CallerIdRuleFormProps {
  callerIdRule?: CallerIdRule | null
  onSubmit: (data: CallerIdRuleCreate) => void
  isLoading: boolean
}

export function CallerIdRuleForm({ callerIdRule, onSubmit, isLoading }: CallerIdRuleFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(callerIdRuleSchema) as any,
    defaultValues: {
      name: callerIdRule?.name ?? "",
      rule_type: callerIdRule?.rule_type ?? "",
      match_pattern: callerIdRule?.match_pattern ?? "",
      action: callerIdRule?.action ?? "",
      priority: callerIdRule?.priority ?? 0,
      notes: callerIdRule?.notes ?? "",
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: CallerIdRuleCreate = {
      ...values,
      notes: values.notes || undefined,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">{t('callerIdRules.form.name')} *</Label>
        <Input id="name" placeholder={t('callerIdRules.form.namePlaceholder')} {...register("name")} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('common.type')} *</Label>
          <Select value={watch("rule_type")} onValueChange={(v) => setValue("rule_type", v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="block">Block</SelectItem>
              <SelectItem value="allow">Allow</SelectItem>
            </SelectContent>
          </Select>
          {errors.rule_type && <p className="text-xs text-destructive">{errors.rule_type.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>{t('common.actions')} *</Label>
          <Select value={watch("action")} onValueChange={(v) => setValue("action", v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select action" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="reject">Reject</SelectItem>
              <SelectItem value="hangup">Hangup</SelectItem>
              <SelectItem value="voicemail">Voicemail</SelectItem>
              <SelectItem value="allow">Allow</SelectItem>
            </SelectContent>
          </Select>
          {errors.action && <p className="text-xs text-destructive">{errors.action.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="match_pattern">{t('callerIdRules.form.matchPattern')} *</Label>
          <Input id="match_pattern" {...register("match_pattern")} placeholder="e.g., ^\\+1555.*$" />
          {errors.match_pattern && <p className="text-xs text-destructive">{errors.match_pattern.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="priority">{t('callerIdRules.form.priority')}</Label>
          <Input id="priority" type="number" min={0} {...register("priority")} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">{t('common.notes')}</Label>
        <Textarea id="notes" {...register("notes")} />
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : callerIdRule ? t('callerIdRules.form.updateButton') : t('callerIdRules.form.createButton')}
      </Button>
    </form>
  )
}
