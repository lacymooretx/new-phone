import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { usePhoneAppConfig, useUpdatePhoneAppConfig } from "@/api/phone-app-config"
import { useAuthStore } from "@/stores/auth-store"
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
  FormDescription,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { Phone, Globe, Palette, Network, Zap, Music, Shield, HardDrive } from "lucide-react"

const schema = z.object({
  // General
  timezone: z.string().min(1),
  language: z.string().min(1),
  date_format: z.string(),
  time_format: z.string(),

  // Branding
  logo_url: z.string().nullable().optional(),
  ringtone: z.string().min(1),
  backlight_time: z.coerce.number().int().min(0).max(1800),
  screensaver_type: z.string(),

  // Network
  vlan_enabled: z.boolean(),
  vlan_id: z.coerce.number().int().min(1).max(4094).nullable().optional(),
  vlan_priority: z.coerce.number().int().min(0).max(7),
  dscp_sip: z.coerce.number().int().min(0).max(63),
  dscp_rtp: z.coerce.number().int().min(0).max(63),

  // Feature codes
  pickup_code: z.string().min(1),
  intercom_code: z.string().min(1),
  parking_code: z.string().min(1),
  dnd_on_code: z.string().nullable().optional(),
  dnd_off_code: z.string().nullable().optional(),
  fwd_unconditional_code: z.string().nullable().optional(),
  fwd_busy_code: z.string().nullable().optional(),
  fwd_noanswer_code: z.string().nullable().optional(),

  // Audio
  codec_priority: z.string().min(1),

  // Security
  phone_admin_password: z.string().nullable().optional(),

  // Firmware
  firmware_url: z.string().nullable().optional(),

  // Phone apps
  directory_enabled: z.boolean(),
  voicemail_enabled: z.boolean(),
  call_history_enabled: z.boolean(),
  parking_enabled: z.boolean(),
  queue_dashboard_enabled: z.boolean(),
  settings_enabled: z.boolean(),
  action_urls_enabled: z.boolean(),
  page_size: z.coerce.number().int().min(5).max(50),
  company_name: z.string().nullable().optional(),
})

type FormValues = z.infer<typeof schema>

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Anchorage",
  "Pacific/Honolulu",
  "America/Phoenix",
  "America/Indiana/Indianapolis",
  "America/Toronto",
  "America/Vancouver",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
  "UTC",
]

const LANGUAGES = [
  "English",
  "Spanish",
  "French",
  "German",
  "Italian",
  "Portuguese",
  "Chinese",
  "Japanese",
  "Korean",
]

function SectionHeader({ icon: Icon, title, description }: { icon: React.ComponentType<{ className?: string }>; title: string; description?: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="h-5 w-5 text-muted-foreground" />
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
    </div>
  )
}

