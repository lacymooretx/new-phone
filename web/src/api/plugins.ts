import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ─────────────────────────────────────────────────────────────

export interface Plugin {
  id: string
  name: string
  version: string
  author: string
  description: string
  icon_url: string | null
  homepage_url: string | null
  manifest: Record<string, unknown>
  permissions: string[]
  hook_types: string[]
  is_published: boolean
  webhook_url: string | null
  created_at: string
  updated_at: string
}

export interface TenantPlugin {
  id: string
  tenant_id: string
  plugin_id: string
  status: string
  config: Record<string, unknown> | null
  installed_at: string
  installed_by_user_id: string | null
  plugin: Plugin
  created_at: string
  updated_at: string
}

export interface PluginEventLog {
  id: string
  tenant_id: string
  plugin_id: string
  hook_type: string
  payload: Record<string, unknown>
  response_status: number | null
  error_message: string | null
  created_at: string
}

// ── Hooks ─────────────────────────────────────────────────────────────

export function useAvailablePlugins() {
  return useQuery({
    queryKey: queryKeys.plugins.catalog(),
    queryFn: () => apiClient.get<Plugin[]>("plugins"),
  })
}

export function useInstalledPlugins() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.plugins.installed(tenantId),
    queryFn: () =>
      apiClient.get<TenantPlugin[]>(`tenants/${tenantId}/plugins`),
    enabled: !!tenantId,
  })
}

export function useInstallPlugin() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pluginId: string) =>
      apiClient.post<TenantPlugin>(
        `tenants/${tenantId}/plugins/${pluginId}/install`
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.plugins.installed(tenantId) })
      qc.invalidateQueries({ queryKey: queryKeys.plugins.catalog() })
    },
  })
}

export function useUninstallPlugin() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pluginId: string) =>
      apiClient.post(`tenants/${tenantId}/plugins/${pluginId}/uninstall`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.plugins.installed(tenantId) })
      qc.invalidateQueries({ queryKey: queryKeys.plugins.catalog() })
    },
  })
}

export function useActivatePlugin() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pluginId: string) =>
      apiClient.post<TenantPlugin>(
        `tenants/${tenantId}/plugins/${pluginId}/activate`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.plugins.installed(tenantId) }),
  })
}

export function useDeactivatePlugin() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pluginId: string) =>
      apiClient.post<TenantPlugin>(
        `tenants/${tenantId}/plugins/${pluginId}/deactivate`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.plugins.installed(tenantId) }),
  })
}

export function useUpdatePluginConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      pluginId,
      config,
    }: {
      pluginId: string
      config: Record<string, unknown>
    }) =>
      apiClient.put<TenantPlugin>(
        `tenants/${tenantId}/plugins/${pluginId}/config`,
        { config }
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.plugins.installed(tenantId) }),
  })
}

export function usePluginEventLogs(pluginId: string, page: number = 1) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.plugins.logs(tenantId, pluginId, page),
    queryFn: () =>
      apiClient.get<{
        items: PluginEventLog[]
        total: number
        page: number
        per_page: number
      }>(`tenants/${tenantId}/plugins/${pluginId}/logs`, {
        page: String(page),
      }),
    enabled: !!tenantId && !!pluginId,
  })
}
