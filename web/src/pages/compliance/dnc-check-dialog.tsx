import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { type DNCCheckResult } from "@/api/compliance"

interface DNCCheckDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  checkPhone: string
  onCheckPhoneChange: (value: string) => void
  onCheck: () => void
  isChecking: boolean
  checkResult: DNCCheckResult | null
}

export function DNCCheckDialog({
  open,
  onOpenChange,
  checkPhone,
  onCheckPhoneChange,
  onCheck,
  isChecking,
  checkResult,
}: DNCCheckDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("compliance.dnc.checkNumber")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={checkPhone}
              onChange={(e) => onCheckPhoneChange(e.target.value)}
              placeholder={t("compliance.dnc.phonePlaceholder")}
            />
            <Button onClick={onCheck} disabled={!checkPhone.trim() || isChecking}>
              {t("compliance.dnc.check")}
            </Button>
          </div>
          {checkResult && (
            <Card className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t("compliance.dnc.status")}:</span>
                <Badge variant={checkResult.is_blocked ? "destructive" : "secondary"}>
                  {checkResult.is_blocked
                    ? t("compliance.dnc.blocked")
                    : t("compliance.dnc.clear")}
                </Badge>
              </div>
              {checkResult.matched_lists.length > 0 && (
                <div>
                  <span className="text-sm font-medium">{t("compliance.dnc.matchedLists")}:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {checkResult.matched_lists.map((name) => (
                      <Badge key={name} variant="outline">{name}</Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className="text-sm">{t("compliance.consent.hasConsent")}:</span>
                <Badge variant={checkResult.has_consent ? "secondary" : "outline"}>
                  {checkResult.has_consent ? t("common.yes") : t("common.no")}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">{t("compliance.settings.callingWindow")}:</span>
                <Badge variant={checkResult.calling_window_ok ? "secondary" : "destructive"}>
                  {checkResult.calling_window_ok ? t("common.yes") : t("common.no")}
                </Badge>
              </div>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
