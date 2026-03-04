import { useTranslation } from "react-i18next"
import { PageHeader } from "@/components/shared/page-header"
import { useExtensions } from "@/api/extensions"
import { useParkingLots, useAllSlotStates, type SlotState } from "@/api/parking"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Phone,
  PhoneOff,
  ParkingSquare,
  Users,
  Loader2,
  Star,
} from "lucide-react"

function ExtensionPresenceGrid() {
  const { t } = useTranslation()
  const { data: extensions, isLoading } = useExtensions()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const activeExtensions = (extensions ?? []).filter((ext) => ext.is_active)

  return (
    <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
      {activeExtensions.map((ext) => (
        <div
          key={ext.id}
          className="flex flex-col items-center rounded-md border p-2 text-center transition-colors hover:bg-accent"
        >
          <div className="text-sm font-mono font-medium">{ext.extension_number}</div>
          <div className="truncate text-xs text-muted-foreground w-full">
            {ext.internal_cid_name || ext.extension_number}
          </div>
          <Badge
            variant={ext.dnd_enabled ? "destructive" : "secondary"}
            className="mt-1 text-[10px]"
          >
            {ext.dnd_enabled ? t("receptionist.dnd") : t("receptionist.available")}
          </Badge>
        </div>
      ))}
    </div>
  )
}

function ActiveCallsPanel() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Phone className="h-4 w-4" />
          {t("receptionist.activeCalls")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
          <PhoneOff className="mr-2 h-4 w-4" />
          {t("receptionist.noActiveCalls")}
        </div>
      </CardContent>
    </Card>
  )
}

function ParkingPanel() {
  const { t } = useTranslation()
  const { data: lots, isLoading: lotsLoading } = useParkingLots()
  const { data: slots, isLoading: slotsLoading } = useAllSlotStates()

  const isLoading = lotsLoading || slotsLoading
  const occupiedSlots = (slots ?? []).filter((s: SlotState) => s.occupied)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ParkingSquare className="h-4 w-4" />
          {t("receptionist.parkingLot")}
          {occupiedSlots.length > 0 && (
            <Badge variant="secondary">{occupiedSlots.length}</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : occupiedSlots.length === 0 ? (
          <div className="text-center py-4 text-sm text-muted-foreground">
            {t("receptionist.noParkedCalls")}
          </div>
        ) : (
          <div className="space-y-2">
            {occupiedSlots.map((slot: SlotState) => (
              <div
                key={slot.slot_number}
                className="flex items-center justify-between rounded-md border bg-green-50 p-2 dark:bg-green-900/20"
              >
                <div>
                  <span className="font-mono text-sm font-medium">
                    {t("receptionist.slot")} {slot.slot_number}
                  </span>
                  <span className="ml-2 text-sm text-muted-foreground">
                    {slot.caller_id_name || slot.caller_id_number || t("common.unknown")}
                  </span>
                </div>
                <Button variant="outline" size="sm">
                  {t("receptionist.pickup")}
                </Button>
              </div>
            ))}
          </div>
        )}
        <div className="mt-2 text-xs text-muted-foreground">
          {t("receptionist.totalLots")}: {lots?.length ?? 0}
        </div>
      </CardContent>
    </Card>
  )
}

function SpeedDialsPanel() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Star className="h-4 w-4" />
          {t("receptionist.speedDials")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
          {t("receptionist.noSpeedDials")}
        </div>
      </CardContent>
    </Card>
  )
}

export function ReceptionistPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("receptionist.title")}
        description={t("receptionist.description")}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: t("receptionist.title") },
        ]}
      />

      {/* Extension Presence Grid */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4" />
            {t("receptionist.extensionPresence")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ExtensionPresenceGrid />
        </CardContent>
      </Card>

      {/* Multi-panel layout */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <ActiveCallsPanel />
        <ParkingPanel />
        <SpeedDialsPanel />
      </div>
    </div>
  )
}
