import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useStirShakenConfig,
  useSpamFilter,
  useSpamBlockList,
  useAddBlockListEntry,
  useSpamAllowList,
  useAddAllowListEntry,
} from "@/api/stir-shaken"
import { toast } from "sonner"
import { ShieldCheck, Ban, CheckCircle2, Plus, Loader2 } from "lucide-react"

function ConfigTab() {
  const { data: config, isLoading } = useStirShakenConfig()
  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>STIR/SHAKEN Configuration</CardTitle>
          {config && <Badge variant={config.enabled ? "default" : "secondary"}>{config.enabled ? "Enabled" : "Disabled"}</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {config ? (
          <>
            <div><Label>Attestation Level</Label><p className="text-sm">{config.attestation_level}</p></div>
            <div><Label>Certificate</Label><p className="text-sm">{config.certificate_pem ? "Uploaded" : "Not configured"}</p></div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No STIR/SHAKEN configuration found. Create one to enable caller ID verification.</p>
        )}
      </CardContent>
    </Card>
  )
}

function SpamFilterTab() {
  const { data: filter, isLoading } = useSpamFilter()
  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <Card>
      <CardHeader><CardTitle>Spam Filter Settings</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {filter ? (
          <div className="grid grid-cols-2 gap-4">
            <div><Label>Active</Label><p className="text-sm">{filter.is_active ? "Yes" : "No"}</p></div>
            <div><Label>Score Threshold</Label><p className="text-sm">{filter.spam_score_threshold}</p></div>
            <div><Label>Block Anonymous</Label><p className="text-sm">{filter.block_anonymous ? "Yes" : "No"}</p></div>
            <div><Label>Min Attestation</Label><p className="text-sm">{filter.min_attestation ?? "None"}</p></div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No spam filter configured.</p>
        )}
      </CardContent>
    </Card>
  )
}

function BlockAllowListTab() {
  const { data: blockList, isLoading: blockLoading } = useSpamBlockList()
  const { data: allowList, isLoading: allowLoading } = useSpamAllowList()
  const addBlock = useAddBlockListEntry()
  const addAllow = useAddAllowListEntry()
  const [showAdd, setShowAdd] = useState<"block" | "allow" | null>(null)
  const [pattern, setPattern] = useState("")

  if (blockLoading || allowLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Block List</h3>
          <Button size="sm" variant="outline" onClick={() => setShowAdd("block")}><Plus className="h-3 w-3 mr-1" />Add</Button>
        </div>
        {!blockList?.length ? (
          <EmptyState icon={Ban} title="No blocked numbers" description="Add number patterns to automatically block." />
        ) : (
          <div className="space-y-1">
            {blockList.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-sm py-1 border-b">
                <span className="font-mono">{e.pattern}</span>
                <span className="text-xs text-muted-foreground">{e.reason}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Allow List</h3>
          <Button size="sm" variant="outline" onClick={() => setShowAdd("allow")}><Plus className="h-3 w-3 mr-1" />Add</Button>
        </div>
        {!allowList?.length ? (
          <EmptyState icon={CheckCircle2} title="No allowed numbers" description="Add number patterns to always allow." />
        ) : (
          <div className="space-y-1">
            {allowList.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-sm py-1 border-b">
                <span className="font-mono">{e.pattern}</span>
                <span className="text-xs text-muted-foreground">{e.reason}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={!!showAdd} onOpenChange={() => { setShowAdd(null); setPattern("") }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Add to {showAdd === "block" ? "Block" : "Allow"} List</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div><Label>Pattern</Label><Input value={pattern} onChange={(e) => setPattern(e.target.value)} placeholder="+1555*" /></div>
            <Button
              disabled={!pattern}
              onClick={async () => {
                if (showAdd === "block") await addBlock.mutateAsync({ pattern })
                else await addAllow.mutateAsync({ pattern })
                toast.success(`Added to ${showAdd} list`)
                setShowAdd(null)
                setPattern("")
              }}
            >
              Add
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export function StirShakenPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="STIR/SHAKEN & Spam Filtering" description="Caller ID verification and robocall protection." />
      <Tabs defaultValue="config">
        <TabsList>
          <TabsTrigger value="config"><ShieldCheck className="h-4 w-4 mr-1.5" />STIR/SHAKEN</TabsTrigger>
          <TabsTrigger value="spam"><Ban className="h-4 w-4 mr-1.5" />Spam Filter</TabsTrigger>
          <TabsTrigger value="lists"><CheckCircle2 className="h-4 w-4 mr-1.5" />Block/Allow</TabsTrigger>
        </TabsList>
        <TabsContent value="config"><ConfigTab /></TabsContent>
        <TabsContent value="spam"><SpamFilterTab /></TabsContent>
        <TabsContent value="lists"><BlockAllowListTab /></TabsContent>
      </Tabs>
    </div>
  )
}
