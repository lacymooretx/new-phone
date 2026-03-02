import { useState } from "react"
import { useTranslation } from "react-i18next"
import i18next from "i18next"
import {
  useSMSProviders,
  useCreateSMSProvider,
  useUpdateSMSProvider,
  useDeleteSMSProvider,
  type SMSProviderConfig,
  type SMSProviderConfigCreate,
} from "@/api/sms"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Cable, MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import type { ColumnDef } from "@tanstack/react-table"

function getProviderColumns(actions: {
  onEdit: (c: SMSProviderConfig) => void
  onDelete: (c: SMSProviderConfig) => void
}): ColumnDef<SMSProviderConfig>[] {
  return [
    {
      accessorKey: "provider_type",
      header: i18next.t('smsProviders.col.provider'),
      cell: ({ row }) => (
        <span className="capitalize font-medium">{row.original.provider_type}</span>
      ),
    },
    {
      accessorKey: "label",
      header: i18next.t('smsProviders.col.label', { defaultValue: 'Label' }),
    },
    {
      accessorKey: "is_default",
      header: i18next.t('smsProviders.col.default', { defaultValue: 'Default' }),
      cell: ({ row }) =>
        row.original.is_default ? (
          <Badge variant="default" className="text-xs">{i18next.t('smsProviders.col.default', { defaultValue: 'Default' })}</Badge>
        ) : null,
    },
    {
      accessorKey: "is_active",
      header: i18next.t('smsProviders.col.status'),
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "outline" : "secondary"}>
          {row.original.is_active ? i18next.t('common.active') : i18next.t('common.inactive')}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: i18next.t('smsProviders.col.created', { defaultValue: 'Created' }),
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions.onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => actions.onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}

interface ProviderFormData {
  provider_type: "clearlyip" | "twilio"
  label: string
  is_default: boolean
  notes: string
  // ClearlyIP
  trunk_token: string
  // Twilio
  account_sid: string
  auth_token: string
}

const INITIAL_FORM: ProviderFormData = {
  provider_type: "clearlyip",
  label: "",
  is_default: false,
  notes: "",
  trunk_token: "",
  account_sid: "",
  auth_token: "",
}

function ProviderForm({
  initial,
  isLoading,
  onSubmit,
}: {
  initial: ProviderFormData
  isLoading: boolean
  onSubmit: (data: ProviderFormData) => void
}) {
  const { t } = useTranslation()
  const [form, setForm] = useState(initial)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label>{t('smsProviders.form.provider')}</Label>
        <Select
          value={form.provider_type}
          onValueChange={(val) => setForm({ ...form, provider_type: val as "clearlyip" | "twilio" })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="clearlyip">{t('smsProviders.form.clearlyIP')}</SelectItem>
            <SelectItem value="twilio">{t('smsProviders.form.twilio')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>{t('smsProviders.form.label', { defaultValue: 'Label' })}</Label>
        <Input
          value={form.label}
          onChange={(e) => setForm({ ...form, label: e.target.value })}
          placeholder={t('smsProviders.form.labelPlaceholder', { defaultValue: 'e.g., ClearlyIP Production' })}
          required
        />
      </div>

      {form.provider_type === "clearlyip" ? (
        <div className="space-y-2">
          <Label>{t('smsProviders.form.trunkToken', { defaultValue: 'Trunk Token' })}</Label>
          <Input
            value={form.trunk_token}
            onChange={(e) => setForm({ ...form, trunk_token: e.target.value })}
            placeholder={t('smsProviders.form.trunkTokenPlaceholder', { defaultValue: 'Enter ClearlyIP trunk token' })}
            type="password"
          />
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <Label>{t('smsProviders.form.accountSid')}</Label>
            <Input
              value={form.account_sid}
              onChange={(e) => setForm({ ...form, account_sid: e.target.value })}
              placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            />
          </div>
          <div className="space-y-2">
            <Label>{t('smsProviders.form.authToken')}</Label>
            <Input
              value={form.auth_token}
              onChange={(e) => setForm({ ...form, auth_token: e.target.value })}
              placeholder={t('smsProviders.form.authTokenPlaceholder', { defaultValue: 'Enter Twilio auth token' })}
              type="password"
            />
          </div>
        </>
      )}

      <div className="flex items-center gap-2">
        <Switch
          checked={form.is_default}
          onCheckedChange={(checked) => setForm({ ...form, is_default: checked })}
        />
        <Label>{t('smsProviders.form.setDefault', { defaultValue: 'Set as default provider' })}</Label>
      </div>

      <div className="space-y-2">
        <Label>{t('common.notes')}</Label>
        <Textarea
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          placeholder={t('smsProviders.form.notesPlaceholder', { defaultValue: 'Optional notes...' })}
          rows={2}
        />
      </div>

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading ? t('common.saving') : t('common.save')}
      </Button>
    </form>
  )
}

export function SMSProvidersPage() {
  const { t } = useTranslation()
  const { data: providers, isLoading, isError, error } = useSMSProviders()
  const createMutation = useCreateSMSProvider()
  const updateMutation = useUpdateSMSProvider()
  const deleteMutation = useDeleteSMSProvider()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<SMSProviderConfig | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<SMSProviderConfig | null>(null)

  const buildCredentials = (form: ProviderFormData): Record<string, string> => {
    if (form.provider_type === "clearlyip") {
      return { trunk_token: form.trunk_token }
    }
    return { account_sid: form.account_sid, auth_token: form.auth_token }
  }

  const handleSubmit = (form: ProviderFormData) => {
    const payload: SMSProviderConfigCreate = {
      provider_type: form.provider_type,
      label: form.label,
      credentials: buildCredentials(form),
      is_default: form.is_default,
      notes: form.notes || undefined,
    }

    if (editing) {
      updateMutation.mutate(
        { id: editing.id, ...payload },
        {
          onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('smsProviders.title') })) },
          onError: (err) => toast.error(err.message),
        },
      )
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('smsProviders.title') })) },
        onError: (err) => toast.error(err.message),
      })
    }
  }

  const handleDelete = () => {
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('smsProviders.deactivated', { defaultValue: 'Provider deactivated' })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const editFormData = editing
    ? {
        provider_type: editing.provider_type as "clearlyip" | "twilio",
        label: editing.label,
        is_default: editing.is_default,
        notes: editing.notes || "",
        trunk_token: "",
        account_sid: "",
        auth_token: "",
      }
    : INITIAL_FORM

  const columns = getProviderColumns({
    onEdit: (c) => { setEditing(c); setDialogOpen(true) },
    onDelete: (c) => { setDeleting(c); setConfirmOpen(true) },
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('smsProviders.title')} description={t('smsProviders.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "SMS" }, { label: "Providers" }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('smsProviders.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={providers ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('smsProviders.searchPlaceholder')}
        emptyState={
          <EmptyState
            icon={Cable}
            title={t('smsProviders.emptyTitle')}
            description={t('smsProviders.emptyDescription')}
            actionLabel={t('smsProviders.create')}
            onAction={() => { setEditing(null); setDialogOpen(true) }}
          />
        }
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('smsProviders.edit') : t('smsProviders.create')}</DialogTitle>
          </DialogHeader>
          <ProviderForm
            initial={editFormData}
            isLoading={createMutation.isPending || updateMutation.isPending}
            onSubmit={handleSubmit}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('smsProviders.deactivateTitle', { defaultValue: 'Deactivate Provider' })}
        description={t('smsProviders.deactivateConfirm', { defaultValue: 'Are you sure you want to deactivate "{{name}}"? This will stop SMS sending through this provider.', name: deleting?.label })}
        confirmLabel={t('smsProviders.deactivateButton', { defaultValue: 'Deactivate' })}
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  )
}
