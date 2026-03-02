import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogFooter,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import {
  useComplianceRules,
  useCreateComplianceRule,
  useUpdateComplianceRule,
  useDeleteComplianceRule,
  type ComplianceRule,
  type ComplianceRuleCreate,
} from "@/api/compliance-monitoring"

const CATEGORIES = [
  "greeting",
  "disclosure",
  "verification",
  "required_statement",
  "prohibited_language",
  "closing",
  "custom",
] as const

const SEVERITIES = ["critical", "major", "minor"] as const

const SCOPE_TYPES = ["all", "queue", "agent_context"] as const

function severityVariant(severity: string) {
  switch (severity) {
    case "critical":
      return "destructive"
    case "major":
      return "default"
    default:
      return "secondary"
  }
}

export function ComplianceRulesPage() {
  const { t } = useTranslation()
  const { data: rules, isLoading } = useComplianceRules()
  const createRule = useCreateComplianceRule()
  const updateRule = useUpdateComplianceRule()
  const deleteRule = useDeleteComplianceRule()

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ComplianceRule | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState<ComplianceRule | null>(null)

  // Form state
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [ruleText, setRuleText] = useState("")
  const [category, setCategory] = useState("custom")
  const [severity, setSeverity] = useState("major")
  const [scopeType, setScopeType] = useState("all")
  const [scopeId, setScopeId] = useState("")

  const resetForm = () => {
    setName("")
    setDescription("")
    setRuleText("")
    setCategory("custom")
    setSeverity("major")
    setScopeType("all")
    setScopeId("")
  }

  const openCreate = () => {
    resetForm()
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (rule: ComplianceRule) => {
    setName(rule.name)
    setDescription(rule.description || "")
    setRuleText(rule.rule_text)
    setCategory(rule.category)
    setSeverity(rule.severity)
    setScopeType(rule.scope_type)
    setScopeId(rule.scope_id || "")
    setEditing(rule)
    setFormOpen(true)
  }

  const handleSubmit = () => {
    const data: ComplianceRuleCreate = {
      name,
      description: description || null,
      rule_text: ruleText,
      category,
      severity,
      scope_type: scopeType,
      scope_id: scopeId || null,
    }

    if (editing) {
      updateRule.mutate(
        { id: editing.id, ...data },
        {
          onSuccess: () => {
            setFormOpen(false)
            toast.success(t("complianceMonitoring.rules.ruleUpdated"))
          },
          onError: (err) => toast.error(err.message),
        }
      )
    } else {
      createRule.mutate(data, {
        onSuccess: () => {
          setFormOpen(false)
          toast.success(t("complianceMonitoring.rules.ruleCreated"))
        },
        onError: (err) => toast.error(err.message),
      })
    }
  }

  const handleDelete = () => {
    if (!deleting) return
    deleteRule.mutate(deleting.id, {
      onSuccess: () => {
        setDeleteOpen(false)
        setDeleting(null)
        toast.success(t("complianceMonitoring.rules.ruleDeactivated"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("complianceMonitoring.rules.title")}
        description={t("complianceMonitoring.rules.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance" }, { label: t("complianceMonitoring.rules.title") }]}
      >
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          {t("complianceMonitoring.rules.createRule")}
        </Button>
      </PageHeader>

      {isLoading && <div className="text-muted-foreground">{t("common.loading")}</div>}

      {rules && rules.length === 0 && (
        <Card className="p-8 text-center text-muted-foreground">
          {t("complianceMonitoring.rules.noRules")}
        </Card>
      )}

      {rules && rules.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("complianceMonitoring.rules.form.name")}</TableHead>
                <TableHead>{t("complianceMonitoring.rules.form.category")}</TableHead>
                <TableHead>{t("complianceMonitoring.rules.form.severity")}</TableHead>
                <TableHead>{t("complianceMonitoring.rules.form.scopeType")}</TableHead>
                <TableHead>{t("common.status")}</TableHead>
                <TableHead>{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell className="font-medium">{rule.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {t(`complianceMonitoring.rules.category.${rule.category}`, { defaultValue: rule.category })}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={severityVariant(rule.severity)}>
                      {t(`complianceMonitoring.rules.severity.${rule.severity}`, { defaultValue: rule.severity })}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {t(`complianceMonitoring.rules.form.scope${rule.scope_type.charAt(0).toUpperCase() + rule.scope_type.slice(1)}`, { defaultValue: rule.scope_type })}
                  </TableCell>
                  <TableCell>
                    <Badge variant={rule.is_active ? "default" : "secondary"}>
                      {rule.is_active ? t("common.active") : t("common.inactive")}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEdit(rule)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          {t("common.edit")}
                        </DropdownMenuItem>
                        {rule.is_active && (
                          <DropdownMenuItem
                            onClick={() => {
                              setDeleting(rule)
                              setDeleteOpen(true)
                            }}
                            className="text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            {t("complianceMonitoring.rules.deleteTitle")}
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Create/Edit dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing
                ? t("complianceMonitoring.rules.editRule")
                : t("complianceMonitoring.rules.createRule")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("complianceMonitoring.rules.form.name")}</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t("complianceMonitoring.rules.form.description")}</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t("complianceMonitoring.rules.form.ruleText")}</Label>
              <Textarea
                value={ruleText}
                onChange={(e) => setRuleText(e.target.value)}
                rows={4}
                placeholder={t("complianceMonitoring.rules.form.ruleTextHint")}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("complianceMonitoring.rules.form.category")}</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {t(`complianceMonitoring.rules.category.${c}`, { defaultValue: c })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{t("complianceMonitoring.rules.form.severity")}</Label>
                <Select value={severity} onValueChange={setSeverity}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEVERITIES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {t(`complianceMonitoring.rules.severity.${s}`, { defaultValue: s })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t("complianceMonitoring.rules.form.scopeType")}</Label>
              <Select value={scopeType} onValueChange={setScopeType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SCOPE_TYPES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {t(`complianceMonitoring.rules.form.scope${s.charAt(0).toUpperCase() + s.slice(1).replace("_", "")}`, { defaultValue: s })}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {scopeType !== "all" && (
              <div className="space-y-2">
                <Label>{t("complianceMonitoring.rules.form.scopeId")}</Label>
                <Input
                  value={scopeId}
                  onChange={(e) => setScopeId(e.target.value)}
                  placeholder="UUID"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!name.trim() || !ruleText.trim() || createRule.isPending || updateRule.isPending}
            >
              {createRule.isPending || updateRule.isPending
                ? t("common.saving")
                : t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t("complianceMonitoring.rules.deleteTitle")}
        description={t("complianceMonitoring.rules.deleteConfirm", { name: deleting?.name })}
        confirmLabel={t("common.confirm")}
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  )
}
