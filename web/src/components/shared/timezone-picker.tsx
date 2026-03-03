import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Check, ChevronsUpDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

// Get all IANA timezones from the browser
const TIMEZONES: string[] = (() => {
  try {
    return Intl.supportedValuesOf("timeZone")
  } catch {
    // Fallback for older browsers
    return [
      "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
      "America/Phoenix", "America/Anchorage", "Pacific/Honolulu", "America/Toronto",
      "America/Vancouver", "America/Mexico_City", "America/Bogota", "America/Sao_Paulo",
      "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
      "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Asia/Dubai",
      "Australia/Sydney", "Pacific/Auckland", "UTC",
    ]
  }
})()

// Group timezones by region for nicer display
function getRegion(tz: string): string {
  return tz.split("/")[0]
}

function formatTzLabel(tz: string): string {
  try {
    const now = new Date()
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      timeZoneName: "shortOffset",
    })
    const parts = formatter.formatToParts(now)
    const offset = parts.find((p) => p.type === "timeZoneName")?.value || ""
    const city = tz.split("/").pop()?.replace(/_/g, " ") || tz
    return `${city} (${offset})`
  } catch {
    return tz
  }
}

interface TimezonePickerProps {
  value: string
  onChange: (value: string) => void
  className?: string
}

export function TimezonePicker({ value, onChange, className }: TimezonePickerProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  const label = useMemo(() => (value ? formatTzLabel(value) : null), [value])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn("w-full justify-between font-normal", !value && "text-muted-foreground", className)}
        >
          {label || t("sites.form.timezonePlaceholder", "Select timezone...")}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[340px] p-0" align="start">
        <Command>
          <CommandInput placeholder={t("sites.form.timezoneSearch", "Search timezones...")} />
          <CommandList>
            <CommandEmpty>{t("common.noResults", "No results found.")}</CommandEmpty>
            {["America", "Europe", "Asia", "Africa", "Australia", "Pacific", "Atlantic", "Indian"].map((region) => {
              const regionTzs = TIMEZONES.filter((tz) => getRegion(tz) === region)
              if (regionTzs.length === 0) return null
              return (
                <CommandGroup key={region} heading={region}>
                  {regionTzs.map((tz) => (
                    <CommandItem
                      key={tz}
                      value={tz}
                      onSelect={() => {
                        onChange(tz)
                        setOpen(false)
                      }}
                    >
                      <Check className={cn("mr-2 h-4 w-4", value === tz ? "opacity-100" : "opacity-0")} />
                      {formatTzLabel(tz)}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
