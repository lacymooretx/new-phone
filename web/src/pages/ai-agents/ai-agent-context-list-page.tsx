import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import {
  useAIAgentContexts,
  useDeleteAIAgentContext,
  type AIAgentContext,
} from "@/api/ai-agents"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
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
import { Input } from "@/components/ui/input"
import { Plus, Bot, MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"

export function AIAgentContextListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: contexts, isLoading, isError, error } = useAIAgentContexts()
  const deleteMutation = useDeleteAIAgentContext()

  const [searchQuery, setSearchQuery] = useState("")
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<AIAgentContext | null>(null)

  const handleDelete = (context: AIAgentContext) => {
    setDeleting(context)
    setConfirmOpen(true)
  }

  const confirmDelete = () => {
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeleting(null)
        toast.success(t("toast.deleted", { item: t("aiAgents.contexts.title") }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const filtered = (contexts ?? []).filter(
    (ctx) =>
      ctx.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ctx.display_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiAgents.contexts.title")}
        description={t("aiAgents.contexts.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.contexts.title") }]}
      >
        <Button onClick={() => navigate("/ai-agents/contexts/new")}>
          <Plus className="mr-2 h-4 w-4" /> {t("aiAgents.contexts.create")}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", { message: error?.message || t("common.unknownError") })}
        </div>
      )}

      <div className="flex items-center gap-4">
        <Input
          placeholder={t("aiAgents.contexts.searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Bot}
          title={t("aiAgents.contexts.emptyTitle")}
          description={t("aiAgents.contexts.emptyDescription")}
          actionLabel={t("aiAgents.contexts.create")}
          onAction={() => navigate("/ai-agents/contexts/new")}
        />
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("aiAgents.contexts.colName")}</TableHead>
                <TableHead>{t("aiAgents.contexts.colDisplayName")}</TableHead>
                <TableHead>{t("aiAgents.contexts.colProviderMode")}</TableHead>
                <TableHead>{t("aiAgents.contexts.colLanguage")}</TableHead>
                <TableHead>{t("aiAgents.contexts.colActive")}</TableHead>
                <TableHead className="w-[80px]">{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((ctx) => (
                <TableRow key={ctx.id}>
                  <TableCell className="font-medium">{ctx.name}</TableCell>
                  <TableCell>{ctx.display_name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {ctx.provider_mode === "monolithic"
                        ? t("aiAgents.contexts.monolithic")
                        : t("aiAgents.contexts.pipeline")}
                    </Badge>
                  </TableCell>
                  <TableCell>{ctx.language}</TableCell>
                  <TableCell>
                    <Badge variant={ctx.is_active ? "default" : "secondary"}>
                      {ctx.is_active ? t("common.active") : t("common.inactive")}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/ai-agents/contexts/${ctx.id}/edit`)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          {t("common.edit")}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDelete(ctx)} className="text-destructive">
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t("common.delete")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("aiAgents.contexts.deleteTitle")}
        description={t("aiAgents.contexts.deleteConfirm", { name: deleting?.display_name })}
        confirmLabel={t("common.delete")}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
