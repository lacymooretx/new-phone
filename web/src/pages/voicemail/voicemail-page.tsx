import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useVoicemailBoxes,
  useVoicemailMessages,
  useMarkMessageRead,
  useDeleteVoicemailMessage,
  useCreateVoicemailBox,
  useUpdateVoicemailBox,
  useDeleteVoicemailBox,
  useResetVoicemailPin,
  type VoicemailBox,
} from "@/api/voicemail"
import { VoicemailBoxForm } from "./voicemail-box-form"
import { PageHeader } from "@/components/shared/page-header"
import { AudioPlayer } from "@/components/shared/audio-player"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Voicemail, Mail, MailOpen, Trash2, Plus, Pencil, KeyRound } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

export function VoicemailPage() {
  const { t } = useTranslation()
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const { data: boxes, isLoading: boxesLoading } = useVoicemailBoxes()
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null)
  const { data: messages, isLoading: msgsLoading } = useVoicemailMessages(selectedBoxId)
  const markRead = useMarkMessageRead()
  const deleteMsg = useDeleteVoicemailMessage()
  const createBox = useCreateVoicemailBox()
  const updateBox = useUpdateVoicemailBox()
  const deleteBox = useDeleteVoicemailBox()
  const resetPin = useResetVoicemailPin()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingBox, setEditingBox] = useState<VoicemailBox | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deletingBox, setDeletingBox] = useState<VoicemailBox | null>(null)
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false)
  const [resettingBox, setResettingBox] = useState<VoicemailBox | null>(null)
  const [deleteMsgConfirmOpen, setDeleteMsgConfirmOpen] = useState(false)
  const [deletingMsg, setDeletingMsg] = useState<{ boxId: string; messageId: string } | null>(null)

  const handleCreateBox = (data: any) => {
    createBox.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('voicemail.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdateBox = (data: any) => {
    if (!editingBox) return
    updateBox.mutate({ id: editingBox.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditingBox(null); toast.success(t('toast.updated', { item: t('voicemail.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDeleteBox = (box: VoicemailBox) => {
    setDeletingBox(box)
    setDeleteConfirmOpen(true)
  }

  const confirmDeleteBox = () => {
    if (!deletingBox) return
    deleteBox.mutate(deletingBox.id, {
      onSuccess: () => {
        if (selectedBoxId === deletingBox.id) setSelectedBoxId(null)
        setDeleteConfirmOpen(false)
        setDeletingBox(null)
        toast.success(t('toast.deleted', { item: t('voicemail.title') }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleResetPin = (box: VoicemailBox) => {
    setResettingBox(box)
    setResetConfirmOpen(true)
  }

  const confirmResetPin = () => {
    if (!resettingBox) return
    resetPin.mutate(resettingBox.id, {
      onSuccess: (data) => {
        setResetConfirmOpen(false)
        setResettingBox(null)
        toast.success(t('voicemail.pinReset', { defaultValue: 'PIN reset. New PIN: {{pin}}', pin: data.pin }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  if (boxesLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('voicemail.title')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('voicemail.title') }]} />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('voicemail.title')} description={t('voicemail.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('voicemail.title') }]}>
        <Button onClick={() => { setEditingBox(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('voicemail.create')}
        </Button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Box list */}
        <div className="space-y-2">
          {boxes?.map((box) => (
            <Card
              key={box.id}
              className={cn(
                "cursor-pointer transition-colors hover:bg-accent",
                selectedBoxId === box.id && "border-primary"
              )}
              onClick={() => setSelectedBoxId(box.id)}
            >
              <CardHeader className="p-4">
                <CardTitle className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <Voicemail className="h-4 w-4" />
                    Box {box.mailbox_number}
                  </span>
                  <span className="flex items-center gap-1">
                    {!box.is_active && <Badge variant="secondary">{t('common.inactive')}</Badge>}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); handleResetPin(box) }}
                      title={t('voicemail.resetPin', { defaultValue: 'Reset PIN' })}
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); setEditingBox(box); setDialogOpen(true) }}
                      title={t('common.edit')}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); handleDeleteBox(box) }}
                      title={t('common.delete')}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </span>
                </CardTitle>
              </CardHeader>
            </Card>
          ))}
          {boxes?.length === 0 && (
            <p className="text-sm text-muted-foreground p-4">{t('voicemail.emptyTitle')}</p>
          )}
        </div>

        {/* Messages */}
        <div>
          {!selectedBoxId && (
            <div className="flex h-40 items-center justify-center text-muted-foreground">
              {t('voicemail.selectBox', { defaultValue: 'Select a voicemail box to view messages' })}
            </div>
          )}

          {selectedBoxId && msgsLoading && (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16" />)}
            </div>
          )}

          {selectedBoxId && messages && (
            <div className="space-y-2">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground p-4">{t('voicemail.noMessages', { defaultValue: 'No messages.' })}</p>
              )}
              {messages.map((msg) => (
                <Card key={msg.id} className={cn(!msg.is_read && "border-primary/50 bg-primary/5")}>
                  <CardContent className="flex items-center gap-4 p-4">
                    {msg.is_read ? (
                      <MailOpen className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <Mail className="h-5 w-5 text-primary" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{msg.caller_name || msg.caller_number}</span>
                        {msg.is_urgent && <Badge variant="destructive">{t('voicemail.urgent', { defaultValue: 'Urgent' })}</Badge>}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(msg.created_at).toLocaleString()} &middot; {msg.duration_seconds}s
                      </div>
                    </div>
                    <AudioPlayer
                      fetchUrl={() =>
                        apiClient.get(`tenants/${tenantId}/voicemail-boxes/${selectedBoxId}/messages/${msg.id}/playback`)
                      }
                    />
                    {!msg.is_read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          markRead.mutate(
                            { boxId: selectedBoxId!, messageId: msg.id },
                            { onError: (err) => toast.error(err.message) }
                          )
                        }}
                      >
                        {t('voicemail.markRead', { defaultValue: 'Mark Read' })}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setDeletingMsg({ boxId: selectedBoxId!, messageId: msg.id })
                        setDeleteMsgConfirmOpen(true)
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingBox ? t('voicemail.edit') : t('voicemail.create')}</DialogTitle>
          </DialogHeader>
          <VoicemailBoxForm
            box={editingBox}
            onSubmit={editingBox ? handleUpdateBox : handleCreateBox}
            isLoading={createBox.isPending || updateBox.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title={t('voicemail.deleteTitle')}
        description={t('voicemail.deleteConfirm', { number: deletingBox?.mailbox_number })}
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDeleteBox}
      />

      <ConfirmDialog
        open={resetConfirmOpen}
        onOpenChange={setResetConfirmOpen}
        title={t('voicemail.resetPinTitle', { defaultValue: 'Reset Voicemail PIN' })}
        description={t('voicemail.resetPinConfirm', { defaultValue: 'Are you sure you want to reset the PIN for voicemail box {{number}}? A new PIN will be generated.', number: resettingBox?.mailbox_number })}
        confirmLabel={t('voicemail.resetPinButton', { defaultValue: 'Reset PIN' })}
        onConfirm={confirmResetPin}
      />

      <ConfirmDialog
        open={deleteMsgConfirmOpen}
        onOpenChange={setDeleteMsgConfirmOpen}
        title={t('voicemail.deleteMsgTitle', { defaultValue: 'Delete Voicemail Message' })}
        description={t('voicemail.deleteMsgConfirm', { defaultValue: 'Are you sure you want to delete this voicemail message? This action cannot be undone.' })}
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={() => {
          if (!deletingMsg) return
          deleteMsg.mutate(deletingMsg, {
            onSuccess: () => { setDeleteMsgConfirmOpen(false); setDeletingMsg(null); toast.success(t('voicemail.messageDeleted', { defaultValue: 'Message deleted' })) },
            onError: (err) => toast.error(err.message),
          })
        }}
      />
    </div>
  )
}
