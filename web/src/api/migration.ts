import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface MigrationJob {
  id: string
  tenant_id: string
  source_platform: string
  status: string
  file_name: string
  total_records: number
  imported_records: number
  failed_records: number
  validation_errors: string[]
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface MigrationUpload {
  source_platform: string
  file_name: string
  file_content: string // base64
}

export function useMigrationJobs() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  return useQuery({
    queryKey: queryKeys.migration.jobs(tenantId!),
    queryFn: () => api.get(`/tenants/${tenantId}/migration/jobs`).then((r) => r.data as MigrationJob[]),
    enabled: !!tenantId,
  })
}

export function useUploadMigration() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: MigrationUpload) => api.post(`/tenants/${tenantId}/migration/upload`, data).then((r) => r.data as MigrationJob),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.migration.jobs(tenantId!) }),
  })
}

export function useValidateMigration() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.post(`/tenants/${tenantId}/migration/jobs/${jobId}/validate`).then((r) => r.data as MigrationJob),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.migration.jobs(tenantId!) }),
  })
}

export function useExecuteMigration() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.post(`/tenants/${tenantId}/migration/jobs/${jobId}/import`).then((r) => r.data as MigrationJob),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.migration.jobs(tenantId!) }),
  })
}
