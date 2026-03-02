import { create } from "zustand"
import i18next from "i18next"
import { decodeJwtPayload, type JwtPayload } from "@/lib/jwt"
import type { Role } from "@/lib/constants"

interface AuthUser {
  id: string
  tenantId: string
  role: Role
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  activeTenantId: string | null
  isAuthenticated: boolean
  isBootstrapping: boolean
  language: string

  setTokens: (accessToken: string, refreshToken: string) => void
  login: (accessToken: string, refreshToken: string) => void
  logout: () => void
  bootstrap: () => Promise<void>
  setActiveTenant: (tenantId: string) => void
  setLanguage: (lang: string) => void
}

function userFromToken(token: string): AuthUser | null {
  try {
    const payload: JwtPayload = decodeJwtPayload(token)
    return { id: payload.sub, tenantId: payload.tenant_id, role: payload.role }
  } catch {
    return null
  }
}

function languageFromToken(token: string): string | null {
  try {
    const payload: JwtPayload = decodeJwtPayload(token)
    return payload.language ?? null
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  activeTenantId: null,
  isAuthenticated: false,
  isBootstrapping: true,
  language: localStorage.getItem("language") || "en",

  setTokens: (accessToken, refreshToken) => {
    const user = userFromToken(accessToken)
    const lang = languageFromToken(accessToken)
    localStorage.setItem("refresh_token", refreshToken)
    if (lang) {
      localStorage.setItem("language", lang)
      void i18next.changeLanguage(lang)
    }
    set({
      accessToken,
      refreshToken,
      user,
      isAuthenticated: !!user,
      activeTenantId: get().activeTenantId || user?.tenantId || null,
      ...(lang ? { language: lang } : {}),
    })
  },

  login: (accessToken, refreshToken) => {
    const user = userFromToken(accessToken)
    const lang = languageFromToken(accessToken)
    localStorage.setItem("refresh_token", refreshToken)
    if (lang) {
      localStorage.setItem("language", lang)
      void i18next.changeLanguage(lang)
    }
    set({
      accessToken,
      refreshToken,
      user,
      isAuthenticated: !!user,
      activeTenantId: user?.tenantId || null,
      isBootstrapping: false,
      ...(lang ? { language: lang } : {}),
    })
  },

  logout: () => {
    localStorage.removeItem("refresh_token")
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeTenantId: null,
      isAuthenticated: false,
      isBootstrapping: false,
    })
  },

  bootstrap: async () => {
    const storedRefreshToken = localStorage.getItem("refresh_token")
    if (!storedRefreshToken) {
      set({ isBootstrapping: false })
      return
    }

    try {
      const res = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefreshToken }),
      })

      if (!res.ok) {
        get().logout()
        return
      }

      const data = await res.json()
      const user = userFromToken(data.access_token)
      localStorage.setItem("refresh_token", data.refresh_token)
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user,
        isAuthenticated: !!user,
        activeTenantId: user?.tenantId || null,
        isBootstrapping: false,
      })
    } catch {
      get().logout()
    }
  },

  setActiveTenant: (tenantId) => set({ activeTenantId: tenantId }),

  setLanguage: (lang) => {
    localStorage.setItem("language", lang)
    void i18next.changeLanguage(lang)
    set({ language: lang })
  },
}))
