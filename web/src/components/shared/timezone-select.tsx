import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const TIMEZONES = [
  { value: "America/New_York", label: "Eastern (New York)" },
  { value: "America/Chicago", label: "Central (Chicago)" },
  { value: "America/Denver", label: "Mountain (Denver)" },
  { value: "America/Los_Angeles", label: "Pacific (Los Angeles)" },
  { value: "America/Anchorage", label: "Alaska (Anchorage)" },
  { value: "Pacific/Honolulu", label: "Hawaii (Honolulu)" },
  { value: "America/Phoenix", label: "Arizona (Phoenix)" },
  { value: "America/Indiana/Indianapolis", label: "Indiana (Indianapolis)" },
  { value: "America/Puerto_Rico", label: "Atlantic (Puerto Rico)" },
  { value: "America/Toronto", label: "Eastern (Toronto)" },
  { value: "America/Winnipeg", label: "Central (Winnipeg)" },
  { value: "America/Edmonton", label: "Mountain (Edmonton)" },
  { value: "America/Vancouver", label: "Pacific (Vancouver)" },
  { value: "America/St_Johns", label: "Newfoundland (St. John's)" },
  { value: "America/Halifax", label: "Atlantic (Halifax)" },
  { value: "America/Mexico_City", label: "Central (Mexico City)" },
  { value: "America/Bogota", label: "Colombia (Bogota)" },
  { value: "America/Sao_Paulo", label: "Brasilia (Sao Paulo)" },
  { value: "America/Argentina/Buenos_Aires", label: "Argentina (Buenos Aires)" },
  { value: "Europe/London", label: "GMT (London)" },
  { value: "Europe/Paris", label: "CET (Paris)" },
  { value: "Europe/Berlin", label: "CET (Berlin)" },
  { value: "Europe/Madrid", label: "CET (Madrid)" },
  { value: "Europe/Rome", label: "CET (Rome)" },
  { value: "Europe/Amsterdam", label: "CET (Amsterdam)" },
  { value: "Europe/Brussels", label: "CET (Brussels)" },
  { value: "Europe/Stockholm", label: "CET (Stockholm)" },
  { value: "Europe/Helsinki", label: "EET (Helsinki)" },
  { value: "Europe/Athens", label: "EET (Athens)" },
  { value: "Europe/Istanbul", label: "Turkey (Istanbul)" },
  { value: "Europe/Moscow", label: "Moscow (MSK)" },
  { value: "Asia/Dubai", label: "Gulf (Dubai)" },
  { value: "Asia/Kolkata", label: "India (Kolkata)" },
  { value: "Asia/Singapore", label: "Singapore" },
  { value: "Asia/Hong_Kong", label: "Hong Kong" },
  { value: "Asia/Shanghai", label: "China (Shanghai)" },
  { value: "Asia/Tokyo", label: "Japan (Tokyo)" },
  { value: "Asia/Seoul", label: "Korea (Seoul)" },
  { value: "Australia/Sydney", label: "AEST (Sydney)" },
  { value: "Australia/Melbourne", label: "AEST (Melbourne)" },
  { value: "Australia/Perth", label: "AWST (Perth)" },
  { value: "Australia/Adelaide", label: "ACST (Adelaide)" },
  { value: "Pacific/Auckland", label: "NZST (Auckland)" },
  { value: "UTC", label: "UTC" },
]

interface TimezoneSelectProps {
  value: string
  onChange: (value: string) => void
}

export function TimezoneSelect({ value, onChange }: TimezoneSelectProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Select timezone" />
      </SelectTrigger>
      <SelectContent>
        {TIMEZONES.map((tz) => (
          <SelectItem key={tz.value} value={tz.value}>
            {tz.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
