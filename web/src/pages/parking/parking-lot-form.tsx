import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import type { ParkingLot, ParkingLotCreate } from "@/api/parking"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { SiteSelector } from "@/components/shared/site-selector"

interface ParkingLotFormProps {
  lot?: ParkingLot | null
  onSubmit: (data: ParkingLotCreate) => void
  isLoading: boolean
}

export function ParkingLotForm({ lot, onSubmit, isLoading }: ParkingLotFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<ParkingLotCreate>({
    defaultValues: {
      name: lot?.name ?? "",
      lot_number: lot?.lot_number ?? 1,
      slot_start: lot?.slot_start ?? 70,
      slot_end: lot?.slot_end ?? 79,
      timeout_seconds: lot?.timeout_seconds ?? 60,
      comeback_enabled: lot?.comeback_enabled ?? true,
      comeback_extension: lot?.comeback_extension ?? null,
      moh_prompt_id: lot?.moh_prompt_id ?? null,
      site_id: lot?.site_id ?? null,
    },
  })

  const comebackEnabled = watch("comeback_enabled")

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('parking.form.name')}</Label>
          <Input
            id="name"
            {...register("name", { required: t('common.required') })}
            placeholder={t('parking.form.namePlaceholder')}
          />
          {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="lot_number">{t('parking.form.lotNumber')}</Label>
          <Input
            id="lot_number"
            type="number"
            {...register("lot_number", { required: true, valueAsNumber: true, min: 1 })}
          />
          {errors.lot_number && <p className="text-sm text-destructive">{t('common.required')}</p>}
        </div>
      </div>

      <SiteSelector
        value={watch("site_id")}
        onChange={(v) => setValue("site_id", v)}
        label={t("sites.form.site")}
      />

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="slot_start">{t('parking.form.slotStart')}</Label>
          <Input
            id="slot_start"
            type="number"
            {...register("slot_start", { required: true, valueAsNumber: true, min: 1 })}
          />
          {errors.slot_start && <p className="text-sm text-destructive">{t('common.required')}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="slot_end">{t('parking.form.slotEnd')}</Label>
          <Input
            id="slot_end"
            type="number"
            {...register("slot_end", { required: true, valueAsNumber: true, min: 1 })}
          />
          {errors.slot_end && <p className="text-sm text-destructive">{t('common.required')}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="timeout_seconds">{t('parking.form.timeout')}</Label>
        <Input
          id="timeout_seconds"
          type="number"
          {...register("timeout_seconds", { required: true, valueAsNumber: true, min: 10, max: 600 })}
        />
        {errors.timeout_seconds && <p className="text-sm text-destructive">{t('common.required')}</p>}
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="comeback_enabled"
          checked={comebackEnabled}
          onCheckedChange={(checked) => setValue("comeback_enabled", checked)}
        />
        <Label htmlFor="comeback_enabled">{t('parking.form.comebackEnabled')}</Label>
      </div>

      {comebackEnabled && (
        <div className="space-y-2">
          <Label htmlFor="comeback_extension">{t('parking.form.comebackExtension')}</Label>
          <Input
            id="comeback_extension"
            {...register("comeback_extension")}
            placeholder={t('parking.form.comebackExtensionPlaceholder')}
          />
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? t('common.saving') : lot ? t('common.save') : t('common.create')}
        </Button>
      </div>
    </form>
  )
}
