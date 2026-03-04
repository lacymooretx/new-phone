import {
  LayoutDashboard,
  Phone,
  Users,
  PhoneCall,
  Disc3,
  Voicemail,
  Settings,
  Building2,
  PhoneForwarded,
  Headset,
  ListTree,
  Radio,
  Megaphone,
  Cable,
  Hash,
  ArrowDownToLine,
  ArrowUpFromLine,
  ArrowRightLeft,
  Music,
  Clock,
  CalendarDays,
  ShieldCheck,
  ClipboardList,
  Monitor,
  MessageSquare,
  Tag,
  BarChart3,
  Globe,
  ParkingSquare,
  ShieldBan,
  FileCheck,
  ScrollText,
  UserCog,
  ScanSearch,
  ClipboardCheck,
  BarChart4,
  TrendingUp,
  CalendarOff,
  Server,
  PhoneCallback,
  Star,
  DollarSign,
  Shield,
  FolderInput,
  MonitorDot,
  BedDouble,
  Puzzle,
  Code2,
} from "lucide-react"
import { ROUTES, PERMISSIONS, type Permission } from "./constants"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  labelKey: string
  path: string
  icon: LucideIcon
  permission: Permission | null
}

export interface NavGroup {
  labelKey: string
  items: NavItem[]
  /** If true, group is only shown to MSP roles */
  mspOnly?: boolean
}

