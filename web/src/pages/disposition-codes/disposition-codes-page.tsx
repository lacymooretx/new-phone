import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useDispositionCodeLists,
  useCreateCodeList,
  useUpdateCodeList,
  useDeleteCodeList,
  useCreateCode,
  useUpdateCode,
  useDeleteCode,
  type DispositionCodeList,
  type DispositionCode,
  type DispositionCodeListCreate,
  type DispositionCodeCreate,
} from "@/api/disposition-codes"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { CodeListForm } from "./code-list-form"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Plus,
  Tag,
  MoreHorizontal,
  Pencil,
  Trash2,
  ChevronRight,
  ChevronDown,
} from "lucide-react"
import { toast } from "sonner"

export function DispositionCodesPage() {
  const { t } = useTranslation()
  const { data: lists, isLoading, isError, error } = useDispositionCodeLists()
  const createList = useCreateCodeList()
  const updateList = useUpdateCodeList()
  const deleteList = useDeleteCodeList()
  const createCode = useCreateCode()
  const updateCode = useUpdateCode()
  const deleteCode = useDeleteCode()

  // List dialog
  const [listDialogOpen, setListDialogOpen] = useState(false)
  const [editingList, setEditingList] = useState<DispositionCodeList | null>(null)

  // Code inline form
  const [addingCodeToListId, setAddingCodeToListId] = useState<string | null>(null)
  const [newCode, setNewCode] = useState({ code: "", label: "", category: "" })
  const [editingCode, setEditingCode] = useState<DispositionCode | null>(null)
  const [editCodeForm, setEditCodeForm] = useState({ code: "", label: "", category: "" })

  // Confirm
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ type: "list"; id: string } | { type: "code"; listId: string; codeId: string } | null>(null)

  // Expanded lists
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // List CRUD
  const handleCreateList = (data: DispositionCodeListCreate) => {
    createList.mutate(data, {
      onSuccess: () => {
        setListDialogOpen(false)
        toast.success(t('toast.created', { item: t('dispositionCodes.title') }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdateList = (data: DispositionCodeListCreate) => {
    if (!editingList) return
    updateList.mutate(
      { id: editingList.id, ...data },
      {
        onSuccess: () => {
          setListDialogOpen(false)
          setEditingList(null)
          toast.success(t('toast.updated', { item: t('dispositionCodes.title') }))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  // Code CRUD
  const handleAddCode = (listId: string) => {
    if (!newCode.code || !newCode.label) {
      toast.error(t('common.required'))
      return
    }
    const data: DispositionCodeCreate & { listId: string } = {
      listId,
      code: newCode.code,
      label: newCode.label,
      category: newCode.category || null,
    }
    createCode.mutate(data, {
      onSuccess: () => {
        setNewCode({ code: "", label: "", category: "" })
        setAddingCodeToListId(null)
        toast.success(t('toast.created', { item: t('dispositionCodes.form.codeLabel') }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdateCode = (listId: string) => {
    if (!editingCode) return
    updateCode.mutate(
      {
        listId,
        codeId: editingCode.id,
        code: editCodeForm.code || undefined,
        label: editCodeForm.label || undefined,
        category: editCodeForm.category || null,
      },
      {
        onSuccess: () => {
          setEditingCode(null)
          toast.success(t('toast.updated', { item: t('dispositionCodes.form.codeLabel') }))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleDeleteConfirm = () => {
    if (!deleteTarget) return
    if (deleteTarget.type === "list") {
      deleteList.mutate(deleteTarget.id, {
        onSuccess: () => {
          setConfirmOpen(false)
          setDeleteTarget(null)
          toast.success(t('toast.deleted', { item: t('dispositionCodes.title') }))
        },
        onError: (err) => toast.error(err.message),
      })
    } else {
      deleteCode.mutate(
        { listId: deleteTarget.listId, codeId: deleteTarget.codeId },
        {
          onSuccess: () => {
            setConfirmOpen(false)
            setDeleteTarget(null)
            toast.success(t('toast.deleted', { item: t('dispositionCodes.form.codeLabel') }))
          },
          onError: (err) => toast.error(err.message),
        }
      )
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('dispositionCodes.title')} description={t('dispositionCodes.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('dispositionCodes.title') }]}>
        <Button
          onClick={() => {
            setEditingList(null)
            setListDialogOpen(true)
          }}
        >
          <Plus className="mr-2 h-4 w-4" /> {t('dispositionCodes.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
          {t('common.loading')}
        </div>
      )}

      {!isLoading && (!lists || lists.length === 0) && (
        <EmptyState
          icon={Tag}
          title={t('dispositionCodes.emptyTitle')}
          description={t('dispositionCodes.emptyDescription')}
          actionLabel={t('dispositionCodes.create')}
          onAction={() => {
            setEditingList(null)
            setListDialogOpen(true)
          }}
        />
      )}

      {lists && lists.length > 0 && (
        <div className="space-y-3">
          {lists.map((codeList) => {
            const isExpanded = expanded.has(codeList.id)
            return (
              <div key={codeList.id} className="rounded-lg border">
                <div className="flex items-center justify-between p-4">
                  <button
                    className="flex items-center gap-2 text-left font-medium hover:underline"
                    onClick={() => toggleExpanded(codeList.id)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    {codeList.name}
                    <Badge variant="secondary" className="ml-2">
                      {codeList.codes.filter((c) => c.is_active).length} codes
                    </Badge>
                  </button>
                  <div className="flex items-center gap-2">
                    {codeList.description && (
                      <span className="text-sm text-muted-foreground mr-2">
                        {codeList.description}
                      </span>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => {
                            setEditingList(codeList)
                            setListDialogOpen(true)
                          }}
                        >
                          <Pencil className="mr-2 h-4 w-4" /> {t('dispositionCodes.edit')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            setDeleteTarget({ type: "list", id: codeList.id })
                            setConfirmOpen(true)
                          }}
                        >
                          <Trash2 className="mr-2 h-4 w-4" /> {t('common.delete')}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
                {isExpanded && (
                  <div className="border-t px-4 pb-4">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t('dispositionCodes.form.codeLabel')}</TableHead>
                          <TableHead>Label</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead className="w-20">Pos</TableHead>
                          <TableHead className="w-16"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {codeList.codes
                          .filter((c) => c.is_active)
                          .map((code) => (
                            <TableRow key={code.id}>
                              {editingCode?.id === code.id ? (
                                <>
                                  <TableCell>
                                    <Input
                                      value={editCodeForm.code}
                                      onChange={(e) =>
                                        setEditCodeForm((f) => ({ ...f, code: e.target.value }))
                                      }
                                      className="h-8"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      value={editCodeForm.label}
                                      onChange={(e) =>
                                        setEditCodeForm((f) => ({ ...f, label: e.target.value }))
                                      }
                                      className="h-8"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      value={editCodeForm.category}
                                      onChange={(e) =>
                                        setEditCodeForm((f) => ({ ...f, category: e.target.value }))
                                      }
                                      className="h-8"
                                    />
                                  </TableCell>
                                  <TableCell>{code.position}</TableCell>
                                  <TableCell>
                                    <div className="flex gap-1">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleUpdateCode(codeList.id)}
                                      >
                                        {t('common.save')}
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setEditingCode(null)}
                                      >
                                        {t('common.cancel')}
                                      </Button>
                                    </div>
                                  </TableCell>
                                </>
                              ) : (
                                <>
                                  <TableCell className="font-mono text-sm">{code.code}</TableCell>
                                  <TableCell>{code.label}</TableCell>
                                  <TableCell>
                                    {code.category ? (
                                      <Badge variant="outline">{code.category}</Badge>
                                    ) : (
                                      <span className="text-muted-foreground">-</span>
                                    )}
                                  </TableCell>
                                  <TableCell>{code.position}</TableCell>
                                  <TableCell>
                                    <DropdownMenu>
                                      <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                          <MoreHorizontal className="h-3 w-3" />
                                        </Button>
                                      </DropdownMenuTrigger>
                                      <DropdownMenuContent align="end">
                                        <DropdownMenuItem
                                          onClick={() => {
                                            setEditingCode(code)
                                            setEditCodeForm({
                                              code: code.code,
                                              label: code.label,
                                              category: code.category ?? "",
                                            })
                                          }}
                                        >
                                          <Pencil className="mr-2 h-4 w-4" /> {t('common.edit')}
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                          className="text-destructive"
                                          onClick={() => {
                                            setDeleteTarget({
                                              type: "code",
                                              listId: codeList.id,
                                              codeId: code.id,
                                            })
                                            setConfirmOpen(true)
                                          }}
                                        >
                                          <Trash2 className="mr-2 h-4 w-4" /> {t('common.delete')}
                                        </DropdownMenuItem>
                                      </DropdownMenuContent>
                                    </DropdownMenu>
                                  </TableCell>
                                </>
                              )}
                            </TableRow>
                          ))}
                        {/* Add code row */}
                        {addingCodeToListId === codeList.id ? (
                          <TableRow>
                            <TableCell>
                              <Input
                                placeholder="code_key"
                                value={newCode.code}
                                onChange={(e) =>
                                  setNewCode((f) => ({ ...f, code: e.target.value }))
                                }
                                className="h-8"
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                placeholder="Display Label"
                                value={newCode.label}
                                onChange={(e) =>
                                  setNewCode((f) => ({ ...f, label: e.target.value }))
                                }
                                className="h-8"
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                placeholder="Category"
                                value={newCode.category}
                                onChange={(e) =>
                                  setNewCode((f) => ({ ...f, category: e.target.value }))
                                }
                                className="h-8"
                              />
                            </TableCell>
                            <TableCell>-</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleAddCode(codeList.id)}
                                  disabled={createCode.isPending}
                                >
                                  {t('common.create')}
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setAddingCodeToListId(null)
                                    setNewCode({ code: "", label: "", category: "" })
                                  }}
                                >
                                  {t('common.cancel')}
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ) : (
                          <TableRow>
                            <TableCell colSpan={5}>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="w-full"
                                onClick={() => {
                                  setAddingCodeToListId(codeList.id)
                                  setNewCode({ code: "", label: "", category: "" })
                                }}
                              >
                                <Plus className="mr-1 h-3 w-3" /> {t('dispositionCodes.form.addCode')}
                              </Button>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* List dialog */}
      <Dialog
        open={listDialogOpen}
        onOpenChange={(open) => {
          if (!open) setEditingList(null)
          setListDialogOpen(open)
        }}
      >
        <DialogContent onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>
              {editingList ? t('dispositionCodes.edit') : t('dispositionCodes.create')}
            </DialogTitle>
          </DialogHeader>
          <CodeListForm
            codeList={editingList}
            onSubmit={editingList ? handleUpdateList : handleCreateList}
            isLoading={createList.isPending || updateList.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Confirm dialog */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={
          deleteTarget?.type === "list"
            ? t('dispositionCodes.deleteTitle')
            : t('dispositionCodes.deleteTitle')
        }
        description={
          deleteTarget?.type === "list"
            ? t('dispositionCodes.deleteConfirm', { name: '' })
            : t('dispositionCodes.deleteConfirm', { name: '' })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}
