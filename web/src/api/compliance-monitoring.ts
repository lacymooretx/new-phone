import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──

export interface ComplianceRule {
  id: string
  tenant_id: string
  name: string
  description: string | null
  rule_text: string
  category: string
  severity: string
  scope_type: string
  scope_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ComplianceRuleCreate {
  name: string
  description?: string | null
  rule_text: string
  category?: string
  severity?: string
  scope_type?: string
  scope_id?: string | null
}

export interface ComplianceRuleUpdate {
  name?: string
  description?: string | null
  rule_text?: string
  category?: string
  severity?: string
  scope_type?: string
  scope_id?: string | null
  is_active?: boolean
}

export interface ComplianceRuleResult {
  id: string
  tenant_id: string
  evaluation_id: string
  rule_id: string | null
  rule_name_snapshot: string
  rule_text_snapshot: string
  result: string
  explanation: string | null
  evidence: string | null
  created_at: string
}

export interface ComplianceEvaluation {
  id: string
  tenant_id: string
  cdr_id: string | null
  ai_conversation_id: string | null
  overall_score: number | null
  rules_passed: number
  rules_failed: number
  rules_not_applicable: number
  is_flagged: boolean
  status: string
  provider_name: string | null
  reviewed_by_id: string | null
  reviewed_at: string | null
  review_notes: string | null
  evaluated_at: string | null
  created_at: string
}

export interface ComplianceEvaluationDetail extends ComplianceEvaluation {
  transcript_text: string
  rule_results: ComplianceRuleResult[]
}

export interface ComplianceSummary {
  total_evaluations: number
  average_score: number | null
  flagged_count: number
  flagged_rate: number
  pass_rate: number
  status_breakdown: Record<string, number>
}

export interface ComplianceAgentScore {
  extension_id: string
  extension_number: string
  evaluation_count: number
  average_score: number | null
  flagged_count: number
}

export interface ComplianceQueueScore {
  queue_id: string
  queue_name: string
  evaluation_count: number
  average_score: number | null
  flagged_count: number
}

export interface ComplianceRuleEffectiveness {
  rule_id: string
  rule_name: string
  severity: string
  total_evaluated: number
  pass_count: number
  fail_count: number
  not_applicable_count: number
  fail_rate: number
}

export interface ComplianceTrendPoint {
  period: string
  evaluation_count: number
  average_score: number | null
  flagged_count: number
}

// ── Rule hooks ──

export function useComplianceRules(params?: {
  category?: string
  scope_type?: string
  is_active?: boolean
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.category) queryParams.category = params.category
  if (params?.scope_type) queryParams.scope_type = params.scope_type
  if (params?.is_active !== undefined) queryParams.is_active = String(params.is_active)

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.rules(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceRule[]>(
        `tenants/${tenantId}/compliance-monitoring/rules`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceRule(ruleId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.complianceMonitoring.ruleDetail(tenantId, ruleId),
    queryFn: () =>
      apiClient.get<ComplianceRule>(
        `tenants/${tenantId}/compliance-monitoring/rules/${ruleId}`
      ),
    enabled: !!tenantId && !!ruleId,
  })
}

export function useCreateComplianceRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ComplianceRuleCreate) =>
      apiClient.post<ComplianceRule>(
        `tenants/${tenantId}/compliance-monitoring/rules`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.complianceMonitoring.all(tenantId),
      }),
  })
}

export function useUpdateComplianceRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & ComplianceRuleUpdate) =>
      apiClient.patch<ComplianceRule>(
        `tenants/${tenantId}/compliance-monitoring/rules/${id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.complianceMonitoring.all(tenantId),
      }),
  })
}

export function useDeleteComplianceRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(
        `tenants/${tenantId}/compliance-monitoring/rules/${id}`
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.complianceMonitoring.all(tenantId),
      }),
  })
}

// ── Evaluation hooks ──

export function useComplianceEvaluations(params?: {
  is_flagged?: boolean
  status?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.is_flagged !== undefined) queryParams.is_flagged = String(params.is_flagged)
  if (params?.status) queryParams.status = params.status
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to
  queryParams.limit = String(params?.limit ?? 50)
  queryParams.offset = String(params?.offset ?? 0)

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.evaluations(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceEvaluation[]>(
        `tenants/${tenantId}/compliance-monitoring/evaluations`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceEvaluation(evaluationId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.complianceMonitoring.evaluationDetail(tenantId, evaluationId),
    queryFn: () =>
      apiClient.get<ComplianceEvaluationDetail>(
        `tenants/${tenantId}/compliance-monitoring/evaluations/${evaluationId}`
      ),
    enabled: !!tenantId && !!evaluationId,
  })
}

export function useTriggerComplianceEvaluation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { cdr_id?: string; ai_conversation_id?: string }) =>
      apiClient.post<ComplianceEvaluation>(
        `tenants/${tenantId}/compliance-monitoring/evaluations`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.complianceMonitoring.all(tenantId),
      }),
  })
}

export function useReviewComplianceEvaluation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      evaluationId,
      review_notes,
    }: {
      evaluationId: string
      review_notes?: string | null
    }) =>
      apiClient.patch<ComplianceEvaluation>(
        `tenants/${tenantId}/compliance-monitoring/evaluations/${evaluationId}/review`,
        { review_notes }
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.complianceMonitoring.all(tenantId),
      }),
  })
}

// ── Analytics hooks ──

export function useComplianceSummary(params?: {
  date_from?: string
  date_to?: string
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.summary(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceSummary>(
        `tenants/${tenantId}/compliance-monitoring/analytics/summary`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceAgentScores(params?: {
  date_from?: string
  date_to?: string
  limit?: number
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to
  if (params?.limit) queryParams.limit = String(params.limit)

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.agentScores(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceAgentScore[]>(
        `tenants/${tenantId}/compliance-monitoring/analytics/agent-scores`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceQueueScores(params?: {
  date_from?: string
  date_to?: string
  limit?: number
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to
  if (params?.limit) queryParams.limit = String(params.limit)

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.queueScores(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceQueueScore[]>(
        `tenants/${tenantId}/compliance-monitoring/analytics/queue-scores`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceRuleEffectiveness(params?: {
  date_from?: string
  date_to?: string
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.ruleEffectiveness(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceRuleEffectiveness[]>(
        `tenants/${tenantId}/compliance-monitoring/analytics/rule-effectiveness`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useComplianceTrend(params?: {
  date_from?: string
  date_to?: string
  granularity?: string
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.date_from) queryParams.date_from = params.date_from
  if (params?.date_to) queryParams.date_to = params.date_to
  if (params?.granularity) queryParams.granularity = params.granularity

  return useQuery({
    queryKey: queryKeys.complianceMonitoring.trend(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<ComplianceTrendPoint[]>(
        `tenants/${tenantId}/compliance-monitoring/analytics/trend`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}
