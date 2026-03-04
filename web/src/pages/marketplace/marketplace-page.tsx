import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useAvailablePlugins,
  useInstalledPlugins,
  useInstallPlugin,
  useUninstallPlugin,
  useActivatePlugin,
  useDeactivatePlugin,
  useUpdatePluginConfig,
  usePluginEventLogs,

  type TenantPlugin,
} from "@/api/plugins"
import { toast } from "sonner"
import {
  Puzzle,
  Download,
  Trash2,
  Play,
  Pause,
  Settings,
  ExternalLink,
  Loader2,
  ScrollText,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal } from "lucide-react"

// ── Available Tab ───────────────────────────────────────────────────

function AvailableTab() {
  const { data: plugins, isLoading } = useAvailablePlugins()
  const { data: installed } = useInstalledPlugins()
  const installMutation = useInstallPlugin()

  const installedPluginIds = new Set((installed ?? []).map((tp) => tp.plugin_id))

  const handleInstall = async (pluginId: string) => {
    await installMutation.mutateAsync(pluginId)
    toast.success("Plugin installed")
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    )
  }

  if (!plugins?.length) {
    return (
      <EmptyState
        icon={Puzzle}
        title="No plugins available"
        description="The plugin marketplace is empty. Check back later for new integrations."
      />
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {plugins.map((plugin) => (
        <Card key={plugin.id}>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                {plugin.icon_url ? (
                  <img src={plugin.icon_url} alt="" className="h-8 w-8 rounded" />
                ) : (
                  <Puzzle className="h-8 w-8 text-muted-foreground" />
                )}
                <div>
                  <CardTitle className="text-base">{plugin.name}</CardTitle>
                  <CardDescription className="text-xs">
                    v{plugin.version} by {plugin.author}
                  </CardDescription>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground line-clamp-2">
              {plugin.description}
            </p>
            <div className="flex flex-wrap gap-1">
              {plugin.hook_types.map((ht) => (
                <Badge key={ht} variant="outline" className="text-xs">
                  {ht}
                </Badge>
              ))}
            </div>
            <div className="flex items-center justify-between pt-1">
              {plugin.homepage_url && (
                <a
                  href={plugin.homepage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                >
                  <ExternalLink className="h-3 w-3" />
                  Website
                </a>
              )}
              <div className="ml-auto">
                {installedPluginIds.has(plugin.id) ? (
                  <Badge variant="secondary">Installed</Badge>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => handleInstall(plugin.id)}
                    disabled={installMutation.isPending}
                  >
                    {installMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Download className="h-4 w-4 mr-1" />
                    )}
                    Install
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Installed Tab ───────────────────────────────────────────────────

function InstalledTab() {
  const { data: installed, isLoading } = useInstalledPlugins()
  const uninstallMutation = useUninstallPlugin()
  const activateMutation = useActivatePlugin()
  const deactivateMutation = useDeactivatePlugin()
  const updateConfigMutation = useUpdatePluginConfig()

  const [uninstallTarget, setUninstallTarget] = useState<TenantPlugin | null>(null)
  const [configTarget, setConfigTarget] = useState<TenantPlugin | null>(null)
  const [configJson, setConfigJson] = useState("")
  const [logsTarget, setLogsTarget] = useState<string | null>(null)

  const handleToggleActive = async (tp: TenantPlugin) => {
    if (tp.status === "active") {
      await deactivateMutation.mutateAsync(tp.plugin_id)
      toast.success("Plugin deactivated")
    } else {
      await activateMutation.mutateAsync(tp.plugin_id)
      toast.success("Plugin activated")
    }
  }

  const openConfig = (tp: TenantPlugin) => {
    setConfigTarget(tp)
    setConfigJson(JSON.stringify(tp.config ?? {}, null, 2))
  }

  const handleSaveConfig = async () => {
    if (!configTarget) return
    try {
      const parsed = JSON.parse(configJson)
      await updateConfigMutation.mutateAsync({
        pluginId: configTarget.plugin_id,
        config: parsed,
      })
      toast.success("Plugin config updated")
      setConfigTarget(null)
    } catch {
      toast.error("Invalid JSON")
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    )
  }

  if (!installed?.length) {
    return (
      <EmptyState
        icon={Puzzle}
        title="No plugins installed"
        description="Browse the Available tab to install plugins."
      />
    )
  }

  return (
    <div className="space-y-3">
      {installed.map((tp) => (
        <Card key={tp.id}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {tp.plugin.icon_url ? (
                  <img src={tp.plugin.icon_url} alt="" className="h-6 w-6 rounded" />
                ) : (
                  <Puzzle className="h-6 w-6 text-muted-foreground" />
                )}
                <CardTitle className="text-base">{tp.plugin.name}</CardTitle>
                <Badge variant="outline" className="text-xs">
                  v{tp.plugin.version}
                </Badge>
                <Badge
                  variant={tp.status === "active" ? "default" : "secondary"}
                >
                  {tp.status}
                </Badge>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleToggleActive(tp)}>
                    {tp.status === "active" ? (
                      <>
                        <Pause className="h-4 w-4 mr-2" />
                        Deactivate
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Activate
                      </>
                    )}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => openConfig(tp)}>
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setLogsTarget(tp.plugin_id)}>
                    <ScrollText className="h-4 w-4 mr-2" />
                    Event Logs
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => setUninstallTarget(tp)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Uninstall
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <CardDescription className="text-xs">
              {tp.plugin.description}
            </CardDescription>
          </CardHeader>
        </Card>
      ))}

      {/* Config Dialog */}
      <Dialog open={!!configTarget} onOpenChange={() => setConfigTarget(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Plugin Settings: {configTarget?.plugin.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Configuration (JSON)</Label>
              <Textarea
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                rows={10}
                className="font-mono text-xs"
              />
            </div>
            <Button
              onClick={handleSaveConfig}
              disabled={updateConfigMutation.isPending}
            >
              {updateConfigMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Event Logs Dialog */}
      {logsTarget && (
        <Dialog open={!!logsTarget} onOpenChange={() => setLogsTarget(null)}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Plugin Event Logs</DialogTitle>
            </DialogHeader>
            <PluginEventLogView pluginId={logsTarget} />
          </DialogContent>
        </Dialog>
      )}

      {/* Uninstall Confirm */}
      <ConfirmDialog
        open={!!uninstallTarget}
        onOpenChange={() => setUninstallTarget(null)}
        title="Uninstall Plugin"
        description={`Uninstall "${uninstallTarget?.plugin.name}"? All plugin configuration for this tenant will be removed.`}
        onConfirm={async () => {
          if (uninstallTarget) {
            await uninstallMutation.mutateAsync(uninstallTarget.plugin_id)
            toast.success("Plugin uninstalled")
            setUninstallTarget(null)
          }
        }}
      />
    </div>
  )
}

// ── Event Log View ──────────────────────────────────────────────────

function PluginEventLogView({ pluginId }: { pluginId: string }) {
  const { data, isLoading } = usePluginEventLogs(pluginId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    )
  }

  if (!data?.items?.length) {
    return (
      <p className="text-sm text-muted-foreground py-4">No event logs yet.</p>
    )
  }

  return (
    <div className="space-y-2">
      {data.items.map((log) => (
        <div
          key={log.id}
          className="flex items-center gap-3 text-xs border rounded px-3 py-2"
        >
          {log.error_message ? (
            <XCircle className="h-4 w-4 text-red-500 shrink-0" />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
          )}
          <Badge variant="outline">{log.hook_type}</Badge>
          <span className="text-muted-foreground">
            {log.response_status ?? "N/A"}
          </span>
          {log.error_message && (
            <span className="text-red-500 truncate max-w-48">
              {log.error_message}
            </span>
          )}
          <span className="text-muted-foreground ml-auto">
            {new Date(log.created_at).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────

export function MarketplacePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Plugin Marketplace"
        description="Browse, install, and manage plugins to extend platform functionality."
      />

      <Tabs defaultValue="available">
        <TabsList>
          <TabsTrigger value="available">
            <Puzzle className="h-4 w-4 mr-1.5" />
            Available
          </TabsTrigger>
          <TabsTrigger value="installed">
            <Download className="h-4 w-4 mr-1.5" />
            Installed
          </TabsTrigger>
        </TabsList>
        <TabsContent value="available">
          <AvailableTab />
        </TabsContent>
        <TabsContent value="installed">
          <InstalledTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
