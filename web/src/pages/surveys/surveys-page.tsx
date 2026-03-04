import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import {
  useSurveyTemplates,
  useCreateSurveyTemplate,
  useDeleteSurveyTemplate,
  useSurveyResponses,
  useSurveyAnalytics,
  type SurveyTemplate,
  type SurveyTemplateCreate,
} from "@/api/surveys"
import { toast } from "sonner"
import { Plus, ClipboardList, BarChart3, Trash2, Loader2, Star } from "lucide-react"

function TemplatesTab() {
  const { data: templates, isLoading } = useSurveyTemplates()
  const createMutation = useCreateSurveyTemplate()
  const deleteMutation = useDeleteSurveyTemplate()
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<SurveyTemplate | null>(null)
  const [analyticsTarget, setAnalyticsTarget] = useState<string | null>(null)

  const handleCreate = async (data: SurveyTemplateCreate) => {
    await createMutation.mutateAsync(data)
    toast.success("Survey template created")
    setShowForm(false)
  }

  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" />Create Template</Button>
      </div>

      {!templates?.length ? (
        <EmptyState icon={ClipboardList} title="No survey templates" description="Create a survey template to collect post-call feedback." />
      ) : (
        <div className="space-y-3">
          {templates.map((tmpl) => (
            <Card key={tmpl.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{tmpl.name}</CardTitle>
                    <Badge variant={tmpl.is_active ? "default" : "secondary"}>{tmpl.is_active ? "Active" : "Inactive"}</Badge>
                    <Badge variant="outline">{tmpl.questions.length} questions</Badge>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => setAnalyticsTarget(tmpl.id)}>
                      <BarChart3 className="h-4 w-4 mr-1" />Analytics
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(tmpl)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
                {tmpl.description && <CardDescription>{tmpl.description}</CardDescription>}
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-1">
                  {tmpl.questions.map((q, i) => (
                    <div key={i} className="text-xs text-muted-foreground flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px]">{q.question_type}</Badge>
                      {q.question_text}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Create Survey Template</DialogTitle></DialogHeader>
          <SurveyTemplateForm onSubmit={handleCreate} isLoading={createMutation.isPending} />
        </DialogContent>
      </Dialog>

      {analyticsTarget && (
        <Dialog open={!!analyticsTarget} onOpenChange={() => setAnalyticsTarget(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle>Survey Analytics</DialogTitle></DialogHeader>
            <AnalyticsView templateId={analyticsTarget} />
          </DialogContent>
        </Dialog>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Survey Template"
        description={`Delete "${deleteTarget?.name}"? All associated responses will also be deleted.`}
        onConfirm={async () => {
          if (deleteTarget) {
            await deleteMutation.mutateAsync(deleteTarget.id)
            toast.success("Survey template deleted")
            setDeleteTarget(null)
          }
        }}
      />
    </div>
  )
}

function SurveyTemplateForm({ onSubmit, isLoading }: { onSubmit: (d: SurveyTemplateCreate) => void; isLoading: boolean }) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [questions, setQuestions] = useState([{ question_text: "", question_type: "rating" }])

  const addQuestion = () => setQuestions([...questions, { question_text: "", question_type: "rating" }])
  const updateQuestion = (i: number, text: string) => {
    const q = [...questions]
    q[i] = { ...q[i], question_text: text }
    setQuestions(q)
  }
  const removeQuestion = (i: number) => setQuestions(questions.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-4">
      <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Post-Call Survey" /></div>
      <div><Label>Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} /></div>
      <div>
        <Label>Questions</Label>
        <div className="space-y-2 mt-1">
          {questions.map((q, i) => (
            <div key={i} className="flex gap-2">
              <Input value={q.question_text} onChange={(e) => updateQuestion(i, e.target.value)} placeholder={`Question ${i + 1}`} className="flex-1" />
              {questions.length > 1 && (
                <Button variant="ghost" size="icon" onClick={() => removeQuestion(i)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addQuestion}><Plus className="h-3 w-3 mr-1" />Add Question</Button>
        </div>
      </div>
      <Button onClick={() => onSubmit({ name, description: description || undefined, questions })} disabled={isLoading || !name || questions.some((q) => !q.question_text)}>
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Create
      </Button>
    </div>
  )
}

function AnalyticsView({ templateId }: { templateId: string }) {
  const { data, isLoading } = useSurveyAnalytics(templateId)
  if (isLoading) return <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin" /></div>
  if (!data) return <p className="text-sm text-muted-foreground">No data available.</p>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{data.total_responses}</p>
            <p className="text-xs text-muted-foreground">Total Responses</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="flex items-center justify-center gap-1">
              <Star className="h-4 w-4 text-yellow-500" />
              <p className="text-2xl font-bold">{data.avg_overall_score?.toFixed(1) ?? "N/A"}</p>
            </div>
            <p className="text-xs text-muted-foreground">Avg Score</p>
          </CardContent>
        </Card>
      </div>

      {Object.keys(data.per_agent_avg).length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2">Per Agent</h4>
          <div className="space-y-1">
            {Object.entries(data.per_agent_avg).map(([agent, score]) => (
              <div key={agent} className="flex items-center justify-between text-xs">
                <span>Ext {agent}</span>
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3 text-yellow-500" />
                  <span>{(score as number).toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ResponsesTab() {
  const { data, isLoading } = useSurveyResponses()
  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>
  const responses = data?.items ?? []

  if (!responses.length) return <EmptyState icon={ClipboardList} title="No responses" description="Survey responses will appear here once callers complete surveys." />

  return (
    <div className="space-y-2">
      {responses.map((r) => (
        <Card key={r.id}>
          <CardContent className="pt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">{r.caller_number}</span>
              {r.agent_extension && <Badge variant="outline">Agent: {r.agent_extension}</Badge>}
              {r.overall_score != null && (
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3 text-yellow-500" />
                  <span className="text-sm">{r.overall_score.toFixed(1)}</span>
                </div>
              )}
            </div>
            <span className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleString()}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function SurveysPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Post-Call Surveys"
        description="Create and manage IVR surveys for collecting caller feedback."
      />

      <Tabs defaultValue="templates">
        <TabsList>
          <TabsTrigger value="templates"><ClipboardList className="h-4 w-4 mr-1.5" />Templates</TabsTrigger>
          <TabsTrigger value="responses"><Star className="h-4 w-4 mr-1.5" />Responses</TabsTrigger>
        </TabsList>
        <TabsContent value="templates"><TemplatesTab /></TabsContent>
        <TabsContent value="responses"><ResponsesTab /></TabsContent>
      </Tabs>
    </div>
  )
}
