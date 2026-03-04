import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface SurveyTemplate {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_active: boolean
  intro_prompt: string | null
  thank_you_prompt: string | null
  questions: Array<{ question_text: string; question_type: string; min_value?: number; max_value?: number }>
  created_at: string
  updated_at: string
}

export interface SurveyTemplateCreate {
  name: string
  description?: string | null
  intro_prompt?: string | null
  thank_you_prompt?: string | null
  questions: Array<{ question_text: string; question_type: string; min_value?: number; max_value?: number }>
}

export interface SurveyResponseItem {
  id: string
  tenant_id: string
  template_id: string
  queue_id: string | null
  agent_extension: string | null
  caller_number: string
  call_uuid: string | null
  answers: Record<string, unknown>
  overall_score: number | null
  completed_at: string | null
  created_at: string
}

export interface SurveyAnalytics {
  template_id: string
  template_name: string
  total_responses: number
  avg_overall_score: number | null
  per_question_avg: Record<string, number>
  per_queue_avg: Record<string, number>
  per_agent_avg: Record<string, number>
}

export function useSurveyTemplates() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.surveys.templates(tenantId),
    queryFn: () => apiClient.get<SurveyTemplate[]>(`tenants/${tenantId}/surveys/templates`),
    enabled: !!tenantId,
  })
}

export function useCreateSurveyTemplate() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SurveyTemplateCreate) =>
      apiClient.post<SurveyTemplate>(`tenants/${tenantId}/surveys/templates`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.surveys.templates(tenantId) }),
  })
}

export function useDeleteSurveyTemplate() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`tenants/${tenantId}/surveys/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.surveys.templates(tenantId) }),
  })
}

export function useSurveyResponses(templateId?: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.surveys.responses(tenantId, templateId),
    queryFn: () => {
      const params: Record<string, string> = {}
      if (templateId) params.template_id = templateId
      return apiClient.get<{ items: SurveyResponseItem[]; total: number }>(`tenants/${tenantId}/surveys/responses`, params)
    },
    enabled: !!tenantId,
  })
}

export function useSurveyAnalytics(templateId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.surveys.analytics(tenantId, templateId),
    queryFn: () => apiClient.get<SurveyAnalytics>(`tenants/${tenantId}/surveys/templates/${templateId}/analytics`),
    enabled: !!tenantId && !!templateId,
  })
}
