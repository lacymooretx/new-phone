# Number Porting

## What is Number Porting?

Number porting (Local Number Portability / LNP) is the process of transferring existing phone numbers from one carrier to another. When a customer switches to the New Phone platform, their existing numbers must be ported from their current carrier through either ClearlyIP or Twilio.

Porting is regulated by the FCC. The losing carrier is required to release numbers within defined timelines, but the process involves coordination between multiple parties (customer, gaining carrier, losing carrier, number portability clearinghouse).

## Port Request Lifecycle

```
submitted
    |
pending_loa  (waiting for customer to provide LOA)
    |
loa_submitted  (LOA uploaded, sent to provider)
    |
foc_received  (provider confirms FOC date)
    |
in_progress  (porting underway on FOC date)
    |
completed  (numbers active on platform)
```

Alternative terminal states:
- `rejected` -- Provider or losing carrier rejected the port
- `cancelled` -- Port cancelled by customer or admin

### Status Flow Diagram

```
submitted ──> pending_loa ──> loa_submitted ──> foc_received ──> in_progress ──> completed
    |              |               |                |                |
    └──> cancelled └──> cancelled  └──> rejected    └──> rejected   └──> rejected
                                   └──> cancelled   └──> cancelled
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tenants/{tid}/port-requests` | List all port requests |
| POST | `/api/v1/tenants/{tid}/port-requests` | Submit a new port request |
| GET | `/api/v1/tenants/{tid}/port-requests/{id}` | Get port request details |
| PATCH | `/api/v1/tenants/{tid}/port-requests/{id}` | Update status, notes, FOC date |
| POST | `/api/v1/tenants/{tid}/port-requests/{id}/upload-loa` | Upload LOA document |
| POST | `/api/v1/tenants/{tid}/port-requests/{id}/check-status` | Poll provider for status |
| POST | `/api/v1/tenants/{tid}/port-requests/{id}/cancel` | Cancel the port request |
| POST | `/api/v1/tenants/{tid}/port-requests/{id}/complete` | Mark port as completed, activate DIDs |

## Submitting a Port Request

### Create Request

```json
POST /api/v1/tenants/{tid}/port-requests
{
  "numbers": ["+15125551234", "+15125555678"],
  "current_carrier": "AT&T",
  "provider": "clearlyip",
  "requested_port_date": "2026-04-15",
  "notes": "Customer switching from AT&T business lines"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `numbers` | list[str] | Yes | Phone numbers to port (E.164 format) |
| `current_carrier` | str | Yes | Name of the losing carrier |
| `provider` | str | Yes | `clearlyip` or `twilio` |
| `requested_port_date` | date | No | Preferred port completion date |
| `notes` | str | No | Internal notes |

## LOA (Letter of Authorization)

The LOA is a signed document from the customer authorizing the number transfer. It is required by the losing carrier before releasing numbers.

### LOA Requirements

- Must be signed by the authorized account holder at the losing carrier
- Must include:
  - Customer name and address (must match losing carrier's records exactly)
  - Phone numbers being ported
  - Current carrier name
  - Account number at losing carrier
  - Authorization signature and date
- Accepted formats: PDF, PNG, JPEG, TIFF
- Maximum file size: 10 MB

### Upload LOA

```
POST /api/v1/tenants/{tid}/port-requests/{id}/upload-loa
Content-Type: multipart/form-data

file: (LOA document)
```

The LOA is stored in MinIO under `port-requests/{tenant_id}/{port_request_id}/loa.{ext}`.

After uploading, update the port request status to `loa_submitted`:

```json
PATCH /api/v1/tenants/{tid}/port-requests/{id}
{
  "status": "loa_submitted"
}
```

## FOC (Firm Order Commitment) Date

The FOC date is when the gaining carrier confirms the port will be completed. Once the losing carrier accepts the port request, they issue an FOC date.

After receiving an FOC:

```json
PATCH /api/v1/tenants/{tid}/port-requests/{id}
{
  "status": "foc_received",
  "foc_date": "2026-04-15"
}
```

The FOC date is the date when numbers will cut over. On that date, the port status moves to `in_progress`.

### Important FOC Notes

- FOC dates are typically 1-5 business days for simple ports, 2-4 weeks for complex ports
- Simple port: 1-5 numbers, single line type, no special features
- Complex port: 6+ numbers, mixed line types, toll-free, or numbers with special features (like hunt groups)
- FOC dates can be rescheduled by the losing carrier (usually with advance notice)

## Completing a Port

Once numbers are live on the platform:

```
POST /api/v1/tenants/{tid}/port-requests/{id}/complete
```

This:
1. Sets status to `completed`
2. Records the actual port date
3. Activates the ported DIDs in the platform (creates DID records if needed)
4. Numbers become available for inbound/outbound routing

## Checking Status

Poll the provider for the current port status:

```
POST /api/v1/tenants/{tid}/port-requests/{id}/check-status
```

This contacts the provider API and syncs the local status with the provider's records. Useful for detecting FOC dates or rejections that haven't been manually updated.

## Cancellation

Cancel a port request at any time before completion:

```
POST /api/v1/tenants/{tid}/port-requests/{id}/cancel?reason=Customer changed mind
```

### Cancellation Rules

- Ports can be cancelled in any status except `completed`
- Cancelling after `foc_received` may incur fees depending on the carrier
- Once a port is `in_progress` (FOC date reached), cancellation is not guaranteed -- the losing carrier may have already released the numbers
- The `reason` field is optional but recommended for audit purposes

## Port Request History

Every status change is tracked in the `port_request_history` table. The full history is returned with each port request response, showing:

- Previous status
- New status
- Who made the change
- Notes
- Timestamp

## RBAC Permissions

| Permission | Roles |
|-----------|-------|
| `manage_dids` | MSP Super Admin, MSP Tech, Tenant Admin |
| `view_dids` | All roles |

Port requests use the DID permission set since they are part of the number management workflow.

## Provider Support

| Feature | ClearlyIP | Twilio |
|---------|-----------|--------|
| Port submission | API-based | API-based |
| Status polling | Supported | Supported |
| LOA upload | Via platform (MinIO) | Via platform (MinIO) |
| Simple ports | Yes | Yes |
| Complex ports | Yes | Yes |
| Wireless ports | Contact provider | Contact provider |

## Key Source Files

| File | Purpose |
|------|---------|
| `api/src/new_phone/routers/port_requests.py` | Port request API endpoints |
| `api/src/new_phone/services/port_service.py` | Port request business logic |
| `api/src/new_phone/schemas/port_requests.py` | Request/response schemas |
| `api/src/new_phone/models/port_request.py` | Database models (PortRequest, PortRequestHistory) |
