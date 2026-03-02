import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, Search, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { DNCListForm } from "./dnc-list-form"
import { DNCCheckDialog } from "./dnc-check-dialog"
import { DNCBulkUploadDialog } from "./dnc-bulk-upload-dialog"
import { DNCListRow } from "./dnc-list-row"
import {
  useDNCLists,
  useCreateDNCList,
  useUpdateDNCList,
  useDeleteDNCList,
  useAddDNCEntry,
  useBulkAddDNCEntries,
  useRemoveDNCEntry,
  useCheckNumber,
  useSyncSmsOptouts,
  type DNCList,
  type DNCCheckResult,
} from "@/api/compliance"

export function DNCListsPage() {
  const { t } = useTranslation()
  const { data: lists, isLoading } = useDNCLists()
  const createList = useCreateDNCList()
  const updateList = useUpdateDNCList()
  const deleteList = useDeleteDNCList()
  const addEntry = useAddDNCEntry()
  const bulkAdd = useBulkAddDNCEntries()
  const removeEntry = useRemoveDNCEntry()
  const checkNumber = useCheckNumber()
  const syncOptouts = useSyncSmsOptouts()

  const [formOpen, setFormOpen] = useState(false)
  const [editingList, setEditingList] = useState<DNCList | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deletingList, setDeletingList] = useState<DNCList | null>(null)
  const [expandedListId, setExpandedListId] = useState<string | null>(null)
  const [addEntryListId, setAddEntryListId] = useState<string | null>(null)
  const [addEntryPhone, setAddEntryPhone] = useState("")
  const [addEntryReason, setAddEntryReason] = useState("")
  const [bulkDialogListId, setBulkDialogListId] = useState<string | null>(null)
  const [bulkText, setBulkText] = useState("")
  const [checkDialogOpen, setCheckDialogOpen] = useState(false)
  const [checkPhone, setCheckPhone] = useState("")
  const [checkResult, setCheckResult] = useState<DNCCheckResult | null>(null)
  const [entryPage, setEntryPage] = useState(1)

  const handleCreateList = (data: Parameters<typeof createList.mutate>[0]) => {
    createList.mutate(data, {
      onSuccess: () => {
        setFormOpen(false)
        toast.success(t("compliance.dnc.listCreated"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdateList = (data: Parameters<typeof createList.mutate>[0]) => {
    if (!editingList) return
    updateList.mutate(
      { id: editingList.id, ...data },
      {
        onSuccess: () => {
          setEditingList(null)
          toast.success(t("compliance.dnc.listUpdated"))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleDeleteList = () => {
    if (!deletingList) return
    deleteList.mutate(deletingList.id, {
      onSuccess: () => {
        setDeleteConfirmOpen(false)
        setDeletingList(null)
        toast.success(t("compliance.dnc.listDeleted"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleAddEntry = () => {
    if (!addEntryListId || !addEntryPhone.trim()) return
    addEntry.mutate(
      { listId: addEntryListId, phone_number: addEntryPhone.trim(), reason: addEntryReason || undefined },
      {
        onSuccess: () => {
          setAddEntryPhone("")
          setAddEntryReason("")
          toast.success(t("compliance.dnc.entryAdded"))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleBulkUpload = () => {
    if (!bulkDialogListId || !bulkText.trim()) return
    const phoneNumbers = bulkText
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (phoneNumbers.length === 0) return
    if (phoneNumbers.length > 10000) {
      toast.error(t("compliance.dnc.bulkLimit"))
      return
    }
    bulkAdd.mutate(
      { listId: bulkDialogListId, phone_numbers: phoneNumbers },
      {
        onSuccess: (result) => {
          setBulkDialogListId(null)
          setBulkText("")
          toast.success(
            t("compliance.dnc.bulkResult", { added: result.added, skipped: result.skipped })
          )
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleCheckNumber = () => {
    if (!checkPhone.trim()) return
    checkNumber.mutate(checkPhone.trim(), {
      onSuccess: (result) => setCheckResult(result),
      onError: (err) => toast.error(err.message),
    })
  }

  const handleSyncOptouts = () => {
    syncOptouts.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(
          t("compliance.dnc.syncResult", { added: result.added, skipped: result.skipped })
        )
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("compliance.dnc.title")}
        description={t("compliance.dnc.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance", href: "/compliance/dnc-lists" }, { label: t("compliance.dnc.title") }]}
      >
        <Button variant="outline" onClick={() => { setCheckDialogOpen(true); setCheckResult(null); setCheckPhone("") }}>
          <Search className="mr-2 h-4 w-4" />
          {t("compliance.dnc.checkNumber")}
        </Button>
        <Button variant="outline" onClick={handleSyncOptouts} disabled={syncOptouts.isPending}>
          <RefreshCw className={`mr-2 h-4 w-4 ${syncOptouts.isPending ? "animate-spin" : ""}`} />
          {t("compliance.dnc.syncOptouts")}
        </Button>
        <Button onClick={() => setFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("compliance.dnc.createList")}
        </Button>
      </PageHeader>

      {isLoading && <div className="text-muted-foreground">{t("common.loading")}</div>}

      {lists && lists.length === 0 && (
        <Card className="p-8 text-center text-muted-foreground">
          {t("compliance.dnc.emptyTitle")}
        </Card>
      )}

      {lists && lists.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>{t("compliance.dnc.form.name")}</TableHead>
                <TableHead>{t("compliance.dnc.form.listType")}</TableHead>
                <TableHead>{t("compliance.dnc.entryCount")}</TableHead>
                <TableHead>{t("compliance.dnc.lastRefreshed")}</TableHead>
                <TableHead>{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lists.map((list) => (
                <DNCListRow
                  key={list.id}
                  list={list}
                  isExpanded={expandedListId === list.id}
                  onToggle={() => {
                    setExpandedListId(expandedListId === list.id ? null : list.id)
                    setEntryPage(1)
                    setAddEntryListId(expandedListId === list.id ? null : list.id)
                  }}
                  onEdit={() => setEditingList(list)}
                  onDelete={() => { setDeletingList(list); setDeleteConfirmOpen(true) }}
                  onBulkUpload={() => { setBulkDialogListId(list.id); setBulkText("") }}
                  addEntryPhone={addEntryListId === list.id ? addEntryPhone : ""}
                  addEntryReason={addEntryListId === list.id ? addEntryReason : ""}
                  onAddEntryPhoneChange={setAddEntryPhone}
                  onAddEntryReasonChange={setAddEntryReason}
                  onAddEntry={handleAddEntry}
                  isAddingEntry={addEntry.isPending}
                  entryPage={entryPage}
                  onPageChange={setEntryPage}
                  onRemoveEntry={(entryId) => {
                    removeEntry.mutate(
                      { listId: list.id, entryId },
                      { onSuccess: () => toast.success(t("compliance.dnc.entryRemoved")) }
                    )
                  }}
                />
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Create/Edit dialog */}
      <DNCListForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleCreateList}
        isPending={createList.isPending}
      />
      {editingList && (
        <DNCListForm
          open={!!editingList}
          onOpenChange={() => setEditingList(null)}
          onSubmit={handleUpdateList}
          initialData={editingList}
          isPending={updateList.isPending}
        />
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title={t("compliance.dnc.deleteTitle")}
        description={t("compliance.dnc.deleteConfirm", { name: deletingList?.name })}
        confirmLabel={t("common.delete")}
        variant="destructive"
        onConfirm={handleDeleteList}
      />

      {/* Bulk upload dialog */}
      <DNCBulkUploadDialog
        open={!!bulkDialogListId}
        onOpenChange={() => setBulkDialogListId(null)}
        bulkText={bulkText}
        onBulkTextChange={setBulkText}
        onUpload={handleBulkUpload}
        isUploading={bulkAdd.isPending}
      />

      {/* Check number dialog */}
      <DNCCheckDialog
        open={checkDialogOpen}
        onOpenChange={setCheckDialogOpen}
        checkPhone={checkPhone}
        onCheckPhoneChange={setCheckPhone}
        onCheck={handleCheckNumber}
        isChecking={checkNumber.isPending}
        checkResult={checkResult}
      />
    </div>
  )
}
