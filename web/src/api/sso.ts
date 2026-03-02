import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──────────────────────────────────────────────────────────

export interface SSOCheckDomainResponse {
  sso_available: boolean
  provider_type: string | null
  display_name: string | null
  enforce_sso: boolean
}

export interface SSOInitiateResponse {
  authorization_url: string
  state: string
}

export interface SSOProviderConfig {
  id: string
  tenant_id: string
  provider_type: "microsoft" | "google"
  display_name: string
  client_id: string
  issuer_url: string
  discovery_url: string
  scopes: string
  auto_provision: boolean
  default_role: string
  enforce_sso: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SSOProviderConfigCreate {
  provider_type: "microsoft" | "google"
  display_name: string
  client_id: string
  client_secret: string
  issuer_url: string
  scopes?: string
  auto_provision?: boolean
  default_role?: string
  enforce_sso?: boolean
}

export interface SSOProviderConfigUpdate {
  display_name?: string
  client_id?: string
  client_secret?: string
  issuer_url?: string
  scopes?: string
  auto_provision?: boolean
  default_role?: string
  enforce_sso?: boolean
  is_active?: boolean
}

export interface SSORoleMapping {
  id: string
  external_group_id: string
  external_group_name: string | null
  pbx_role: string
}

export interface SSORoleMappingCreate {
  external_group_id: string
  external_group_name?: string | null
  pbx_role: string
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// ── SSO Auth Flow ──────────────────────────────────────────────────

export function useSSOCheckDomain() {
  return useMutation({
    mutationFn: (email: string) =>
      apiClient.get<SSOCheckDomainResponse>("/api/v1/auth/sso/check-domain", { email }),
  })
}

export function useSSOInitiate() {
  return useMutation({
    mutationFn: (data: { email: string }) =>
      apiClient.post<SSOInitiateResponse>("/api/v1/auth/sso/initiate", data),
  })
}

export function useSSOComplete() {
  return useMutation({
    mutationFn: (data: { state: string }) =>
      apiClient.post<TokenResponse>("/api/v1/auth/sso/complete", data),
  })
}

// ── SSO Config CRUD ──────────────────────────────────────────────

export function useSSOConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sso.config(tenantId),
    queryFn: () => apiClient.get<SSOProviderConfig>("/api/v1/sso-config"),
    enabled: !!tenantId,
    retry: false,
  })
}

export function useCreateSSOConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SSOProviderConfigCreate) =>
      apiClient.post<SSOProviderConfig>("/api/v1/sso-config", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sso.config(tenantId) }),
  })
}

export function useUpdateSSOConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SSOProviderConfigUpdate) =>
      apiClient.patch<SSOProviderConfig>("/api/v1/sso-config", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sso.config(tenantId) }),
  })
}

export function useDeleteSSOConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.delete("/api/v1/sso-config"),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sso.config(tenantId) }),
  })
}

export function useTestSSOConfig() {
  return useMutation({
    mutationFn: () => apiClient.post<{ success: boolean; message: string }>("/api/v1/sso-config/test"),
  })
}

// ── Role Mappings ──────────────────────────────────────────────────

export function useSSORoleMappings() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sso.roleMappings(tenantId),
    queryFn: () => apiClient.get<SSORoleMapping[]>("/api/v1/sso-config/role-mappings"),
    enabled: !!tenantId,
  })
}

export function useAddRoleMapping() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SSORoleMappingCreate) =>
      apiClient.post<SSORoleMapping>("/api/v1/sso-config/role-mappings", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sso.roleMappings(tenantId) }),
  })
}

export function useDeleteRoleMapping() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (mappingId: string) =>
      apiClient.delete(`/api/v1/sso-config/role-mappings/${mappingId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sso.roleMappings(tenantId) }),
  })
}
