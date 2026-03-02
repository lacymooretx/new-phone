import { http, HttpResponse } from "msw"
import { setupServer } from "msw/node"

const tenantId = "00000000-0000-0000-0000-000000000001"

// Create a valid JWT-like token for testing
function makeToken(payload: Record<string, unknown>) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
  const body = btoa(JSON.stringify(payload))
  const sig = btoa("test-signature")
  return `${header}.${body}.${sig}`
}

export const testAccessToken = makeToken({
  sub: "user-001",
  tenant_id: tenantId,
  role: "msp_super_admin",
  type: "access",
  exp: Math.floor(Date.now() / 1000) + 3600,
  iat: Math.floor(Date.now() / 1000),
})

export const testRefreshToken = "refresh-token-test"

const handlers = [
  // Auth
  http.post("/api/v1/auth/login", async ({ request }) => {
    const body = (await request.json()) as Record<string, string>
    if (body.email === "admin@test.com" && body.password === "password123") {
      return HttpResponse.json({
        access_token: testAccessToken,
        refresh_token: testRefreshToken,
        token_type: "bearer",
      })
    }
    return HttpResponse.json({ detail: "Invalid credentials" }, { status: 401 })
  }),

  http.post("/api/v1/auth/refresh", () => {
    return HttpResponse.json({
      access_token: testAccessToken,
      refresh_token: testRefreshToken,
      token_type: "bearer",
    })
  }),

  // Health
  http.get("/api/v1/health", () => {
    return HttpResponse.json({
      status: "healthy",
      database: "connected",
      redis: "connected",
      freeswitch: "connected",
      minio: "connected",
    })
  }),

  // Tenants
  http.get("/api/v1/tenants", () => {
    return HttpResponse.json([
      {
        id: tenantId,
        name: "Test Tenant",
        slug: "test",
        domain: "test.com",
        sip_domain: "test.sip.local",
        default_moh_prompt_id: null,
        is_active: true,
        notes: null,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ])
  }),

  // Extensions
  http.get(`/api/v1/tenants/:tenantId/extensions`, () => {
    return HttpResponse.json([
      {
        id: "ext-001",
        tenant_id: tenantId,
        extension_number: "1001",
        sip_username: "1001@test.sip.local",
        user_id: null,
        voicemail_box_id: null,
        internal_cid_name: "John Doe",
        internal_cid_number: "1001",
        external_cid_name: null,
        external_cid_number: null,
        emergency_cid_number: null,
        e911_street: null,
        e911_city: null,
        e911_state: null,
        e911_zip: null,
        e911_country: null,
        call_forward_unconditional: null,
        call_forward_busy: null,
        call_forward_no_answer: null,
        call_forward_not_registered: null,
        call_forward_ring_time: 25,
        dnd_enabled: false,
        call_waiting: true,
        max_registrations: 3,
        outbound_cid_mode: "internal",
        class_of_service: "domestic",
        recording_policy: "never",
        notes: null,
        agent_status: null,
        pickup_group: null,
        is_active: true,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ])
  }),

  // CDRs
  http.get(`/api/v1/tenants/:tenantId/cdrs`, () => {
    return HttpResponse.json([
      {
        id: "cdr-001",
        tenant_id: tenantId,
        call_id: "call-001",
        direction: "inbound",
        caller_number: "+15551234567",
        caller_name: "Test Caller",
        called_number: "1001",
        extension_id: null,
        did_id: null,
        trunk_id: null,
        ring_group_id: null,
        disposition: "answered",
        hangup_cause: null,
        duration_seconds: 120,
        billable_seconds: 115,
        ring_seconds: 5,
        start_time: "2025-01-15T10:00:00Z",
        answer_time: "2025-01-15T10:00:05Z",
        end_time: "2025-01-15T10:02:00Z",
        has_recording: true,
        created_at: "2025-01-15T10:02:00Z",
      },
    ])
  }),
]

export const server = setupServer(...handlers)
