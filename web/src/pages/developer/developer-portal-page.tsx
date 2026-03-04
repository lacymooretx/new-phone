import { useState } from "react"
import { useTranslation } from "react-i18next"
import { PageHeader } from "@/components/shared/page-header"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useWebhookDeliveries,
  type WebhookSubscription,
  type WebhookSubscriptionCreate,
} from "@/api/webhooks"
import {
  useApiKeys,
  useCreateApiKey,
  useDeleteApiKey,
  type ApiKeyResponse,
  type ApiKeyCreate,
  type ApiKeyCreatedResponse,
} from "@/api/api-keys"
import { toast } from "sonner"
import {
  Plus,
  Webhook,
  Key,
  Send,
  Trash2,
  Pencil,
  Copy,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Code2,
  Loader2,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal } from "lucide-react"

const WEBHOOK_EVENT_TYPES = [
  "call.start", "call.end", "call.answered",
  "voicemail.received",
  "extension.registered", "extension.unregistered",
  "queue.join", "queue.leave", "queue.answer",
  "sms.received", "sms.sent",
  "recording.ready", "cdr.created",
  "parking.parked", "parking.retrieved",
]

// ── Webhooks Tab ─────────────────────────────────────────────────────
function WebhooksTab() {
  const { data: webhooks, isLoading } = useWebhooks()
  const createMutation = useCreateWebhook()
  const deleteMutation = useDeleteWebhook()
  const testMutation = useTestWebhook()
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<WebhookSubscription | null>(null)
  const [deliveryTarget, setDeliveryTarget] = useState<string | null>(null)

  const handleCreate = async (data: WebhookSubscriptionCreate) => {
    await createMutation.mutateAsync(data)
    toast.success("Webhook created")
    setShowForm(false)
  }

  const handleTest = async (id: string) => {
    const result = await testMutation.mutateAsync(id)
    if (result.status === "success") {
      toast.success("Test delivery succeeded")
    } else {
      toast.error(`Test delivery failed: ${result.error_message || "Unknown error"}`)
    }
  }

  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" />Add Webhook</Button>
      </div>

      {!webhooks?.length ? (
        <EmptyState icon={Webhook} title="No webhooks" description="Create a webhook to receive platform event notifications." />
      ) : (
        <div className="space-y-3">
          {webhooks.map((wh) => (
            <Card key={wh.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{wh.name}</CardTitle>
                    <Badge variant={wh.is_active ? "default" : "secondary"}>{wh.is_active ? "Active" : "Inactive"}</Badge>
                    {wh.failure_count > 0 && <Badge variant="destructive">{wh.failure_count} failures</Badge>}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleTest(wh.id)}><Send className="h-4 w-4 mr-2" />Test</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setDeliveryTarget(wh.id)}><Clock className="h-4 w-4 mr-2" />View Deliveries</DropdownMenuItem>
                      <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(wh)}><Trash2 className="h-4 w-4 mr-2" />Delete</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <CardDescription className="text-xs font-mono truncate">{wh.target_url}</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-1">
                  {wh.event_types.map((et) => <Badge key={et} variant="outline" className="text-xs">{et}</Badge>)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Create Webhook</DialogTitle></DialogHeader>
          <WebhookForm onSubmit={handleCreate} isLoading={createMutation.isPending} />
        </DialogContent>
      </Dialog>

      {deliveryTarget && (
        <Dialog open={!!deliveryTarget} onOpenChange={() => setDeliveryTarget(null)}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Delivery Log</DialogTitle></DialogHeader>
            <DeliveryLogView webhookId={deliveryTarget} />
          </DialogContent>
        </Dialog>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Webhook"
        description={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        onConfirm={async () => {
          if (deleteTarget) {
            await deleteMutation.mutateAsync(deleteTarget.id)
            toast.success("Webhook deleted")
            setDeleteTarget(null)
          }
        }}
      />
    </div>
  )
}

function WebhookForm({ onSubmit, isLoading }: { onSubmit: (d: WebhookSubscriptionCreate) => void; isLoading: boolean }) {
  const [name, setName] = useState("")
  const [url, setUrl] = useState("")
  const [events, setEvents] = useState<string[]>([])
  const [description, setDescription] = useState("")

  return (
    <div className="space-y-4">
      <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Webhook" /></div>
      <div><Label>Target URL</Label><Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/webhook" /></div>
      <div>
        <Label>Events</Label>
        <div className="grid grid-cols-2 gap-1 mt-1 max-h-48 overflow-y-auto border rounded p-2">
          {WEBHOOK_EVENT_TYPES.map((et) => (
            <label key={et} className="flex items-center gap-1.5 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={events.includes(et)}
                onChange={(e) => setEvents(e.target.checked ? [...events, et] : events.filter((x) => x !== et))}
                className="rounded"
              />
              {et}
            </label>
          ))}
        </div>
      </div>
      <div><Label>Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} /></div>
      <Button onClick={() => onSubmit({ name, target_url: url, event_types: events, description: description || undefined })} disabled={isLoading || !name || !url || !events.length}>
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Create
      </Button>
    </div>
  )
}

function DeliveryLogView({ webhookId }: { webhookId: string }) {
  const { data, isLoading } = useWebhookDeliveries(webhookId)
  if (isLoading) return <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin" /></div>
  if (!data?.items?.length) return <p className="text-sm text-muted-foreground py-4">No deliveries yet.</p>

  return (
    <div className="space-y-2">
      {data.items.map((log) => (
        <div key={log.id} className="flex items-center gap-3 text-xs border rounded px-3 py-2">
          {log.status === "success" ? <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" /> :
           log.status === "retrying" ? <Clock className="h-4 w-4 text-yellow-500 shrink-0" /> :
           <XCircle className="h-4 w-4 text-red-500 shrink-0" />}
          <Badge variant="outline">{log.event_type}</Badge>
          <span className="text-muted-foreground">{log.response_status_code ?? "N/A"}</span>
          <span className="text-muted-foreground ml-auto">{new Date(log.created_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

// ── API Keys Tab ─────────────────────────────────────────────────────
function ApiKeysTab() {
  const { data: keys, isLoading } = useApiKeys()
  const createMutation = useCreateApiKey()
  const deleteMutation = useDeleteApiKey()
  const [showForm, setShowForm] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ApiKeyResponse | null>(null)

  const handleCreate = async (data: ApiKeyCreate) => {
    const result = await createMutation.mutateAsync(data) as ApiKeyCreatedResponse
    setCreatedKey(result.raw_key)
    toast.success("API key created")
    setShowForm(false)
  }

  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" />Create API Key</Button>
      </div>

      {createdKey && (
        <Card className="border-green-500/50 bg-green-50 dark:bg-green-950/20">
          <CardContent className="pt-4">
            <p className="text-sm font-medium mb-1">Your new API key (copy it now — it won't be shown again):</p>
            <div className="flex items-center gap-2">
              <code className="text-xs bg-background px-2 py-1 rounded border flex-1 truncate">{createdKey}</code>
              <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(createdKey); toast.success("Copied") }}>
                <Copy className="h-3 w-3" />
              </Button>
            </div>
            <Button variant="ghost" size="sm" className="mt-2" onClick={() => setCreatedKey(null)}>Dismiss</Button>
          </CardContent>
        </Card>
      )}

      {!keys?.length ? (
        <EmptyState icon={Key} title="No API keys" description="Create an API key to authenticate programmatic access." />
      ) : (
        <div className="space-y-3">
          {keys.map((k) => (
            <Card key={k.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{k.name}</CardTitle>
                    <Badge variant={k.is_active ? "default" : "secondary"}>{k.is_active ? "Active" : "Revoked"}</Badge>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(k)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                </div>
                <CardDescription className="text-xs font-mono">{k.key_prefix}...</CardDescription>
              </CardHeader>
              <CardContent className="pt-0 flex gap-2 items-center text-xs text-muted-foreground">
                <div className="flex gap-1">{k.scopes.map((s) => <Badge key={s} variant="outline">{s}</Badge>)}</div>
                <span>Rate: {k.rate_limit}/min</span>
                {k.last_used_at && <span>Last used: {new Date(k.last_used_at).toLocaleDateString()}</span>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Create API Key</DialogTitle></DialogHeader>
          <ApiKeyForm onSubmit={handleCreate} isLoading={createMutation.isPending} />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete API Key"
        description={`Delete "${deleteTarget?.name}"? Any integrations using this key will stop working.`}
        onConfirm={async () => {
          if (deleteTarget) {
            await deleteMutation.mutateAsync(deleteTarget.id)
            toast.success("API key deleted")
            setDeleteTarget(null)
          }
        }}
      />
    </div>
  )
}

function ApiKeyForm({ onSubmit, isLoading }: { onSubmit: (d: ApiKeyCreate) => void; isLoading: boolean }) {
  const [name, setName] = useState("")
  const [scopes, setScopes] = useState<string[]>(["read"])
  const [rateLimit, setRateLimit] = useState("1000")
  const [description, setDescription] = useState("")

  const allScopes = ["read", "write", "admin"]

  return (
    <div className="space-y-4">
      <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Integration Key" /></div>
      <div>
        <Label>Scopes</Label>
        <div className="flex gap-3 mt-1">
          {allScopes.map((s) => (
            <label key={s} className="flex items-center gap-1.5 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={scopes.includes(s)}
                onChange={(e) => setScopes(e.target.checked ? [...scopes, s] : scopes.filter((x) => x !== s))}
                className="rounded"
              />
              {s}
            </label>
          ))}
        </div>
      </div>
      <div><Label>Rate Limit (req/min)</Label><Input type="number" value={rateLimit} onChange={(e) => setRateLimit(e.target.value)} /></div>
      <div><Label>Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} /></div>
      <Button onClick={() => onSubmit({ name, scopes, rate_limit: parseInt(rateLimit), description: description || undefined })} disabled={isLoading || !name || !scopes.length}>
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Create Key
      </Button>
    </div>
  )
}

// ── Docs Tab ─────────────────────────────────────────────────────────
function DocsTab() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Code2 className="h-5 w-5" />API Documentation</CardTitle>
          <CardDescription>Interactive API documentation powered by OpenAPI.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Button variant="outline" asChild>
              <a href="/api/docs" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />Swagger UI
              </a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/api/redoc" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />ReDoc
              </a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/api/openapi.json" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />OpenAPI JSON
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>All API requests require authentication via one of:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Bearer Token</strong> — Include <code className="text-xs bg-muted px-1 rounded">Authorization: Bearer &lt;JWT&gt;</code> header</li>
            <li><strong>API Key</strong> — Include <code className="text-xs bg-muted px-1 rounded">X-API-Key: np_...</code> header</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Webhook Signatures</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>All webhook deliveries include an HMAC-SHA256 signature in the <code className="text-xs bg-muted px-1 rounded">X-Webhook-Signature</code> header.</p>
          <p>Verify by computing <code className="text-xs bg-muted px-1 rounded">sha256=HMAC(secret, body)</code> and comparing.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SDK Quick Start</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">Python</p>
              <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">{`pip install aspendora-connect
from aspendora_connect import Client
client = Client(api_key="np_...", base_url="https://your-instance.com")`}</pre>
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Node.js / TypeScript</p>
              <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">{`npm install @aspendora/connect
import { Client } from '@aspendora/connect';
const client = new Client({ apiKey: 'np_...', baseUrl: 'https://your-instance.com' });`}</pre>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────────────
export function DeveloperPortalPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Developer Portal"
        description="Manage webhooks, API keys, and integration tools."
      />

      <Tabs defaultValue="webhooks">
        <TabsList>
          <TabsTrigger value="webhooks"><Webhook className="h-4 w-4 mr-1.5" />Webhooks</TabsTrigger>
          <TabsTrigger value="api-keys"><Key className="h-4 w-4 mr-1.5" />API Keys</TabsTrigger>
          <TabsTrigger value="docs"><Code2 className="h-4 w-4 mr-1.5" />Docs & SDKs</TabsTrigger>
        </TabsList>
        <TabsContent value="webhooks"><WebhooksTab /></TabsContent>
        <TabsContent value="api-keys"><ApiKeysTab /></TabsContent>
        <TabsContent value="docs"><DocsTab /></TabsContent>
      </Tabs>
    </div>
  )
}
