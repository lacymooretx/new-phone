import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──────────────────────────────────────────────────────────

export interface AIProviderConfig {
  id: string
  tenant_id: string
  provider_name: string
  base_url: string | null
  model_id: string | null
  extra_config: Record<string, unknown> | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AIProviderConfigCreate {
  provider_name: string
  api_key: string
  base_url?: string | null
  model_id?: string | null
  extra_config?: Record<string, unknown> | null
}

export interface AIProviderConfigUpdate {
  api_key?: string
  base_url?: string | null
  model_id?: string | null
  extra_config?: Record<string, unknown> | null
  is_active?: boolean
}

export interface AIAgentContext {
  id: string
  tenant_id: string
  name: string
  display_name: string
  system_prompt: string
  greeting: string
  provider_mode: "monolithic" | "pipeline"
  monolithic_provider: string | null
  pipeline_stt: string | null
  pipeline_llm: string | null
  pipeline_tts: string | null
  pipeline_options: Record<string, unknown> | null
  voice_id: string | null
  language: string
  barge_in_enabled: boolean
  barge_in_sensitivity: string
  silence_timeout_ms: number
  max_call_duration_seconds: number
  available_tools: string[] | null
  escalation_rules: Record<string, unknown> | null
  knowledge_base: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AIAgentContextCreate {
  name: string
  display_name: string
  system_prompt: string
  greeting: string
  provider_mode: "monolithic" | "pipeline"
  monolithic_provider?: string | null
  pipeline_stt?: string | null
  pipeline_llm?: string | null
  pipeline_tts?: string | null
  pipeline_options?: Record<string, unknown> | null
  voice_id?: string | null
  language?: string
  barge_in_enabled?: boolean
  barge_in_sensitivity?: string
  silence_timeout_ms?: number
  max_call_duration_seconds?: number
  available_tools?: string[] | null
  escalation_rules?: Record<string, unknown> | null
  knowledge_base?: string | null
}

export interface AIAgentContextUpdate {
  display_name?: string
  system_prompt?: string
  greeting?: string
  provider_mode?: "monolithic" | "pipeline"
  monolithic_provider?: string | null
  pipeline_stt?: string | null
  pipeline_llm?: string | null
  pipeline_tts?: string | null
  pipeline_options?: Record<string, unknown> | null
  voice_id?: string | null
  language?: string
  barge_in_enabled?: boolean
  barge_in_sensitivity?: string
  silence_timeout_ms?: number
  max_call_duration_seconds?: number
  available_tools?: string[] | null
  escalation_rules?: Record<string, unknown> | null
  knowledge_base?: string | null
  is_active?: boolean
}

export interface AIAgentTool {
  id: string
  tenant_id: string
  name: string
  display_name: string
  description: string
  category: string
  parameters_schema: Record<string, unknown>
  webhook_url: string | null
  webhook_method: string
  mcp_server_url: string | null
  max_execution_time: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AIAgentToolCreate {
  name: string
  display_name: string
  description: string
  category: string
  parameters_schema: Record<string, unknown>
  webhook_url?: string | null
  webhook_method?: string
  webhook_headers?: Record<string, string> | null
  mcp_server_url?: string | null
  max_execution_time?: number
}

export interface AIAgentToolUpdate {
  display_name?: string
  description?: string
  parameters_schema?: Record<string, unknown>
  webhook_url?: string | null
  webhook_method?: string
  webhook_headers?: Record<string, string> | null
  mcp_server_url?: string | null
  max_execution_time?: number
  is_active?: boolean
}

export interface AIAgentConversation {
  id: string
  tenant_id: string
  context_id: string | null
  call_id: string
  caller_number: string
  caller_name: string | null
  provider_name: string
  outcome: string
  duration_seconds: number
  turn_count: number
  barge_in_count: number
  started_at: string
  ended_at: string | null
  created_at: string
}

export interface AIAgentConversationDetail extends AIAgentConversation {
  transcript: Array<{ speaker: string; text: string; timestamp_ms: number }>
  tool_calls: Array<{ tool_name: string; params: Record<string, unknown>; result: Record<string, unknown>; timestamp_ms: number }> | null
  summary: string | null
  transferred_to: string | null
  latency_metrics: Record<string, number> | null
  provider_cost_usd: number | null
}

export interface AIAgentStats {
  calls_today: number
  calls_this_week: number
  calls_this_month: number
  avg_duration_seconds: number
  avg_turn_response_ms: number
  transfer_rate: number
  outcomes: Record<string, number>
}

export interface AIProviderStatus {
  name: string
  display_name: string
  configured: boolean
  status: "connected" | "error" | "unconfigured"
}

// ── Provider Configs ──────────────────────────────────────────────

export function useAIProviderConfigs() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.providerConfigs(tenantId),
    queryFn: () => apiClient.get<AIProviderConfig[]>("/api/v1/ai-agents/provider-configs"),
    enabled: !!tenantId,
  })
}

