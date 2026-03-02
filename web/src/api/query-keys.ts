export const queryKeys = {
  auth: {
    all: ["auth"] as const,
  },
  tenants: {
    all: ["tenants"] as const,
    list: () => [...queryKeys.tenants.all, "list"] as const,
    detail: (id: string) => [...queryKeys.tenants.all, "detail", id] as const,
    health: () => [...queryKeys.tenants.all, "health"] as const,
  },
  extensions: {
    all: (tenantId: string) => ["extensions", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.extensions.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.extensions.all(tenantId), "detail", id] as const,
  },
  users: {
    all: (tenantId: string) => ["users", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.users.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.users.all(tenantId), "detail", id] as const,
  },
  cdrs: {
    all: (tenantId: string) => ["cdrs", tenantId] as const,
    list: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.cdrs.all(tenantId), "list", filters] as const,
  },
  recordings: {
    all: (tenantId: string) => ["recordings", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.recordings.all(tenantId), "list"] as const,
    playback: (tenantId: string, id: string) => [...queryKeys.recordings.all(tenantId), "playback", id] as const,
  },
  voicemail: {
    boxes: (tenantId: string) => ["voicemail", tenantId, "boxes"] as const,
    messages: (tenantId: string, boxId: string) => ["voicemail", tenantId, "messages", boxId] as const,
    playback: (tenantId: string, boxId: string, msgId: string) => ["voicemail", tenantId, "playback", boxId, msgId] as const,
  },
  ringGroups: {
    all: (tenantId: string) => ["ringGroups", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.ringGroups.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.ringGroups.all(tenantId), "detail", id] as const,
  },
  queues: {
    all: (tenantId: string) => ["queues", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.queues.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.queues.all(tenantId), "detail", id] as const,
    stats: (tenantId: string) => [...queryKeys.queues.all(tenantId), "stats"] as const,
    agentStatus: (tenantId: string) => [...queryKeys.queues.all(tenantId), "agentStatus"] as const,
  },
  parkingLots: {
    all: (tenantId: string) => ["parkingLots", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.parkingLots.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.parkingLots.all(tenantId), "detail", id] as const,
    slots: (tenantId: string) => [...queryKeys.parkingLots.all(tenantId), "slots"] as const,
    lotSlots: (tenantId: string, lotId: string) => [...queryKeys.parkingLots.all(tenantId), "lotSlots", lotId] as const,
  },
  ivrMenus: {
    all: (tenantId: string) => ["ivrMenus", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.ivrMenus.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.ivrMenus.all(tenantId), "detail", id] as const,
  },
  conferences: {
    all: (tenantId: string) => ["conferences", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.conferences.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.conferences.all(tenantId), "detail", id] as const,
  },
  pageGroups: {
    all: (tenantId: string) => ["pageGroups", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.pageGroups.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.pageGroups.all(tenantId), "detail", id] as const,
  },
  sipTrunks: {
    all: (tenantId: string) => ["sipTrunks", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.sipTrunks.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.sipTrunks.all(tenantId), "detail", id] as const,
  },
  dids: {
    all: (tenantId: string) => ["dids", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.dids.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.dids.all(tenantId), "detail", id] as const,
    search: (tenantId: string, params?: Record<string, unknown>) => [...queryKeys.dids.all(tenantId), "search", params] as const,
  },
  portRequests: {
    all: (tenantId: string) => ["portRequests", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.portRequests.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.portRequests.all(tenantId), "detail", id] as const,
    history: (tenantId: string, id: string) => [...queryKeys.portRequests.all(tenantId), "history", id] as const,
  },
  inboundRoutes: {
    all: (tenantId: string) => ["inboundRoutes", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.inboundRoutes.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.inboundRoutes.all(tenantId), "detail", id] as const,
  },
  outboundRoutes: {
    all: (tenantId: string) => ["outboundRoutes", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.outboundRoutes.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.outboundRoutes.all(tenantId), "detail", id] as const,
  },
  audioPrompts: {
    all: (tenantId: string) => ["audioPrompts", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.audioPrompts.all(tenantId), "list"] as const,
    playback: (tenantId: string, id: string) => [...queryKeys.audioPrompts.all(tenantId), "playback", id] as const,
  },
  timeConditions: {
    all: (tenantId: string) => ["timeConditions", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.timeConditions.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.timeConditions.all(tenantId), "detail", id] as const,
  },
  holidayCalendars: {
    all: (tenantId: string) => ["holidayCalendars", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.holidayCalendars.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.holidayCalendars.all(tenantId), "detail", id] as const,
  },
  callerIdRules: {
    all: (tenantId: string) => ["callerIdRules", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.callerIdRules.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.callerIdRules.all(tenantId), "detail", id] as const,
  },
  phoneModels: {
    all: ["phoneModels"] as const,
    list: () => [...queryKeys.phoneModels.all, "list"] as const,
    detail: (id: string) => [...queryKeys.phoneModels.all, "detail", id] as const,
  },
  devices: {
    all: (tenantId: string) => ["devices", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.devices.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.devices.all(tenantId), "detail", id] as const,
    keys: (tenantId: string, deviceId: string) => [...queryKeys.devices.all(tenantId), "keys", deviceId] as const,
  },
  webrtc: {
    all: ["webrtc"] as const,
    credentials: () => [...queryKeys.webrtc.all, "credentials"] as const,
  },
  followMe: {
    all: (tenantId: string) => ["followMe", tenantId] as const,
    detail: (tenantId: string, extensionId: string) => [...queryKeys.followMe.all(tenantId), "detail", extensionId] as const,
  },
  auditLogs: {
    all: ["auditLogs"] as const,
    list: (filters?: Record<string, string>) => [...queryKeys.auditLogs.all, "list", filters] as const,
  },
  dispositionCodeLists: {
    all: (tenantId: string) => ["dispositionCodeLists", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.dispositionCodeLists.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.dispositionCodeLists.all(tenantId), "detail", id] as const,
  },
  sms: {
    all: (tenantId: string) => ["sms", tenantId] as const,
    conversations: (tenantId: string, state?: string, queueId?: string) => [...queryKeys.sms.all(tenantId), "conversations", state, queueId] as const,
    conversationDetail: (tenantId: string, id: string) => [...queryKeys.sms.all(tenantId), "conversation", id] as const,
    messages: (tenantId: string, conversationId: string) => [...queryKeys.sms.all(tenantId), "messages", conversationId] as const,
    notes: (tenantId: string, conversationId: string) => [...queryKeys.sms.all(tenantId), "notes", conversationId] as const,
    providers: (tenantId: string) => [...queryKeys.sms.all(tenantId), "providers"] as const,
  },
  sso: {
    config: (tenantId: string) => ["sso", tenantId, "config"] as const,
    roleMappings: (tenantId: string) => ["sso", tenantId, "roleMappings"] as const,
  },
  connectwise: {
    config: (tenantId: string) => ["connectwise", tenantId, "config"] as const,
    companyMappings: (tenantId: string) => ["connectwise", tenantId, "companyMappings"] as const,
    companySearch: (tenantId: string, q: string) => ["connectwise", tenantId, "companySearch", q] as const,
    boards: (tenantId: string) => ["connectwise", tenantId, "boards"] as const,
    boardStatuses: (tenantId: string, boardId: number) => ["connectwise", tenantId, "boardStatuses", boardId] as const,
    boardTypes: (tenantId: string, boardId: number) => ["connectwise", tenantId, "boardTypes", boardId] as const,
    ticketLogs: (tenantId: string, filters?: Record<string, string>) => ["connectwise", tenantId, "ticketLogs", filters] as const,
    ticketLogStats: (tenantId: string) => ["connectwise", tenantId, "ticketLogStats"] as const,
  },
  aiAgents: {
    all: (tenantId: string) => ["aiAgents", tenantId] as const,
    providerConfigs: (tenantId: string) => [...queryKeys.aiAgents.all(tenantId), "providerConfigs"] as const,
    contexts: (tenantId: string) => [...queryKeys.aiAgents.all(tenantId), "contexts"] as const,
    contextDetail: (tenantId: string, id: string) => [...queryKeys.aiAgents.all(tenantId), "context", id] as const,
    tools: (tenantId: string) => [...queryKeys.aiAgents.all(tenantId), "tools"] as const,
    conversations: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.aiAgents.all(tenantId), "conversations", filters] as const,
    conversationDetail: (tenantId: string, id: string) => [...queryKeys.aiAgents.all(tenantId), "conversation", id] as const,
    stats: (tenantId: string) => [...queryKeys.aiAgents.all(tenantId), "stats"] as const,
    providers: (tenantId: string) => [...queryKeys.aiAgents.all(tenantId), "providers"] as const,
  },
  compliance: {
    all: (tenantId: string) => ["compliance", tenantId] as const,
    lists: (tenantId: string) => [...queryKeys.compliance.all(tenantId), "lists"] as const,
    listDetail: (tenantId: string, id: string) => [...queryKeys.compliance.all(tenantId), "list", id] as const,
    entries: (tenantId: string, listId: string, page?: number) => [...queryKeys.compliance.all(tenantId), "entries", listId, page] as const,
    consentRecords: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.compliance.all(tenantId), "consentRecords", filters] as const,
    settings: (tenantId: string) => [...queryKeys.compliance.all(tenantId), "settings"] as const,
    auditLog: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.compliance.all(tenantId), "auditLog", filters] as const,
    dncCheck: (tenantId: string, phone: string) => [...queryKeys.compliance.all(tenantId), "dncCheck", phone] as const,
  },
  complianceMonitoring: {
    all: (tenantId: string) => ["complianceMonitoring", tenantId] as const,
    rules: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "rules", filters] as const,
    ruleDetail: (tenantId: string, id: string) => [...queryKeys.complianceMonitoring.all(tenantId), "rule", id] as const,
    evaluations: (tenantId: string, filters?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "evaluations", filters] as const,
    evaluationDetail: (tenantId: string, id: string) => [...queryKeys.complianceMonitoring.all(tenantId), "evaluation", id] as const,
    summary: (tenantId: string, params?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "summary", params] as const,
    agentScores: (tenantId: string, params?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "agentScores", params] as const,
    queueScores: (tenantId: string, params?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "queueScores", params] as const,
    ruleEffectiveness: (tenantId: string, params?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "ruleEffectiveness", params] as const,
    trend: (tenantId: string, params?: Record<string, string>) => [...queryKeys.complianceMonitoring.all(tenantId), "trend", params] as const,
  },
  analytics: {
    all: (tenantId: string) => ["analytics", tenantId] as const,
    summary: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "summary", params] as const,
    volumeTrend: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "volumeTrend", params] as const,
    extensionActivity: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "extensionActivity", params] as const,
    didUsage: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "didUsage", params] as const,
    durationDistribution: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "durationDistribution", params] as const,
    topCallers: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "topCallers", params] as const,
    hourlyDistribution: (tenantId: string, params?: Record<string, string>) => [...queryKeys.analytics.all(tenantId), "hourlyDistribution", params] as const,
    mspOverview: () => ["analytics", "mspOverview"] as const,
  },
  bossAdmin: {
    all: (tenantId: string) => ["bossAdmin", tenantId] as const,
    relationships: (tenantId: string) => [...queryKeys.bossAdmin.all(tenantId), "relationships"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.bossAdmin.all(tenantId), id] as const,
    myExecutives: (tenantId: string) => [...queryKeys.bossAdmin.all(tenantId), "my-executives"] as const,
    myAssistants: (tenantId: string) => [...queryKeys.bossAdmin.all(tenantId), "my-assistants"] as const,
  },
  sites: {
    all: (tenantId: string) => ["sites", tenantId] as const,
    list: (tenantId: string) => [...queryKeys.sites.all(tenantId), "list"] as const,
    detail: (tenantId: string, id: string) => [...queryKeys.sites.all(tenantId), "detail", id] as const,
    summaries: (tenantId: string) => [...queryKeys.sites.all(tenantId), "summaries"] as const,
  },
  wfm: {
    all: (tenantId: string) => ["wfm", tenantId] as const,
    shifts: (tenantId: string) => [...queryKeys.wfm.all(tenantId), "shifts"] as const,
    schedule: (tenantId: string, dateFrom?: string, dateTo?: string, extensionId?: string) =>
      [...queryKeys.wfm.all(tenantId), "schedule", dateFrom, dateTo, extensionId] as const,
    scheduleOverview: (tenantId: string, dateFrom?: string, dateTo?: string) =>
      [...queryKeys.wfm.all(tenantId), "scheduleOverview", dateFrom, dateTo] as const,
    timeOff: (tenantId: string, filters?: Record<string, string>) =>
      [...queryKeys.wfm.all(tenantId), "timeOff", filters] as const,
    forecastConfigs: (tenantId: string) =>
      [...queryKeys.wfm.all(tenantId), "forecastConfigs"] as const,
    hourlyVolume: (tenantId: string, queueId: string, dateFrom?: string, dateTo?: string) =>
      [...queryKeys.wfm.all(tenantId), "hourlyVolume", queueId, dateFrom, dateTo] as const,
    dailyVolume: (tenantId: string, queueId: string, dateFrom?: string, dateTo?: string) =>
      [...queryKeys.wfm.all(tenantId), "dailyVolume", queueId, dateFrom, dateTo] as const,
    forecast: (tenantId: string, queueId: string) =>
      [...queryKeys.wfm.all(tenantId), "forecast", queueId] as const,
    staffingSummary: (tenantId: string) =>
      [...queryKeys.wfm.all(tenantId), "staffingSummary"] as const,
  },
}
