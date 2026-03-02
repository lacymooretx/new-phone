import { useMutation } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

interface MfaChallengeResponse {
  mfa_required: boolean
  mfa_token: string
}

type LoginResponse = TokenResponse | MfaChallengeResponse

export function isMfaResponse(res: LoginResponse): res is MfaChallengeResponse {
  return "mfa_required" in res && res.mfa_required
}

export function useLogin() {
  return useMutation({
    mutationFn: (data: { email: string; password: string }) =>
      apiClient.post<LoginResponse>("/api/v1/auth/login", data),
  })
}

export function useMfaChallenge() {
  return useMutation({
    mutationFn: (data: { mfa_token: string; code: string }) =>
      apiClient.post<TokenResponse>("/api/v1/auth/mfa/challenge", data),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      apiClient.post("/api/v1/auth/change-password", data),
  })
}

interface MfaSetupResponse {
  totp_uri: string
  backup_codes: string[]
}

export function useSetupMfa() {
  return useMutation({
    mutationFn: () =>
      apiClient.post<MfaSetupResponse>("/api/v1/auth/mfa/setup", {}),
  })
}

export function useConfirmMfa() {
  return useMutation({
    mutationFn: (data: { code: string }) =>
      apiClient.post("/api/v1/auth/mfa/confirm", data),
  })
}

export function useDisableMfa() {
  return useMutation({
    mutationFn: (data: { password: string }) =>
      apiClient.post("/api/v1/auth/mfa/disable", data),
  })
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (data: { email: string }) =>
      apiClient.post("/api/v1/auth/forgot-password", data),
  })
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (data: { token: string; new_password: string }) =>
      apiClient.post("/api/v1/auth/reset-password", data),
  })
}
