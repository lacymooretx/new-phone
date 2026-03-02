import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { DNCList, DNCListCreate } from "@/api/compliance"

const LIST_TYPES = [
  { value: "internal", label: "Internal" },
  { value: "national", label: "National" },
  { value: "state", label: "State" },
  { value: "custom", label: "Custom" },
]

interface DNCListFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: DNCListCreate) => void
  initialData?: DNCList | null
  isPending?: boolean
}

export function DNCListForm({
  open,
  onOpenChange,
  onSubmit,
  initialData,
  isPending,
}: DNCListFormProps) {
  const { t } = useTranslation()
  const [name, setName] = useState(initialData?.name ?? "")
  const [description, setDescription] = useState(initialData?.description ?? "")
  const [listType, setListType] = useState(initialData?.list_type ?? "internal")
  const [sourceUrl, setSourceUrl] = useState(initialData?.source_url ?? "")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name,
      description: description || null,
      list_type: listType,
      source_url: sourceUrl || null,
    })
  }

  const showSourceUrl = listType === "national" || listType === "state"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {initialData
              ? t("compliance.dnc.editList")
              : t("compliance.dnc.createList")}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">{t("compliance.dnc.form.name")}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={255}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">{t("compliance.dnc.form.description")}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label>{t("compliance.dnc.form.listType")}</Label>
            <Select value={listType} onValueChange={setListType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LIST_TYPES.map((lt) => (
                  <SelectItem key={lt.value} value={lt.value}>
                    {lt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {showSourceUrl && (
            <div className="space-y-2">
              <Label htmlFor="sourceUrl">{t("compliance.dnc.form.sourceUrl")}</Label>
              <Input
                id="sourceUrl"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://"
                maxLength={500}
              />
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={!name.trim() || isPending}>
              {isPending ? t("common.saving") : t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