export function PhoneProvisioningCard() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const { data: config, isLoading } = usePhoneAppConfig(tenantId)
  const updateMutation = useUpdatePhoneAppConfig()
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      timezone: "America/Chicago",
      language: "English",
      date_format: "2",
      time_format: "1",
      logo_url: "",
      ringtone: "Ring1.wav",
      backlight_time: 60,
      screensaver_type: "2",
      vlan_enabled: false,
      vlan_id: null,
      vlan_priority: 5,
      dscp_sip: 46,
      dscp_rtp: 46,
      pickup_code: "*8",
      intercom_code: "*80",
      parking_code: "*85",
      dnd_on_code: "",
      dnd_off_code: "",
      fwd_unconditional_code: "",
      fwd_busy_code: "",
      fwd_noanswer_code: "",
      codec_priority: "PCMU,PCMA,G722,G729,opus",
      phone_admin_password: "",
      firmware_url: "",
      directory_enabled: true,
      voicemail_enabled: true,
      call_history_enabled: true,
      parking_enabled: true,
      queue_dashboard_enabled: true,
      settings_enabled: true,
      action_urls_enabled: true,
      page_size: 15,
      company_name: "",
    },
  })

  useEffect(() => {
    if (config) {
      form.reset({
        timezone: config.timezone,
        language: config.language,
        date_format: config.date_format,
        time_format: config.time_format,
        logo_url: config.logo_url ?? "",
        ringtone: config.ringtone,
        backlight_time: config.backlight_time,
        screensaver_type: config.screensaver_type,
        vlan_enabled: config.vlan_enabled,
        vlan_id: config.vlan_id,
        vlan_priority: config.vlan_priority,
        dscp_sip: config.dscp_sip,
        dscp_rtp: config.dscp_rtp,
        pickup_code: config.pickup_code,
        intercom_code: config.intercom_code,
        parking_code: config.parking_code,
        dnd_on_code: config.dnd_on_code ?? "",
        dnd_off_code: config.dnd_off_code ?? "",
        fwd_unconditional_code: config.fwd_unconditional_code ?? "",
        fwd_busy_code: config.fwd_busy_code ?? "",
        fwd_noanswer_code: config.fwd_noanswer_code ?? "",
        codec_priority: config.codec_priority,
        phone_admin_password: "",
        firmware_url: config.firmware_url ?? "",
        directory_enabled: config.directory_enabled,
        voicemail_enabled: config.voicemail_enabled,
        call_history_enabled: config.call_history_enabled,
        parking_enabled: config.parking_enabled,
        queue_dashboard_enabled: config.queue_dashboard_enabled,
        settings_enabled: config.settings_enabled,
        action_urls_enabled: config.action_urls_enabled,
        page_size: config.page_size,
        company_name: config.company_name ?? "",
      })
    }
  }, [config, form])

  const vlanEnabled = form.watch("vlan_enabled")

  const onSubmit = (data: FormValues) => {
    // Only send phone_admin_password if user typed something
    const payload: Record<string, unknown> = { ...data }
    if (!data.phone_admin_password) {
      delete payload.phone_admin_password
    }
    // Convert empty strings to null for nullable fields
    for (const key of ["logo_url", "firmware_url", "dnd_on_code", "dnd_off_code", "fwd_unconditional_code", "fwd_busy_code", "fwd_noanswer_code", "company_name"]) {
      if (payload[key] === "") payload[key] = null
    }
    if (!vlanEnabled) payload.vlan_id = null

    updateMutation.mutate(
      { tenantId, data: payload as any },
      {
        onSuccess: () => toast.success("Phone provisioning settings saved"),
        onError: (err) => toast.error(err.message),
      }
    )
  }

  if (isLoading) return <Skeleton className="h-96" />

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="h-5 w-5" />
          Phone Provisioning
        </CardTitle>
        <CardDescription>
          Configure Yealink desk phone settings applied during auto-provisioning. Changes take effect on next phone reboot.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            {/* General */}
            <div>
              <SectionHeader icon={Globe} title="General" description="Timezone, language, and date/time display" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                <FormField control={form.control} name="timezone" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timezone</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {TIMEZONES.map((tz) => <SelectItem key={tz} value={tz}>{tz}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="language" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Language</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {LANGUAGES.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="date_format" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Date Format</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="0">YYYY/MM/DD</SelectItem>
                          <SelectItem value="1">DD/MM/YYYY</SelectItem>
                          <SelectItem value="2">MM/DD/YYYY</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="time_format" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Time Format</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">12-hour</SelectItem>
                          <SelectItem value="0">24-hour</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Branding */}
            <div>
              <SectionHeader icon={Palette} title="Branding" description="Logo, ringtone, display settings" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                <FormField control={form.control} name="logo_url" render={({ field }) => (
                  <FormItem className="md:col-span-2">
                    <FormLabel>Logo / Wallpaper URL</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="https://example.com/logo.png" /></FormControl>
                    <FormDescription>URL to wallpaper image pushed to phones</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="ringtone" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ringtone</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {["Ring1.wav", "Ring2.wav", "Ring3.wav", "Ring4.wav", "Ring5.wav", "Ring6.wav", "Ring7.wav", "Ring8.wav", "Silent.wav"].map((r) => (
                            <SelectItem key={r} value={r}>{r.replace(".wav", "")}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="backlight_time" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Backlight Timeout (sec)</FormLabel>
                    <FormControl><Input type="number" {...field} /></FormControl>
                    <FormDescription>0 = always on</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="screensaver_type" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Screensaver</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="0">Off</SelectItem>
                          <SelectItem value="1">System</SelectItem>
                          <SelectItem value="2">Clock</SelectItem>
                          <SelectItem value="3">Color Photo</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Network / QoS */}
            <div>
              <SectionHeader icon={Network} title="Network" description="VLAN and QoS (DSCP) settings" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                <FormField control={form.control} name="vlan_enabled" render={({ field }) => (
                  <FormItem className="flex items-center gap-3 md:col-span-2">
                    <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
                    <FormLabel className="!mt-0">Enable Voice VLAN</FormLabel>
                  </FormItem>
                )} />
                {vlanEnabled && (
                  <>
                    <FormField control={form.control} name="vlan_id" render={({ field }) => (
                      <FormItem>
                        <FormLabel>VLAN ID</FormLabel>
                        <FormControl><Input type="number" {...field} value={field.value ?? ""} placeholder="100" /></FormControl>
                        <FormDescription>1-4094</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )} />
                    <FormField control={form.control} name="vlan_priority" render={({ field }) => (
                      <FormItem>
                        <FormLabel>VLAN Priority (802.1p)</FormLabel>
                        <FormControl><Input type="number" {...field} /></FormControl>
                        <FormDescription>0-7</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )} />
                  </>
                )}
                <FormField control={form.control} name="dscp_sip" render={({ field }) => (
                  <FormItem>
                    <FormLabel>DSCP SIP Signaling</FormLabel>
                    <FormControl><Input type="number" {...field} /></FormControl>
                    <FormDescription>0-63 (46 = EF)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="dscp_rtp" render={({ field }) => (
                  <FormItem>
                    <FormLabel>DSCP RTP Audio</FormLabel>
                    <FormControl><Input type="number" {...field} /></FormControl>
                    <FormDescription>0-63 (46 = EF)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Feature Codes */}
            <div>
              <SectionHeader icon={Zap} title="Feature Codes" description="Pickup, intercom, parking, DND, and call forwarding codes" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl">
                <FormField control={form.control} name="pickup_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pickup Code</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="intercom_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Intercom Code</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="parking_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Parking Code</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="dnd_on_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>DND On</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="e.g. *78" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="dnd_off_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>DND Off</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="e.g. *79" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="fwd_unconditional_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fwd Always</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="e.g. *72" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="fwd_busy_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fwd Busy</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="e.g. *90" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="fwd_noanswer_code" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fwd No Answer</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="e.g. *92" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Audio / Codecs */}
            <div>
              <SectionHeader icon={Music} title="Audio" description="Codec priority for voice calls" />
              <div className="max-w-2xl">
                <FormField control={form.control} name="codec_priority" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Codec Priority</FormLabel>
                    <FormControl><Input {...field} placeholder="PCMU,PCMA,G722,G729,opus" /></FormControl>
                    <FormDescription>Comma-separated, highest priority first. Supported: PCMU, PCMA, G722, G729, opus, G726-32, iLBC</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Security */}
            <div>
              <SectionHeader icon={Shield} title="Security" description="Phone admin web UI password" />
              <div className="max-w-2xl space-y-2">
                <FormField control={form.control} name="phone_admin_password" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Admin Password</FormLabel>
                    <FormControl>
                      <Input
                        type={showPassword ? "text" : "password"}
                        {...field}
                        value={field.value ?? ""}
                        placeholder={config?.has_phone_admin_password ? "(password set — leave blank to keep)" : "Set admin password"}
                      />
                    </FormControl>
                    <FormDescription>
                      <button type="button" className="text-xs underline" onClick={() => setShowPassword(!showPassword)}>
                        {showPassword ? "Hide" : "Show"}
                      </button>
                      {" "}— Leave blank to keep current. Replaces default "admin" password.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Firmware */}
            <div>
              <SectionHeader icon={HardDrive} title="Firmware" description="Auto-update firmware URL" />
              <div className="max-w-2xl">
                <FormField control={form.control} name="firmware_url" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Firmware Server URL</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="https://example.com/firmware/" /></FormControl>
                    <FormDescription>Phones check this URL for firmware updates on boot</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <Separator />

            {/* Phone Apps */}
            <div>
              <SectionHeader icon={Phone} title="Phone Apps" description="XML app toggles, page size, company name" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                {(["directory_enabled", "voicemail_enabled", "call_history_enabled", "parking_enabled", "queue_dashboard_enabled", "settings_enabled", "action_urls_enabled"] as const).map((name) => (
                  <FormField key={name} control={form.control} name={name} render={({ field }) => (
                    <FormItem className="flex items-center gap-3">
                      <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
                      <FormLabel className="!mt-0">{name.replace(/_enabled$/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</FormLabel>
                    </FormItem>
                  )} />
                ))}
                <FormField control={form.control} name="page_size" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Page Size</FormLabel>
                    <FormControl><Input type="number" {...field} /></FormControl>
                    <FormDescription>Items per page in phone app lists</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="company_name" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Company Name</FormLabel>
                    <FormControl><Input {...field} value={field.value ?? ""} placeholder="Used in phone display" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <div className="pt-4">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Phone Settings"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