export const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: "",
    items: [
      { labelKey: "nav.dashboard", path: ROUTES.DASHBOARD, icon: LayoutDashboard, permission: null },
    ],
  },
  {
    labelKey: "nav.telephony",
    items: [
      { labelKey: "nav.extensions", path: ROUTES.EXTENSIONS, icon: Phone, permission: PERMISSIONS.VIEW_EXTENSIONS },
      { labelKey: "nav.bossAdmin", path: ROUTES.BOSS_ADMIN, icon: UserCog, permission: PERMISSIONS.VIEW_EXTENSIONS },
      { labelKey: "nav.ringGroups", path: ROUTES.RING_GROUPS, icon: PhoneForwarded, permission: PERMISSIONS.VIEW_RING_GROUPS },
      { labelKey: "nav.queues", path: ROUTES.QUEUES, icon: Headset, permission: PERMISSIONS.VIEW_QUEUES },
      { labelKey: "nav.dispositionCodes", path: ROUTES.DISPOSITION_CODES, icon: Tag, permission: PERMISSIONS.VIEW_QUEUES },
      { labelKey: "nav.parking", path: ROUTES.PARKING, icon: ParkingSquare, permission: PERMISSIONS.VIEW_QUEUES },
      { labelKey: "nav.callbacks", path: ROUTES.CALLBACKS, icon: PhoneCallback, permission: PERMISSIONS.VIEW_QUEUES },
      { labelKey: "nav.surveys", path: ROUTES.SURVEYS, icon: Star, permission: PERMISSIONS.VIEW_QUEUES },
      { labelKey: "nav.ivrMenus", path: ROUTES.IVR_MENUS, icon: ListTree, permission: PERMISSIONS.VIEW_IVR },
      { labelKey: "nav.conferences", path: ROUTES.CONFERENCES, icon: Radio, permission: PERMISSIONS.VIEW_CONFERENCES },
      { labelKey: "nav.paging", path: ROUTES.PAGING, icon: Megaphone, permission: PERMISSIONS.VIEW_PAGING },
      { labelKey: "nav.devices", path: ROUTES.DEVICES, icon: Monitor, permission: PERMISSIONS.VIEW_DEVICES },
    ],
  },
  {
    labelKey: "nav.sms",
    items: [
      { labelKey: "nav.conversations", path: ROUTES.SMS_CONVERSATIONS, icon: MessageSquare, permission: PERMISSIONS.VIEW_SMS },
      { labelKey: "nav.smsProviders", path: ROUTES.SMS_PROVIDERS, icon: Cable, permission: PERMISSIONS.MANAGE_SMS },
    ],
  },
  {
    labelKey: "nav.connectivity",
    items: [
      { labelKey: "nav.sipTrunks", path: ROUTES.SIP_TRUNKS, icon: Cable, permission: PERMISSIONS.VIEW_TRUNKS },
      { labelKey: "nav.dids", path: ROUTES.DIDS, icon: Hash, permission: PERMISSIONS.VIEW_DIDS },
      { labelKey: "nav.inboundRoutes", path: ROUTES.INBOUND_ROUTES, icon: ArrowDownToLine, permission: PERMISSIONS.VIEW_INBOUND_ROUTES },
      { labelKey: "nav.outboundRoutes", path: ROUTES.OUTBOUND_ROUTES, icon: ArrowUpFromLine, permission: PERMISSIONS.VIEW_OUTBOUND_ROUTES },
      { labelKey: "nav.portRequests", path: ROUTES.PORT_REQUESTS, icon: ArrowRightLeft, permission: PERMISSIONS.VIEW_DIDS },
    ],
  },
  {
    labelKey: "nav.reports",
    items: [
      { labelKey: "nav.callHistory", path: ROUTES.CDRS, icon: PhoneCall, permission: PERMISSIONS.VIEW_CDRS },
      { labelKey: "nav.callAnalytics", path: ROUTES.ANALYTICS, icon: BarChart3, permission: PERMISSIONS.VIEW_CDRS },
      { labelKey: "nav.recordings", path: ROUTES.RECORDINGS, icon: Disc3, permission: PERMISSIONS.VIEW_RECORDINGS },
      { labelKey: "nav.voicemail", path: ROUTES.VOICEMAIL, icon: Voicemail, permission: PERMISSIONS.VIEW_VOICEMAIL },
    ],
  },
  {
    labelKey: "nav.compliance",
    items: [
      { labelKey: "nav.dncLists", path: ROUTES.COMPLIANCE_DNC, icon: ShieldBan, permission: PERMISSIONS.VIEW_COMPLIANCE },
      { labelKey: "nav.consentRecords", path: ROUTES.COMPLIANCE_CONSENT, icon: FileCheck, permission: PERMISSIONS.VIEW_COMPLIANCE },
      { labelKey: "nav.complianceSettings", path: ROUTES.COMPLIANCE_SETTINGS, icon: Settings, permission: PERMISSIONS.MANAGE_COMPLIANCE },
      { labelKey: "nav.complianceAudit", path: ROUTES.COMPLIANCE_AUDIT, icon: ScrollText, permission: PERMISSIONS.VIEW_COMPLIANCE },
      { labelKey: "nav.complianceRules", path: ROUTES.COMPLIANCE_MONITORING_RULES, icon: ClipboardCheck, permission: PERMISSIONS.VIEW_COMPLIANCE },
      { labelKey: "nav.complianceEvaluations", path: ROUTES.COMPLIANCE_MONITORING_EVALUATIONS, icon: ScanSearch, permission: PERMISSIONS.VIEW_COMPLIANCE },
      { labelKey: "nav.complianceAnalytics", path: ROUTES.COMPLIANCE_MONITORING_ANALYTICS, icon: BarChart4, permission: PERMISSIONS.VIEW_COMPLIANCE },
    ],
  },
  {
    labelKey: "nav.workforce",
    items: [
      { labelKey: "nav.wfmShifts", path: ROUTES.WFM_SHIFTS, icon: Clock, permission: PERMISSIONS.VIEW_WFM },
      { labelKey: "nav.wfmSchedule", path: ROUTES.WFM_SCHEDULE, icon: CalendarDays, permission: PERMISSIONS.VIEW_WFM },
      { labelKey: "nav.wfmTimeOff", path: ROUTES.WFM_TIME_OFF, icon: CalendarOff, permission: PERMISSIONS.VIEW_WFM },
      { labelKey: "nav.wfmAnalytics", path: ROUTES.WFM_ANALYTICS, icon: TrendingUp, permission: PERMISSIONS.VIEW_WFM },
    ],
  },
  {
    labelKey: "nav.securityCompliance",
    items: [
      { labelKey: "nav.stirShaken", path: ROUTES.STIR_SHAKEN, icon: Shield, permission: PERMISSIONS.MANAGE_TENANT },
    ],
  },
  {
    labelKey: "nav.billingBusiness",
    items: [
      { labelKey: "nav.billing", path: ROUTES.BILLING, icon: DollarSign, permission: PERMISSIONS.MANAGE_TENANT },
    ],
  },
  {
    labelKey: "nav.advancedFeatures",
    items: [
      { labelKey: "nav.receptionist", path: ROUTES.RECEPTIONIST, icon: MonitorDot, permission: PERMISSIONS.VIEW_EXTENSIONS },
      { labelKey: "nav.hospitality", path: ROUTES.HOSPITALITY, icon: BedDouble, permission: PERMISSIONS.MANAGE_EXTENSIONS },
      { labelKey: "nav.migration", path: ROUTES.MIGRATION, icon: FolderInput, permission: PERMISSIONS.MANAGE_TENANT },
      { labelKey: "nav.developer", path: ROUTES.DEVELOPER, icon: Code2, permission: PERMISSIONS.MANAGE_TENANT },
      { labelKey: "nav.marketplace", path: ROUTES.MARKETPLACE, icon: Puzzle, permission: PERMISSIONS.MANAGE_TENANT },
    ],
  },
  {
    labelKey: "nav.system",
    items: [
      { labelKey: "nav.sites", path: ROUTES.SITES, icon: Building2, permission: PERMISSIONS.VIEW_TENANT },
      { labelKey: "nav.users", path: ROUTES.USERS, icon: Users, permission: PERMISSIONS.VIEW_USERS },
      { labelKey: "nav.audioPrompts", path: ROUTES.AUDIO_PROMPTS, icon: Music, permission: PERMISSIONS.MANAGE_EXTENSIONS },
      { labelKey: "nav.timeConditions", path: ROUTES.TIME_CONDITIONS, icon: Clock, permission: PERMISSIONS.MANAGE_EXTENSIONS },
      { labelKey: "nav.holidayCalendars", path: ROUTES.HOLIDAY_CALENDARS, icon: CalendarDays, permission: PERMISSIONS.MANAGE_EXTENSIONS },
      { labelKey: "nav.callerIdRules", path: ROUTES.CALLER_ID_RULES, icon: ShieldCheck, permission: PERMISSIONS.MANAGE_EXTENSIONS },
      { labelKey: "nav.auditLogs", path: ROUTES.AUDIT_LOGS, icon: ClipboardList, permission: PERMISSIONS.VIEW_AUDIT_LOGS },
      { labelKey: "nav.settings", path: ROUTES.TENANT_SETTINGS, icon: Settings, permission: PERMISSIONS.VIEW_TENANT },
    ],
  },
  {
    labelKey: "nav.msp",
    mspOnly: true,
    items: [
      { labelKey: "nav.tenants", path: ROUTES.TENANTS, icon: Building2, permission: null },
      { labelKey: "nav.mspOverview", path: ROUTES.MSP_OVERVIEW, icon: Globe, permission: null },
      { labelKey: "nav.telephonyProviders", path: ROUTES.MSP_TELEPHONY_PROVIDERS, icon: Server, permission: null },
    ],
  },
]

/** Flat list of all nav items for search/command palette */
export function getAllNavItems(): (NavItem & { group: string })[] {
  return NAV_GROUPS.flatMap((group) =>
    group.items.map((item) => ({ ...item, group: group.labelKey }))
  )
}
