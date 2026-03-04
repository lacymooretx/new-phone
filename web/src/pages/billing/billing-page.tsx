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
import { useUsageRecords, useRateDecks, useCreateRateDeck, useBillingConfig, useUpdateBillingConfig } from "@/api/billing"
import { toast } from "sonner"
import { DollarSign, FileBarChart, Settings, Plus, Loader2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

function UsageTab() {
  const { data, isLoading } = useUsageRecords()
  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>
  const records = data?.items ?? []

  if (!records.length) return <EmptyState icon={FileBarChart} title="No usage records" description="Usage records will appear after the first billing cycle." />

  return (
    <div className="space-y-2">
      {records.map((r) => (
        <Card key={r.id}>
          <CardContent className="pt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge variant="outline">{r.metric}</Badge>
              <span className="text-sm font-medium">{r.quantity.toLocaleString()} units</span>
              {r.total_cost != null && <span className="text-sm text-muted-foreground">${r.total_cost.toFixed(2)}</span>}
            </div>
            <span className="text-xs text-muted-foreground">
              {new Date(r.period_start).toLocaleDateString()} - {new Date(r.period_end).toLocaleDateString()}
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function RateDecksTab() {
  const { data: rateDecks, isLoading } = useRateDecks()
  const createMutation = useCreateRateDeck()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState("")

  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" />Create Rate Deck</Button>
      </div>

      {!rateDecks?.length ? (
        <EmptyState icon={DollarSign} title="No rate decks" description="Create a rate deck to define per-minute rates." />
      ) : (
        <div className="space-y-3">
          {rateDecks.map((rd) => (
            <Card key={rd.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{rd.name}</CardTitle>
                    {rd.is_default && <Badge>Default</Badge>}
                    <Badge variant={rd.is_active ? "default" : "secondary"}>{rd.is_active ? "Active" : "Inactive"}</Badge>
                  </div>
                </div>
              </CardHeader>
              {rd.description && <CardContent className="pt-0 text-xs text-muted-foreground">{rd.description}</CardContent>}
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Create Rate Deck</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="US Domestic" /></div>
            <Button
              disabled={!name || createMutation.isPending}
              onClick={async () => {
                await createMutation.mutateAsync({ name })
                toast.success("Rate deck created")
                setShowForm(false)
                setName("")
              }}
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ConfigTab() {
  const { data: config, isLoading } = useBillingConfig()
  const updateMutation = useUpdateBillingConfig()

  if (isLoading) return <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>
  if (!config) return <p className="text-sm text-muted-foreground">No billing configuration found.</p>

  return (
    <Card>
      <CardHeader><CardTitle>Billing Configuration</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>Billing Provider</Label>
          <Select
            value={config.billing_provider}
            onValueChange={async (v) => {
              await updateMutation.mutateAsync({ billing_provider: v })
              toast.success("Billing provider updated")
            }}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="manual">Manual</SelectItem>
              <SelectItem value="connectwise">ConnectWise</SelectItem>
              <SelectItem value="pax8">Pax8</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Billing Cycle Day</Label>
            <p className="text-sm">{config.billing_cycle_day}</p>
          </div>
          <div>
            <Label>Auto Generate</Label>
            <p className="text-sm">{config.auto_generate ? "Yes" : "No"}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function BillingPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Billing & Usage" description="Usage metering, rate decks, and billing configuration." />
      <Tabs defaultValue="usage">
        <TabsList>
          <TabsTrigger value="usage"><FileBarChart className="h-4 w-4 mr-1.5" />Usage</TabsTrigger>
          <TabsTrigger value="rate-decks"><DollarSign className="h-4 w-4 mr-1.5" />Rate Decks</TabsTrigger>
          <TabsTrigger value="config"><Settings className="h-4 w-4 mr-1.5" />Config</TabsTrigger>
        </TabsList>
        <TabsContent value="usage"><UsageTab /></TabsContent>
        <TabsContent value="rate-decks"><RateDecksTab /></TabsContent>
        <TabsContent value="config"><ConfigTab /></TabsContent>
      </Tabs>
    </div>
  )
}