export function useCreateAIProviderConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AIProviderConfigCreate) =>
      apiClient.post<AIProviderConfig>("/api/v1/ai-agents/provider-configs", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.providerConfigs(tenantId) }),
  })
}

export function useUpdateAIProviderConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: AIProviderConfigUpdate & { id: string }) =>
      apiClient.patch<AIProviderConfig>(`/api/v1/ai-agents/provider-configs/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.providerConfigs(tenantId) }),
  })
}

export function useDeleteAIProviderConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/api/v1/ai-agents/provider-configs/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.providerConfigs(tenantId) }),
  })
}

export function useTestAIProviderConfig() {
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<{ success: boolean; message: string }>(`/api/v1/ai-agents/provider-configs/${id}/test`),
  })
}

// ── Agent Contexts ──────────────────────────────────────────────

export function useAIAgentContexts() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.contexts(tenantId),
    queryFn: () => apiClient.get<AIAgentContext[]>("/api/v1/ai-agents/contexts"),
    enabled: !!tenantId,
  })
}

export function useAIAgentContext(id: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.contextDetail(tenantId, id),
    queryFn: () => apiClient.get<AIAgentContext>(`/api/v1/ai-agents/contexts/${id}`),
    enabled: !!tenantId && !!id,
  })
}

export function useCreateAIAgentContext() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AIAgentContextCreate) =>
      apiClient.post<AIAgentContext>("/api/v1/ai-agents/contexts", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.contexts(tenantId) }),
  })
}

export function useUpdateAIAgentContext() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: AIAgentContextUpdate & { id: string }) =>
      apiClient.put<AIAgentContext>(`/api/v1/ai-agents/contexts/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.contexts(tenantId) }),
  })
}

export function useDeleteAIAgentContext() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/api/v1/ai-agents/contexts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.contexts(tenantId) }),
  })
}

export function useTestAIAgentContext() {
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<{ success: boolean; message: string }>(`/api/v1/ai-agents/contexts/${id}/test`),
  })
}

// ── Tools ──────────────────────────────────────────────────────

export function useAIAgentTools() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.tools(tenantId),
    queryFn: () => apiClient.get<AIAgentTool[]>("/api/v1/ai-agents/tools"),
    enabled: !!tenantId,
  })
}

export function useCreateAIAgentTool() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AIAgentToolCreate) =>
      apiClient.post<AIAgentTool>("/api/v1/ai-agents/tools", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.tools(tenantId) }),
  })
}

export function useUpdateAIAgentTool() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: AIAgentToolUpdate & { id: string }) =>
      apiClient.patch<AIAgentTool>(`/api/v1/ai-agents/tools/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.tools(tenantId) }),
  })
}

export function useDeleteAIAgentTool() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/api/v1/ai-agents/tools/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.aiAgents.tools(tenantId) }),
  })
}

// ── Conversations ──────────────────────────────────────────────

export function useAIAgentConversations(params?: Record<string, string>) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.conversations(tenantId, params),
    queryFn: () => apiClient.get<AIAgentConversation[]>("/api/v1/ai-agents/conversations", params),
    enabled: !!tenantId,
  })
}

export function useAIAgentConversation(id: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.conversationDetail(tenantId, id),
    queryFn: () => apiClient.get<AIAgentConversationDetail>(`/api/v1/ai-agents/conversations/${id}`),
    enabled: !!tenantId && !!id,
  })
}

// ── Stats & Providers ──────────────────────────────────────────

export function useAIAgentStats() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.stats(tenantId),
    queryFn: () => apiClient.get<AIAgentStats>("/api/v1/ai-agents/stats"),
    enabled: !!tenantId,
  })
}

export function useAIAgentProviders() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.aiAgents.providers(tenantId),
    queryFn: () => apiClient.get<AIProviderStatus[]>("/api/v1/ai-agents/providers"),
    enabled: !!tenantId,
  })
}
