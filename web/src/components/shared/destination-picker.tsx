import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { useExtensions } from "@/api/extensions"
import { useRingGroups } from "@/api/ring-groups"
import { useQueues } from "@/api/queues"
import { useConferences } from "@/api/conferences"
import { useIvrMenus, type IVRMenu } from "@/api/ivr-menus"
import { useVoicemailBoxes } from "@/api/voicemail"
import { useTimeConditions } from "@/api/time-conditions"
import { useAudioPrompts } from "@/api/audio-prompts"
import { useHolidayCalendars } from "@/api/holiday-calendars"

interface PickerOption {
  value: string
  label: string
}

// Types that need an entity select picker
const ENTITY_TYPES = new Set([
  "extension", "ring_group", "voicemail", "ivr", "queue", "conference", "time_condition",
])

// Types that need no target (the type IS the action)
const NO_TARGET_TYPES = new Set(["hangup", "terminate", "repeat"])

interface DestinationPickerProps {
  destinationType: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

function useEntityOptions(destinationType: string): { options: PickerOption[]; isLoading: boolean } {
  const extensions = useExtensions()
  const ringGroups = useRingGroups()
  const queues = useQueues()
  const conferences = useConferences()
  const ivrMenus = useIvrMenus()
  const voicemail = useVoicemailBoxes()
  const timeConditions = useTimeConditions()

  switch (destinationType) {
    case "extension":
      return {
        options: (extensions.data ?? []).map((e) => ({
          value: e.id,
          label: `${e.extension_number}${e.internal_cid_name ? ` - ${e.internal_cid_name}` : ""}`,
        })),
        isLoading: extensions.isLoading,
      }
    case "ring_group":
      return {
        options: (ringGroups.data ?? []).map((rg) => ({
          value: rg.id,
          label: `${rg.group_number} - ${rg.name}`,
        })),
        isLoading: ringGroups.isLoading,
      }
    case "queue":
      return {
        options: (queues.data ?? []).map((q) => ({
          value: q.id,
          label: `${q.queue_number} - ${q.name}`,
        })),
        isLoading: queues.isLoading,
      }
    case "conference":
      return {
        options: (conferences.data ?? []).map((c) => ({
          value: c.id,
          label: `${c.room_number} - ${c.name}`,
        })),
        isLoading: conferences.isLoading,
      }
    case "ivr":
      return {
        options: (ivrMenus.data ?? []).map((m: IVRMenu) => ({
          value: m.id,
          label: m.name,
        })),
        isLoading: ivrMenus.isLoading,
      }
    case "voicemail":
      return {
        options: (voicemail.data ?? []).map((v) => ({
          value: v.id,
          label: `Mailbox ${v.mailbox_number}`,
        })),
        isLoading: voicemail.isLoading,
      }
    case "time_condition":
      return {
        options: (timeConditions.data ?? []).map((tc) => ({
          value: tc.id,
          label: tc.name,
        })),
        isLoading: timeConditions.isLoading,
      }
    default:
      return { options: [], isLoading: false }
  }
}

export function DestinationPicker({ destinationType, value, onChange, placeholder }: DestinationPickerProps) {
  const { t } = useTranslation()
  const { options, isLoading } = useEntityOptions(destinationType)

  // No target needed for hangup/terminate/repeat
  if (NO_TARGET_TYPES.has(destinationType)) {
    return (
      <Input disabled value="N/A" className="bg-muted" />
    )
  }

  // External number needs a text input
  if (destinationType === "external") {
    return (
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? t('destination.phoneNumber')}
      />
    )
  }

  // Entity types get a select dropdown
  if (ENTITY_TYPES.has(destinationType)) {
    return (
      <Select value={value || ""} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder={isLoading ? t('common.loading') : (placeholder ?? t('destination.select'))} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
          {options.length === 0 && !isLoading && (
            <div className="px-2 py-1.5 text-xs text-muted-foreground">{t('destination.noItemsFound')}</div>
          )}
        </SelectContent>
      </Select>
    )
  }

  // Fallback: plain text input for unknown types or empty
  return (
    <Input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder ?? "ID"}
    />
  )
}

// Audio prompt picker
interface AudioPromptPickerProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function AudioPromptPicker({ value, onChange, placeholder }: AudioPromptPickerProps) {
  const { t } = useTranslation()
  const { data: prompts, isLoading } = useAudioPrompts()
  const options: PickerOption[] = (prompts ?? []).map((p) => ({
    value: p.id,
    label: p.name,
  }))

  return (
    <Select value={value || "_none_"} onValueChange={(v) => onChange(v === "_none_" ? "" : v)}>
      <SelectTrigger>
        <SelectValue placeholder={isLoading ? t('common.loading') : (placeholder ?? t('destination.selectAudioPrompt'))} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="_none_">{t('common.none')}</SelectItem>
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

// Holiday calendar picker
interface HolidayCalendarPickerProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function HolidayCalendarPicker({ value, onChange, placeholder }: HolidayCalendarPickerProps) {
  const { t } = useTranslation()
  const { data: calendars, isLoading } = useHolidayCalendars()
  const options: PickerOption[] = (calendars ?? []).map((c) => ({
    value: c.id,
    label: c.name,
  }))

  return (
    <Select value={value || "_none_"} onValueChange={(v) => onChange(v === "_none_" ? "" : v)}>
      <SelectTrigger>
        <SelectValue placeholder={isLoading ? t('common.loading') : (placeholder ?? t('destination.selectCalendar'))} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="_none_">{t('common.none')}</SelectItem>
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
