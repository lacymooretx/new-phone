import { useTranslation } from "react-i18next"
import { useSiteSummaries } from "@/api/sites"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"

interface SiteSelectorProps {
  value: string | null | undefined
  onChange: (value: string | null) => void
  label?: string
  className?: string
}

export function SiteSelector({ value, onChange, label, className }: SiteSelectorProps) {
  const { t } = useTranslation()
  const { data: sites } = useSiteSummaries()

  return (
    <div className={className}>
      {label && <Label className="mb-2 block">{label}</Label>}
      <Select
        value={value || "_none_"}
        onValueChange={(v) => onChange(v === "_none_" ? null : v)}
      >
        <SelectTrigger>
          <SelectValue placeholder={t("sites.form.selectSite")} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_none_">{t("sites.form.noSite")}</SelectItem>
          {sites?.map((site) => (
            <SelectItem key={site.id} value={site.id}>
              {site.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
