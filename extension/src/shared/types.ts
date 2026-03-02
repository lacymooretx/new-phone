// Message types from content/popup → service worker
export type MessageType =
  | "AUTH_LOGIN"
  | "AUTH_LOGOUT"
  | "AUTH_STATUS"
  | "AUTH_MFA_COMPLETE"
  | "INITIATE_CALL"
  | "LOOKUP_NUMBER"
  | "GET_RECENT_CALLS"
  | "GET_ACTIVE_CALL"
  | "OPEN_WEB_CLIENT"
  | "GET_SETTINGS"
  | "SAVE_SETTINGS"
  | "TEST_CONNECTION"
  | "DISMISS_ERROR"

export interface ExtMessage {
  type: MessageType
  payload?: unknown
}

// Auth
export interface LoginPayload {
  email: string
  password: string
  apiBaseUrl: string
}

export interface MfaPayload {
  code: string
}

export interface AuthState {
  isAuthenticated: boolean
  mfaRequired?: boolean
  user?: UserInfo
}

export interface UserInfo {
  id: string
  email: string
  display_name: string
  tenant_id: string
  role: string
  extension_number?: string
  extension_id?: string
}

// Calls
export interface InitiateCallPayload {
  destination: string
  method?: "originate" | "web_client"
}

export interface LookupPayload {
  number: string
  tenantId: string
}

export interface OriginateResponse {
  status: string
  destination: string
  caller_extension: string
}

export interface ExtensionLookupResponse {
  extension_id: string | null
  extension_number: string | null
  display_name: string | null
  dnd_enabled: boolean
  agent_status: string | null
  is_internal: boolean
}

export interface NumberHistoryEntry {
  id: string
  direction: string
  caller_number: string
  caller_name: string
  called_number: string
  disposition: string
  duration_seconds: number
  start_time: string
}

// Active call state
export type CallState = "idle" | "ringing" | "connected" | "on_hold"

export interface ActiveCallInfo {
  state: CallState
  remote_number: string
  remote_name?: string
  direction: "inbound" | "outbound"
  started_at: string
}

// Settings
export interface ExtensionSettings {
  callMethod: "originate" | "web_client"
  blockedSites: string[]
  apiBaseUrl: string
  numberDetectionEnabled: boolean
  defaultCountryCode: string
}

// Error banner types
export type ErrorType = "connection" | "auth_expired" | "server_unreachable"

export interface AppError {
  type: ErrorType
  message: string
  dismissible: boolean
}

// Message response
export interface MessageResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
}
