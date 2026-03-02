import { useTranslation } from "react-i18next"
import { Plus, Upload, Trash2, Pencil, ChevronDown, ChevronRight, MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  useDNCEntries,
  type DNCList,
} from "@/api/compliance"

interface DNCListRowProps {
  list: DNCList
  isExpanded: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onBulkUpload: () => void
  addEntryPhone: string
  addEntryReason: string
  onAddEntryPhoneChange: (v: string) => void
  onAddEntryReasonChange: (v: string) => void
  onAddEntry: () => void
  isAddingEntry: boolean
  entryPage: number
  onPageChange: (p: number) => void
  onRemoveEntry: (id: string) => void
}

export function DNCListRow({
  list,
  isExpanded,
  onToggle,
  onEdit,
  onDelete,
  onBulkUpload,
  addEntryPhone,
  addEntryReason,
  onAddEntryPhoneChange,
  onAddEntryReasonChange,
  onAddEntry,
  isAddingEntry,
  entryPage,
  onPageChange,
  onRemoveEntry,
}: DNCListRowProps) {
  const { t } = useTranslation()
  const { data: entriesData } = useDNCEntries(isExpanded ? list.id : "", entryPage)

  return (
    <>
      <TableRow className="cursor-pointer" onClick={onToggle}>
        <TableCell>
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </TableCell>
        <TableCell className="font-medium">{list.name}</TableCell>
        <TableCell>
          <Badge variant="outline">{list.list_type}</Badge>
        </TableCell>
        <TableCell>{list.entry_count}</TableCell>
        <TableCell>
          {list.last_refreshed_at
            ? new Date(list.last_refreshed_at).toLocaleDateString()
            : "-"}
        </TableCell>
        <TableCell onClick={(e) => e.stopPropagation()}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>
                <Pencil className="mr-2 h-4 w-4" />
                {t("common.edit")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onBulkUpload}>
                <Upload className="mr-2 h-4 w-4" />
                {t("compliance.dnc.bulkUpload")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                {t("common.delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </TableCell>
      </TableRow>
      {isExpanded && (
        <TableRow>
          <TableCell colSpan={6} className="bg-muted/50 p-4">
            {/* Add entry inline */}
            <div className="flex items-end gap-2 mb-4">
              <div className="space-y-1">
                <Label className="text-xs">{t("compliance.dnc.phoneNumber")}</Label>
                <Input
                  value={addEntryPhone}
                  onChange={(e) => onAddEntryPhoneChange(e.target.value)}
                  placeholder="+15551234567"
                  className="w-48"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("compliance.dnc.reason")}</Label>
                <Input
                  value={addEntryReason}
                  onChange={(e) => onAddEntryReasonChange(e.target.value)}
                  placeholder={t("compliance.dnc.reasonPlaceholder")}
                  className="w-48"
                />
              </div>
              <Button size="sm" onClick={onAddEntry} disabled={!addEntryPhone.trim() || isAddingEntry}>
                <Plus className="mr-1 h-3 w-3" />
                {t("compliance.dnc.addEntry")}
              </Button>
            </div>

            {/* Entries table */}
            {entriesData && entriesData.items.length > 0 ? (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("compliance.dnc.phoneNumber")}</TableHead>
                      <TableHead>{t("compliance.dnc.reason")}</TableHead>
                      <TableHead>{t("compliance.dnc.source")}</TableHead>
                      <TableHead>{t("compliance.dnc.addedAt")}</TableHead>
                      <TableHead className="w-12" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entriesData.items.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="font-mono">{entry.phone_number}</TableCell>
                        <TableCell>{entry.reason || "-"}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{entry.source}</Badge>
                        </TableCell>
                        <TableCell>{new Date(entry.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => onRemoveEntry(entry.id)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {/* Pagination */}
                {entriesData.total > entriesData.per_page && (
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-muted-foreground">
                      {t("compliance.pagination", {
                        from: (entryPage - 1) * entriesData.per_page + 1,
                        to: Math.min(entryPage * entriesData.per_page, entriesData.total),
                        total: entriesData.total,
                      })}
                    </span>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={entryPage <= 1}
                        onClick={() => onPageChange(entryPage - 1)}
                      >
                        {t("compliance.prev")}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={entryPage * entriesData.per_page >= entriesData.total}
                        onClick={() => onPageChange(entryPage + 1)}
                      >
                        {t("compliance.next")}
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t("compliance.dnc.noEntries")}</p>
            )}
          </TableCell>
        </TableRow>
      )}
    </>
  )
}
