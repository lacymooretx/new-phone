import type { AppError } from "@/shared/types"

const ERROR_CONFIG: Record<
  string,
  { icon: string; actionLabel: string; actionType: "retry" | "relogin" }
> = {
  connection: {
    icon: "!",
    actionLabel: "Retry",
    actionType: "retry",
  },
  auth_expired: {
    icon: "!",
    actionLabel: "Sign In",
    actionType: "relogin",
  },
  server_unreachable: {
    icon: "!",
    actionLabel: "Retry",
    actionType: "retry",
  },
}

export function ErrorBanner({
  error,
  onDismiss,
  onRetry,
  onRelogin,
}: {
  error: AppError
  onDismiss: () => void
  onRetry: () => void
  onRelogin: () => void
}) {
  const config = ERROR_CONFIG[error.type] || ERROR_CONFIG.connection

  const bgColor =
    error.type === "auth_expired" ? "#fffbeb" : "#fef2f2"
  const borderColor =
    error.type === "auth_expired" ? "#fde68a" : "#fecaca"
  const iconColor =
    error.type === "auth_expired" ? "#d97706" : "#dc2626"
  const textColor =
    error.type === "auth_expired" ? "#92400e" : "#991b1b"

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "8px",
        padding: "8px 10px",
        background: bgColor,
        border: `1px solid ${borderColor}`,
        borderRadius: "6px",
        marginBottom: "8px",
        fontSize: "12px",
        color: textColor,
      }}
    >
      {/* Icon */}
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: "16px",
          height: "16px",
          borderRadius: "50%",
          background: iconColor,
          color: "#fff",
          fontSize: "10px",
          fontWeight: "700",
          flexShrink: 0,
          marginTop: "1px",
        }}
      >
        {config.icon}
      </span>

      {/* Message + action */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ lineHeight: "1.4" }}>{error.message}</div>
        <button
          onClick={
            config.actionType === "relogin" ? onRelogin : onRetry
          }
          style={actionBtnStyle}
        >
          {config.actionLabel}
        </button>
      </div>

      {/* Dismiss */}
      {error.dismissible && (
        <button
          onClick={onDismiss}
          style={dismissBtnStyle}
          title="Dismiss"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M2.5 2.5L9.5 9.5M9.5 2.5L2.5 9.5"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
      )}
    </div>
  )
}

// --- Styles ---

const actionBtnStyle: Record<string, string> = {
  marginTop: "4px",
  padding: "3px 8px",
  background: "rgba(0,0,0,0.08)",
  border: "none",
  borderRadius: "4px",
  fontSize: "11px",
  fontWeight: "600",
  cursor: "pointer",
  color: "inherit",
  fontFamily: "inherit",
}

const dismissBtnStyle: Record<string, string> = {
  padding: "2px",
  background: "transparent",
  border: "none",
  cursor: "pointer",
  color: "inherit",
  opacity: "0.6",
  flexShrink: "0",
}
