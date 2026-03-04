import { useState } from "react"
import { useTranslation } from "react-i18next"
import { PageHeader } from "@/components/shared/page-header"
import {
  useRooms,
  useCreateRoom,

  useCheckIn,
  useCheckOut,
  type Room,
  type RoomCreate,
} from "@/api/hospitality"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Plus,
  Hotel,
  LogIn,
  LogOut,
  Loader2,
} from "lucide-react"
import { toast } from "sonner"

const STATUS_COLORS: Record<string, string> = {
  vacant: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  occupied: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  checkout: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  maintenance: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
}

const HOUSEKEEPING_COLORS: Record<string, string> = {
  clean: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  dirty: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  inspected: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  out_of_order: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
}

function RoomCard({
  room,
  onCheckIn,
  onCheckOut,
}: {
  room: Room
  onCheckIn: (room: Room) => void
  onCheckOut: (room: Room) => void
}) {
  const { t } = useTranslation()

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-mono">
            {room.room_number}
          </CardTitle>
          <Badge className={STATUS_COLORS[room.status] ?? ""}>{room.status}</Badge>
        </div>
        {room.room_type && (
          <p className="text-xs text-muted-foreground">{room.room_type}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={HOUSEKEEPING_COLORS[room.housekeeping_status] ?? ""}
          >
            {room.housekeeping_status.replace("_", " ")}
          </Badge>
          {room.floor && (
            <span className="text-xs text-muted-foreground">
              {t("hospitality.floor")} {room.floor}
            </span>
          )}
        </div>

        {room.guest_name && (
          <div className="text-sm">
            <span className="text-muted-foreground">{t("hospitality.guest")}:</span>{" "}
            {room.guest_name}
          </div>
        )}

        {room.wake_up_enabled && room.wake_up_time && (
          <div className="text-xs text-muted-foreground">
            {t("hospitality.wakeUp")}: {room.wake_up_time}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          {room.status === "vacant" ? (
            <Button
              size="sm"
              variant="default"
              className="w-full"
              onClick={() => onCheckIn(room)}
            >
              <LogIn className="mr-1 h-3 w-3" />
              {t("hospitality.checkIn")}
            </Button>
          ) : room.status === "occupied" ? (
            <Button
              size="sm"
              variant="outline"
              className="w-full"
              onClick={() => onCheckOut(room)}
            >
              <LogOut className="mr-1 h-3 w-3" />
              {t("hospitality.checkOut")}
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function HospitalityPage() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [createOpen, setCreateOpen] = useState(false)
  const [checkInOpen, setCheckInOpen] = useState(false)
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null)
  const [guestName, setGuestName] = useState("")
  const [newRoom, setNewRoom] = useState<Partial<RoomCreate>>({ room_number: "" })

  const { data: rooms, isLoading, isError, error } = useRooms(
    statusFilter !== "all" ? statusFilter : undefined
  )
  const createMutation = useCreateRoom()
  const checkInMutation = useCheckIn()
  const checkOutMutation = useCheckOut()

  const handleCreate = () => {
    if (!newRoom.room_number) return
    createMutation.mutate(newRoom as RoomCreate, {
      onSuccess: () => {
        setCreateOpen(false)
        setNewRoom({ room_number: "" })
        toast.success(t("toast.created", { item: t("hospitality.room") }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleCheckIn = (room: Room) => {
    setSelectedRoom(room)
    setGuestName("")
    setCheckInOpen(true)
  }

  const confirmCheckIn = () => {
    if (!selectedRoom || !guestName) return
    checkInMutation.mutate(
      { roomId: selectedRoom.id, guestName },
      {
        onSuccess: () => {
          setCheckInOpen(false)
          setSelectedRoom(null)
          toast.success(t("hospitality.checkedIn"))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleCheckOut = (room: Room) => {
    checkOutMutation.mutate(room.id, {
      onSuccess: () => toast.success(t("hospitality.checkedOut")),
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("hospitality.title")}
        description={t("hospitality.description")}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: t("hospitality.title") },
        ]}
      >
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> {t("hospitality.createRoom")}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error?.message || t("common.unknownError")}
        </div>
      )}

      {/* Status filter */}
      <div className="flex items-center gap-2">
        <Label>{t("hospitality.filterStatus")}:</Label>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("common.all")}</SelectItem>
            <SelectItem value="vacant">{t("hospitality.vacant")}</SelectItem>
            <SelectItem value="occupied">{t("hospitality.occupied")}</SelectItem>
            <SelectItem value="checkout">{t("hospitality.checkout")}</SelectItem>
            <SelectItem value="maintenance">{t("hospitality.maintenance")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Room grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : !rooms?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Hotel className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">{t("hospitality.noRooms")}</p>
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="mr-2 h-4 w-4" /> {t("hospitality.createRoom")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {rooms.map((room) => (
            <RoomCard
              key={room.id}
              room={room}
              onCheckIn={handleCheckIn}
              onCheckOut={handleCheckOut}
            />
          ))}
        </div>
      )}

      {/* Create room dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("hospitality.createRoom")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>{t("hospitality.roomNumber")}</Label>
              <Input
                value={newRoom.room_number ?? ""}
                onChange={(e) =>
                  setNewRoom({ ...newRoom, room_number: e.target.value })
                }
                placeholder="101"
              />
            </div>
            <div>
              <Label>{t("hospitality.roomType")}</Label>
              <Input
                value={newRoom.room_type ?? ""}
                onChange={(e) =>
                  setNewRoom({ ...newRoom, room_type: e.target.value })
                }
                placeholder="Suite"
              />
            </div>
            <div>
              <Label>{t("hospitality.floor")}</Label>
              <Input
                value={newRoom.floor ?? ""}
                onChange={(e) =>
                  setNewRoom({ ...newRoom, floor: e.target.value })
                }
                placeholder="1"
              />
            </div>
            <Button
              onClick={handleCreate}
              disabled={createMutation.isPending || !newRoom.room_number}
              className="w-full"
            >
              {createMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t("common.create")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Check-in dialog */}
      <Dialog open={checkInOpen} onOpenChange={setCheckInOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("hospitality.checkIn")} - {selectedRoom?.room_number}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>{t("hospitality.guestName")}</Label>
              <Input
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                placeholder={t("hospitality.guestNamePlaceholder")}
              />
            </div>
            <Button
              onClick={confirmCheckIn}
              disabled={checkInMutation.isPending || !guestName}
              className="w-full"
            >
              {checkInMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t("hospitality.confirmCheckIn")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
