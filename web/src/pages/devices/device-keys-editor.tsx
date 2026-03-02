import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { useDeviceKeys, useUpdateDeviceKeys, type DeviceKeyCreate, type DeviceKey } from "@/api/devices"
import type { Device } from "@/api/devices"
import { usePhoneModels } from "@/api/phone-models"
import { useExtensions } from "@/api/extensions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Save } from "lucide-react"

const KEY_TYPES = [
  { value: "none", label: "None" },
  { value: "line", label: "Line" },
  { value: "blf", label: "BLF" },
  { value: "speed_dial", label: "Speed Dial" },
  { value: "dtmf", label: "DTMF" },
  { value: "park", label: "Park" },
  { value: "intercom", label: "Intercom" },
]

interface KeySlot {
  key_section: string
  key_index: number
  key_type: string
  label: string
  value: string
  line: number
}

interface DeviceKeysEditorProps {
  device: Device
  onClose: () => void
}

export function DeviceKeysEditor({ device, onClose }: DeviceKeysEditorProps) {
  const { t } = useTranslation()
  const { data: existingKeys, isLoading: keysLoading } = useDeviceKeys(device.id)
  const { data: phoneModels } = usePhoneModels()
  const { data: extensions } = useExtensions()
  const updateKeysMutation = useUpdateDeviceKeys()

  const [slots, setSlots] = useState<KeySlot[]>([])

  const phoneModel = phoneModels?.find((m) => m.id === device.phone_model_id)
  const maxKeys = phoneModel?.max_line_keys ?? 10

  // Initialize slots from existing keys or create empty slots
  useEffect(() => {
    const keyMap = new Map<string, DeviceKey>()
    if (existingKeys) {
      for (const k of existingKeys) {
        keyMap.set(`${k.key_section}-${k.key_index}`, k)
      }
    }

    const newSlots: KeySlot[] = []
    for (let i = 1; i <= maxKeys; i++) {
      const existing = keyMap.get(`line_key-${i}`)
      newSlots.push({
        key_section: "line_key",
        key_index: i,
        key_type: existing?.key_type ?? "none",
        label: existing?.label ?? "",
        value: existing?.value ?? "",
        line: existing?.line ?? 1,
      })
    }
    setSlots(newSlots)
  }, [existingKeys, maxKeys])

  const updateSlot = (index: number, field: keyof KeySlot, value: string | number) => {
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, [field]: value } : s))
  }

  const handleSave = () => {
    const keys: DeviceKeyCreate[] = slots
      .filter((s) => s.key_type !== "none")
      .map((s) => ({
        key_section: s.key_section,
        key_index: s.key_index,
        key_type: s.key_type,
        label: s.label || null,
        value: s.value || null,
        line: s.line,
      }))

    updateKeysMutation.mutate(
      { deviceId: device.id, keys },
      {
        onSuccess: () => {
          toast.success(t('toast.saved', { item: t('devices.form.lineKeys') }))
          onClose()
        },
        onError: (err) => toast.error(err.message),
      },
    )
  }

  if (keysLoading) {
    return <div className="flex items-center justify-center py-8 text-muted-foreground">{t('common.loading')}</div>
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        {phoneModel?.manufacturer} {phoneModel?.model_name} — {maxKeys} line keys available
      </div>

      <div className="max-h-[60vh] overflow-y-auto space-y-2">
        {slots.map((slot, idx) => (
          <div key={slot.key_index} className="grid grid-cols-[3rem_8rem_1fr_1fr_4rem] gap-2 items-center">
            <span className="text-xs font-mono text-muted-foreground text-center">{slot.key_index}</span>

            <Select value={slot.key_type} onValueChange={(v) => updateSlot(idx, "key_type", v)}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KEY_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {slot.key_type === "blf" ? (
              <Select
                value={slot.value || "_none_"}
                onValueChange={(v) => {
                  const ext = extensions?.find((e) => e.extension_number === v)
                  updateSlot(idx, "value", v === "_none_" ? "" : v)
                  if (ext) updateSlot(idx, "label", ext.internal_cid_name || ext.extension_number)
                }}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select extension" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none_">Select...</SelectItem>
                  {extensions?.map((e) => (
                    <SelectItem key={e.id} value={e.extension_number}>
                      {e.extension_number} — {e.internal_cid_name || "No name"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                className="h-8 text-xs"
                placeholder={slot.key_type === "none" ? "" : "Value"}
                value={slot.value}
                onChange={(e) => updateSlot(idx, "value", e.target.value)}
                disabled={slot.key_type === "none"}
              />
            )}

            <Input
              className="h-8 text-xs"
              placeholder={slot.key_type === "none" ? "" : "Label"}
              value={slot.label}
              onChange={(e) => updateSlot(idx, "label", e.target.value)}
              disabled={slot.key_type === "none"}
            />

            <Select
              value={String(slot.line)}
              onValueChange={(v) => updateSlot(idx, "line", Number(v))}
              disabled={slot.key_type === "none"}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <SelectItem key={n} value={String(n)}>L{n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center pt-2">
        <div className="text-xs text-muted-foreground">
          {slots.filter((s) => s.key_type !== "none").length} of {maxKeys} keys configured
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClose}>{t('common.cancel')}</Button>
          <Button onClick={handleSave} disabled={updateKeysMutation.isPending}>
            <Save className="mr-2 h-4 w-4" />
            {updateKeysMutation.isPending ? t('common.saving') : t('common.save')}
          </Button>
        </div>
      </div>
    </div>
  )
}
