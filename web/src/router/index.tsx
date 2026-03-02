import { lazy, Suspense } from "react"
import { createBrowserRouter } from "react-router"
import { Loader2 } from "lucide-react"
import { AuthGuard } from "@/components/auth/auth-guard"
import { AppLayout } from "@/components/layout/app-layout"

const LoginPage = lazy(() => import("@/pages/login/login-page").then((m) => ({ default: m.LoginPage })))
const DashboardPage = lazy(() => import("@/pages/dashboard/dashboard-page").then((m) => ({ default: m.DashboardPage })))
const ExtensionsPage = lazy(() => import("@/pages/extensions/extensions-page").then((m) => ({ default: m.ExtensionsPage })))
const FollowMePage = lazy(() => import("@/pages/extensions/follow-me-page").then((m) => ({ default: m.FollowMePage })))
const UsersPage = lazy(() => import("@/pages/users/users-page").then((m) => ({ default: m.UsersPage })))
const CdrsPage = lazy(() => import("@/pages/cdrs/cdrs-page").then((m) => ({ default: m.CdrsPage })))
const RecordingsPage = lazy(() => import("@/pages/recordings/recordings-page").then((m) => ({ default: m.RecordingsPage })))
const VoicemailPage = lazy(() => import("@/pages/voicemail/voicemail-page").then((m) => ({ default: m.VoicemailPage })))
const TenantSettingsPage = lazy(() => import("@/pages/tenant-settings/tenant-settings-page").then((m) => ({ default: m.TenantSettingsPage })))
const TenantsPage = lazy(() => import("@/pages/tenants/tenants-page").then((m) => ({ default: m.TenantsPage })))
const RingGroupsPage = lazy(() => import("@/pages/ring-groups/ring-groups-page").then((m) => ({ default: m.RingGroupsPage })))
const QueuesPage = lazy(() => import("@/pages/queues/queues-page").then((m) => ({ default: m.QueuesPage })))
const IvrMenusPage = lazy(() => import("@/pages/ivr-menus/ivr-menus-page").then((m) => ({ default: m.IvrMenusPage })))
const ConferencesPage = lazy(() => import("@/pages/conferences/conferences-page").then((m) => ({ default: m.ConferencesPage })))
const PagingPage = lazy(() => import("@/pages/paging/paging-page").then((m) => ({ default: m.PagingPage })))
const SipTrunksPage = lazy(() => import("@/pages/sip-trunks/sip-trunks-page").then((m) => ({ default: m.SipTrunksPage })))
const DidsPage = lazy(() => import("@/pages/dids/dids-page").then((m) => ({ default: m.DidsPage })))
const InboundRoutesPage = lazy(() => import("@/pages/inbound-routes/inbound-routes-page").then((m) => ({ default: m.InboundRoutesPage })))
const OutboundRoutesPage = lazy(() => import("@/pages/outbound-routes/outbound-routes-page").then((m) => ({ default: m.OutboundRoutesPage })))
const AudioPromptsPage = lazy(() => import("@/pages/audio-prompts/audio-prompts-page").then((m) => ({ default: m.AudioPromptsPage })))
const TimeConditionsPage = lazy(() => import("@/pages/time-conditions/time-conditions-page").then((m) => ({ default: m.TimeConditionsPage })))
const HolidayCalendarsPage = lazy(() => import("@/pages/holiday-calendars/holiday-calendars-page").then((m) => ({ default: m.HolidayCalendarsPage })))
const CallerIdRulesPage = lazy(() => import("@/pages/caller-id-rules/caller-id-rules-page").then((m) => ({ default: m.CallerIdRulesPage })))
const DevicesPage = lazy(() => import("@/pages/devices/devices-page").then((m) => ({ default: m.DevicesPage })))
const SMSConversationsPage = lazy(() => import("@/pages/sms/conversations-page").then((m) => ({ default: m.SMSConversationsPage })))
const SMSProvidersPage = lazy(() => import("@/pages/sms/sms-providers-page").then((m) => ({ default: m.SMSProvidersPage })))
const ParkingPage = lazy(() => import("@/pages/parking/parking-page").then((m) => ({ default: m.ParkingPage })))
const DispositionCodesPage = lazy(() => import("@/pages/disposition-codes/disposition-codes-page").then((m) => ({ default: m.DispositionCodesPage })))
const AuditLogsPage = lazy(() => import("@/pages/audit-logs/audit-logs-page").then((m) => ({ default: m.AuditLogsPage })))
const ProfilePage = lazy(() => import("@/pages/profile/profile-page").then((m) => ({ default: m.ProfilePage })))
const ForgotPasswordPage = lazy(() => import("@/pages/login/forgot-password-page").then((m) => ({ default: m.ForgotPasswordPage })))
const ResetPasswordPage = lazy(() => import("@/pages/login/reset-password-page").then((m) => ({ default: m.ResetPasswordPage })))
const AnalyticsPage = lazy(() => import("@/pages/analytics/analytics-page").then((m) => ({ default: m.AnalyticsPage })))
const MSPOverviewPage = lazy(() => import("@/pages/msp/msp-overview-page").then((m) => ({ default: m.MSPOverviewPage })))
const DNCListsPage = lazy(() => import("@/pages/compliance/dnc-lists-page").then((m) => ({ default: m.DNCListsPage })))
const ConsentRecordsPage = lazy(() => import("@/pages/compliance/consent-records-page").then((m) => ({ default: m.ConsentRecordsPage })))
const ComplianceSettingsPage = lazy(() => import("@/pages/compliance/compliance-settings-page").then((m) => ({ default: m.ComplianceSettingsPage })))
const ComplianceAuditPage = lazy(() => import("@/pages/compliance/compliance-audit-page").then((m) => ({ default: m.ComplianceAuditPage })))
const ComplianceRulesPage = lazy(() => import("@/pages/compliance-monitoring/compliance-rules-page").then((m) => ({ default: m.ComplianceRulesPage })))
const ComplianceEvaluationsPage = lazy(() => import("@/pages/compliance-monitoring/compliance-evaluations-page").then((m) => ({ default: m.ComplianceEvaluationsPage })))
const ComplianceAnalyticsPage = lazy(() => import("@/pages/compliance-monitoring/compliance-analytics-page").then((m) => ({ default: m.ComplianceAnalyticsPage })))
const BossAdminPage = lazy(() => import("@/pages/boss-admin/boss-admin-page").then((m) => ({ default: m.BossAdminPage })))
const SitesPage = lazy(() => import("@/pages/sites/sites-page").then((m) => ({ default: m.SitesPage })))
const WfmShiftsPage = lazy(() => import("@/pages/workforce-management/wfm-shifts-page").then((m) => ({ default: m.WfmShiftsPage })))
const WfmSchedulePage = lazy(() => import("@/pages/workforce-management/wfm-schedule-page").then((m) => ({ default: m.WfmSchedulePage })))
const WfmTimeOffPage = lazy(() => import("@/pages/workforce-management/wfm-time-off-page").then((m) => ({ default: m.WfmTimeOffPage })))
const WfmAnalyticsPage = lazy(() => import("@/pages/workforce-management/wfm-analytics-page").then((m) => ({ default: m.WfmAnalyticsPage })))
const PortRequestsPage = lazy(() => import("@/pages/port-requests/port-requests-page").then((m) => ({ default: m.PortRequestsPage })))
const NotFoundPage = lazy(() => import("@/pages/not-found/not-found-page").then((m) => ({ default: m.NotFoundPage })))

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}>
      {children}
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LazyPage><LoginPage /></LazyPage>,
  },
  {
    path: "/forgot-password",
    element: <LazyPage><ForgotPasswordPage /></LazyPage>,
  },
  {
    path: "/reset-password",
    element: <LazyPage><ResetPasswordPage /></LazyPage>,
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <LazyPage><DashboardPage /></LazyPage> },
          { path: "extensions", element: <LazyPage><ExtensionsPage /></LazyPage> },
          { path: "extensions/:extensionId/follow-me", element: <LazyPage><FollowMePage /></LazyPage> },
          { path: "boss-admin", element: <LazyPage><BossAdminPage /></LazyPage> },
          { path: "ring-groups", element: <LazyPage><RingGroupsPage /></LazyPage> },
          { path: "queues", element: <LazyPage><QueuesPage /></LazyPage> },
          { path: "ivr-menus", element: <LazyPage><IvrMenusPage /></LazyPage> },
          { path: "conferences", element: <LazyPage><ConferencesPage /></LazyPage> },
          { path: "paging", element: <LazyPage><PagingPage /></LazyPage> },
          { path: "devices", element: <LazyPage><DevicesPage /></LazyPage> },
          { path: "sms/conversations", element: <LazyPage><SMSConversationsPage /></LazyPage> },
          { path: "sms/providers", element: <LazyPage><SMSProvidersPage /></LazyPage> },
          { path: "sip-trunks", element: <LazyPage><SipTrunksPage /></LazyPage> },
          { path: "dids", element: <LazyPage><DidsPage /></LazyPage> },
          { path: "inbound-routes", element: <LazyPage><InboundRoutesPage /></LazyPage> },
          { path: "outbound-routes", element: <LazyPage><OutboundRoutesPage /></LazyPage> },
          { path: "users", element: <LazyPage><UsersPage /></LazyPage> },
          { path: "cdrs", element: <LazyPage><CdrsPage /></LazyPage> },
          { path: "recordings", element: <LazyPage><RecordingsPage /></LazyPage> },
          { path: "voicemail", element: <LazyPage><VoicemailPage /></LazyPage> },
          { path: "audio-prompts", element: <LazyPage><AudioPromptsPage /></LazyPage> },
          { path: "time-conditions", element: <LazyPage><TimeConditionsPage /></LazyPage> },
          { path: "holiday-calendars", element: <LazyPage><HolidayCalendarsPage /></LazyPage> },
          { path: "caller-id-rules", element: <LazyPage><CallerIdRulesPage /></LazyPage> },
          { path: "parking", element: <LazyPage><ParkingPage /></LazyPage> },
          { path: "disposition-codes", element: <LazyPage><DispositionCodesPage /></LazyPage> },
          { path: "audit-logs", element: <LazyPage><AuditLogsPage /></LazyPage> },
          { path: "settings", element: <LazyPage><TenantSettingsPage /></LazyPage> },
          { path: "sites", element: <LazyPage><SitesPage /></LazyPage> },
          { path: "tenants", element: <LazyPage><TenantsPage /></LazyPage> },
          { path: "analytics", element: <LazyPage><AnalyticsPage /></LazyPage> },
          { path: "msp-overview", element: <LazyPage><MSPOverviewPage /></LazyPage> },
          { path: "compliance/dnc-lists", element: <LazyPage><DNCListsPage /></LazyPage> },
          { path: "compliance/consent-records", element: <LazyPage><ConsentRecordsPage /></LazyPage> },
          { path: "compliance/settings", element: <LazyPage><ComplianceSettingsPage /></LazyPage> },
          { path: "compliance/audit-log", element: <LazyPage><ComplianceAuditPage /></LazyPage> },
          { path: "compliance/monitoring-rules", element: <LazyPage><ComplianceRulesPage /></LazyPage> },
          { path: "compliance/monitoring-evaluations", element: <LazyPage><ComplianceEvaluationsPage /></LazyPage> },
          { path: "compliance/monitoring-analytics", element: <LazyPage><ComplianceAnalyticsPage /></LazyPage> },
          { path: "wfm/shifts", element: <LazyPage><WfmShiftsPage /></LazyPage> },
          { path: "wfm/schedule", element: <LazyPage><WfmSchedulePage /></LazyPage> },
          { path: "wfm/time-off", element: <LazyPage><WfmTimeOffPage /></LazyPage> },
          { path: "wfm/analytics", element: <LazyPage><WfmAnalyticsPage /></LazyPage> },
          { path: "port-requests", element: <LazyPage><PortRequestsPage /></LazyPage> },
          { path: "profile", element: <LazyPage><ProfilePage /></LazyPage> },
          { path: "*", element: <LazyPage><NotFoundPage /></LazyPage> },
        ],
      },
    ],
  },
])
