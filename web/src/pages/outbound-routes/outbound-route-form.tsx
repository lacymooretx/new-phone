import { useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useSipTrunks } from "@/api/sip-trunks"
import type { OutboundRoute, OutboundRouteCreate } from "@/api/outbound-routes"

const outboundRouteSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  dial_pattern: z.string().min(1, "Required"),
  prepend_digits: z.string().optional().or(z.literal("")),
  strip_digits: z.coerce.number().min(0).default(0),
  cid_mode: z.string().default("extension"),
  custom_cid: z.string().optional().or(z.literal("")),
  priority: z.coerce.number().min(0).default(100),
  enabled: z.boolean().default(true),
})

type FormValues = z.infer<typeof outboundRouteSchema>

interface OutboundRouteFormProps {
  outboundRoute?: OutboundRoute | null
  onSubmit: (data: OutboundRouteCreate) => void
  isLoading: boolean
}

export function OutboundRouteForm({ outboundRoute, onSubmit, isLoading }: OutboundRouteFormProps) {
  const { t } = useTranslation()
  const { data: trunks } = useSipTrunks()
  const [selectedTrunkIds, setSelectedTrunkIds] = useState<string[]>(
    outboundRoute?.trunk_ids ?? []
  )

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(outboundRouteSchema) as any,
    defaultValues: {
      name: outboundRoute?.name ?? "",
      dial_pattern: outboundRoute?.dial_pattern ?? "",
      prepend_digits: outboundRoute?.prepend_digits ?? "",
      strip_digits: outboundRoute?.strip_digits ?? 0,
      cid_mode: outboundRoute?.cid_mode ?? "extension",
      custom_cid: outboundRoute?.custom_cid ?? "",
      priority: outboundRoute?.priority ?? 100,
      enabled: outboundRoute?.enabled ?? true,
    },
  })

  const cidMode = watch("cid_mode")

  const addTrunk = (trunkId: string) => {
    if (!selectedTrunkIds.includes(trunkId)) {
      setSelectedTrunkIds([...selectedTrunkIds, trunkId])
    }
  }

  const removeTrunk = (trunkId: string) => {
    setSelectedTrunkIds(selectedTrunkIds.filter((id) => id !== trunkId))
  }

  const moveTrunk = (index: number, direction: "up" | "down") => {
    const newIds = [...selectedTrunkIds]
    const swapIndex = direction === "up" ? index - 1 : index + 1
    if (swapIndex < 0 || swapIndex >= newIds.length) return
    ;[newIds[index], newIds[swapIndex]] = [newIds[swapIndex], newIds[index]]
    setSelectedTrunkIds(newIds)
  }

  const submitHandler = (values: FormValues) => {
    const data: OutboundRouteCreate = {
      ...values,
      prepend_digits: values.prepend_digits || undefined,
      custom_cid: values.custom_cid || undefined,
      trunk_ids: selectedTrunkIds,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('outboundRoutes.form.name')} *</Label>
          <Input id="name" placeholder={t('outboundRoutes.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="dial_pattern">{t('outboundRoutes.form.dialPattern', { defaultValue: 'Dial Pattern' })} *</Label>
          <Input id="dial_pattern" placeholder={t('outboundRoutes.form.patternPlaceholder')} {...register("dial_pattern")} />
          {errors.dial_pattern && <p className="text-xs text-destructive">{errors.dial_pattern.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="prepend_digits">{t('outboundRoutes.form.prepend')}</Label>
          <Input id="prepend_digits" placeholder={t('outboundRoutes.form.prependPlaceholder', { defaultValue: 'e.g., 1' })} {...register("prepend_digits")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="strip_digits">{t('outboundRoutes.form.stripDigits', { defaultValue: 'Strip Digits' })}</Label>
          <Input id="strip_digits" type="number" min={0} {...register("strip_digits")} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('outboundRoutes.form.callerIdMode')}</Label>
          <Select value={cidMode} onValueChange={(v) => setValue("cid_mode", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="extension">{t('destination.extension')}</SelectItem>
              <SelectItem value="trunk">{t('outboundRoutes.form.trunk', { defaultValue: 'Trunk' })}</SelectItem>
              <SelectItem value="custom">{t('outboundRoutes.form.custom', { defaultValue: 'Custom' })}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {cidMode === "custom" && (
          <div className="space-y-2">
            <Label htmlFor="custom_cid">{t('outboundRoutes.form.customCid', { defaultValue: 'Custom CID' })}</Label>
            <Input id="custom_cid" placeholder="+15551234567" type="tel" {...register("custom_cid")} />
          </div>
        )}
      </div>

      {/* SIP Trunk Selection */}
      <div className="space-y-2">
        <Label>{t('outboundRoutes.form.trunks', { defaultValue: 'SIP Trunks' })} *</Label>
        <p className="text-xs text-muted-foreground">
          {t('outboundRoutes.form.trunksHelp', { defaultValue: 'Select trunks for this route. Order determines failover priority.' })}
        </p>

        {trunks && trunks.length > 0 ? (
          <div className="space-y-1 rounded-md border p-2">
            {trunks.map((trunk) => {
              const isSelected = selectedTrunkIds.includes(trunk.id)
              const position = selectedTrunkIds.indexOf(trunk.id)
              return (
                <div
                  key={trunk.id}
                  role="button"
                  tabIndex={0}
                  className={`flex items-center gap-2 rounded px-2 py-1.5 text-sm cursor-pointer transition-colors ${isSelected ? "bg-primary/10 border border-primary/30" : "hover:bg-muted/50"}`}
                  onClick={() => isSelected ? removeTrunk(trunk.id) : addTrunk(trunk.id)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); isSelected ? removeTrunk(trunk.id) : addTrunk(trunk.id) }}}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    readOnly
                    className="size-4 rounded accent-primary pointer-events-none"
                  />
                  {isSelected && (
                    <span className="text-xs font-medium text-primary w-4">{position + 1}.</span>
                  )}
                  <span className="flex-1 truncate">{trunk.name}</span>
                  <span className="text-xs text-muted-foreground">{trunk.host}</span>
                  {isSelected && selectedTrunkIds.length > 1 && (
                    <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                      <Button
                        type="button" variant="ghost" size="sm"
                        className="h-6 w-6 p-0" disabled={position === 0}
                        onClick={() => moveTrunk(position, "up")}
                      >
                        ↑
                      </Button>
                      <Button
                        type="button" variant="ghost" size="sm"
                        className="h-6 w-6 p-0" disabled={position === selectedTrunkIds.length - 1}
                        onClick={() => moveTrunk(position, "down")}
                      >
                        ↓
                      </Button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : trunks?.length === 0 ? (
          <p className="text-xs text-destructive">
            {t('outboundRoutes.form.noTrunks', { defaultValue: 'No SIP trunks configured. Create a trunk first.' })}
          </p>
        ) : null}

        {selectedTrunkIds.length === 0 && trunks && trunks.length > 0 && (
          <p className="text-xs text-destructive">
            {t('outboundRoutes.form.trunkRequired', { defaultValue: 'At least one trunk is required for outbound calls.' })}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="priority">{t('outboundRoutes.form.priority')}</Label>
        <Input id="priority" type="number" min={0} {...register("priority")} />
      </div>

      <div className="flex items-center gap-2">
        <Switch id="enabled" checked={watch("enabled")} onCheckedChange={(v) => setValue("enabled", v)} />
        <Label htmlFor="enabled">{t('common.enabled')}</Label>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : outboundRoute ? t('outboundRoutes.form.updateButton') : t('outboundRoutes.form.createButton')}
      </Button>
    </form>
  )
}
