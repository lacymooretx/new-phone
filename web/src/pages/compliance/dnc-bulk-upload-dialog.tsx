import { useTranslation } from "react-i18next"
import { Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface DNCBulkUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  bulkText: string
  onBulkTextChange: (value: string) => void
  onUpload: () => void
  isUploading: boolean
}

export function DNCBulkUploadDialog({
  open,
  onOpenChange,
  bulkText,
  onBulkTextChange,
  onUpload,
  isUploading,
}: DNCBulkUploadDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("compliance.dnc.bulkUpload")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t("compliance.dnc.bulkPhoneNumbers")}</Label>
            <Textarea
              value={bulkText}
              onChange={(e) => onBulkTextChange(e.target.value)}
              rows={8}
              placeholder={t("compliance.dnc.bulkPlaceholder")}
            />
            <p className="text-xs text-muted-foreground">
              {t("compliance.dnc.bulkHint")}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={onUpload} disabled={!bulkText.trim() || isUploading}>
            <Upload className="mr-2 h-4 w-4" />
            {isUploading ? t("common.saving") : t("compliance.dnc.bulkUpload")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
