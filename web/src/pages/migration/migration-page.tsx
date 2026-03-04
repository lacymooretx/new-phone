import { useState, useCallback } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/shared/empty-state"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { useMigrationJobs, useUploadMigration, useValidateMigration, useExecuteMigration } from "@/api/migration"
import { toast } from "sonner"
import { Upload, FileUp, CheckCircle2, AlertCircle, Loader2, Play, Search } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const statusConfig: Record<string, { color: string; label: string }> = {
  pending: { color: "text-yellow-500", label: "Pending" },
  validating: { color: "text-blue-500", label: "Validating" },
  validated: { color: "text-green-500", label: "Validated" },
  importing: { color: "text-blue-500", label: "Importing" },
  completed: { color: "text-green-600", label: "Completed" },
  failed: { color: "text-red-500", label: "Failed" },
}

export function MigrationPage() {
  const { data: jobs, isLoading } = useMigrationJobs()
  const uploadMutation = useUploadMigration()
  const validateMutation = useValidateMigration()
  const executeMutation = useExecuteMigration()
  const [showUpload, setShowUpload] = useState(false)
  const [platform, setPlatform] = useState("freepbx")
  const [file, setFile] = useState<File | null>(null)

  const handleUpload = useCallback(async () => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = async () => {
      const base64 = (reader.result as string).split(",")[1]
      await uploadMutation.mutateAsync({
        source_platform: platform,
        file_name: file.name,
        file_content: base64,
      })
      toast.success("Migration file uploaded")
      setShowUpload(false)
      setFile(null)
    }
    reader.readAsDataURL(file)
  }, [file, platform, uploadMutation])

  return (
    <div className="space-y-6">
      <PageHeader title="Migration Tools" description="Import configuration from FreePBX, 3CX, Asterisk, or CSV." />

      <div className="flex justify-end">
        <Button onClick={() => setShowUpload(true)}><Upload className="h-4 w-4 mr-2" />Upload Migration File</Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-5 w-5 animate-spin" /></div>
      ) : !jobs?.length ? (
        <EmptyState icon={FileUp} title="No migration jobs" description="Upload a backup or CSV file to begin migrating." />
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const cfg = statusConfig[job.status] ?? statusConfig.pending
            return (
              <Card key={job.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div>
                        <CardTitle className="text-base">{job.file_name}</CardTitle>
                        <p className="text-xs text-muted-foreground">{job.source_platform}</p>
                      </div>
                      <Badge variant="outline" className={cfg.color}>{cfg.label}</Badge>
                    </div>
                    <div className="flex gap-1">
                      {job.status === "pending" && (
                        <Button size="sm" variant="outline" onClick={() => validateMutation.mutateAsync(job.id).then(() => toast.success("Validation started"))}>
                          <Search className="h-4 w-4 mr-1" />Validate
                        </Button>
                      )}
                      {job.status === "validated" && (
                        <Button size="sm" onClick={() => executeMutation.mutateAsync(job.id).then(() => toast.success("Import started"))}>
                          <Play className="h-4 w-4 mr-1" />Import
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0 text-xs text-muted-foreground flex gap-4">
                  <span>Records: {job.imported_records}/{job.total_records}</span>
                  {job.failed_records > 0 && <span className="text-red-500">Failed: {job.failed_records}</span>}
                  {job.validation_errors.length > 0 && (
                    <span className="text-yellow-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />{job.validation_errors.length} warnings
                    </span>
                  )}
                  {job.completed_at && <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>Upload Migration File</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Source Platform</Label>
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="freepbx">FreePBX</SelectItem>
                  <SelectItem value="3cx">3CX</SelectItem>
                  <SelectItem value="asterisk">Asterisk</SelectItem>
                  <SelectItem value="csv">CSV Import</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>File</Label>
              <Input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
            <Button disabled={!file || uploadMutation.isPending} onClick={handleUpload}>
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Upload
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
