import { useState, useRef } from "react"
import { useTranslation } from "react-i18next"
import { useAudioPrompts, useUploadAudioPrompt, useDeleteAudioPrompt, type AudioPrompt } from "@/api/audio-prompts"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getAudioPromptColumns } from "./audio-prompt-columns"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, Music } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function AudioPromptsPage() {
  const { t } = useTranslation()
  const { data: prompts, isLoading, isError, error } = useAudioPrompts()
  const uploadMutation = useUploadAudioPrompt()
  const deleteMutation = useDeleteAudioPrompt()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<AudioPrompt | null>(null)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState("general")
  const fileRef = useRef<HTMLInputElement>(null)

  useBeforeUnload(dialogOpen)

  const handleExport = (data: AudioPrompt[]) => {
    exportToCsv(data, [
      { key: "name", label: t('audioPrompts.col.name') },
      { key: "category", label: t('common.type') },
      { key: "format", label: t('common.type') },
    ], "audio-prompts")
  }

  const handleDelete = (prompt: AudioPrompt) => {
    setDeleting(prompt)
    setConfirmOpen(true)
  }

  const confirmDelete = () => {
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('audioPrompts.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpload = () => {
    const file = fileRef.current?.files?.[0]
    if (!file) {
      toast.error(t('common.required'))
      return
    }
    if (!name.trim()) {
      toast.error(t('common.required'))
      return
    }

    const formData = new FormData()
    formData.append("name", name.trim())
    if (description.trim()) formData.append("description", description.trim())
    formData.append("category", category)
    formData.append("file", file)

    uploadMutation.mutate(formData, {
      onSuccess: () => {
        setDialogOpen(false)
        setName("")
        setDescription("")
        setCategory("general")
        if (fileRef.current) fileRef.current.value = ""
        toast.success(t('toast.created', { item: t('audioPrompts.title') }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getAudioPromptColumns({
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('audioPrompts.title')} description={t('audioPrompts.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('audioPrompts.title') }]}>
        <Button onClick={() => setDialogOpen(true)}>
          <Upload className="mr-2 h-4 w-4" /> {t('audioPrompts.upload')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('audioPrompts.searchPlaceholder')}
        data={prompts ?? []}
        isLoading={isLoading}
        onExport={handleExport}
        emptyState={<EmptyState icon={Music} title={t('audioPrompts.emptyTitle')} description={t('audioPrompts.emptyDescription')} actionLabel={t('audioPrompts.upload')} onAction={() => setDialogOpen(true)} />}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{t('audioPrompts.upload')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="prompt-name">{t('common.name')} *</Label>
              <Input
                id="prompt-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Main IVR Greeting"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="prompt-description">{t('common.description')}</Label>
              <Textarea
                id="prompt-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="ivr_greeting">IVR Greeting</SelectItem>
                  <SelectItem value="voicemail_greeting">Voicemail Greeting</SelectItem>
                  <SelectItem value="moh">Music on Hold</SelectItem>
                  <SelectItem value="announcement">Announcement</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="prompt-file">Audio File *</Label>
              <Input
                id="prompt-file"
                type="file"
                accept="audio/*"
                ref={fileRef}
              />
            </div>
            <Button onClick={handleUpload} disabled={uploadMutation.isPending} className="w-full">
              {uploadMutation.isPending ? t('common.saving') : t('audioPrompts.upload')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('audioPrompts.deleteTitle')}
        description={t('audioPrompts.deleteConfirm', { name: deleting?.name })}
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
