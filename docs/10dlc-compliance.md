# 10DLC Compliance

## What is 10DLC?

10DLC (10-Digit Long Code) is a US carrier-mandated registration system for businesses that send Application-to-Person (A2P) SMS messages using standard 10-digit phone numbers. Without 10DLC registration, SMS messages sent from local numbers face heavy filtering, throttling, or outright blocking by carriers (T-Mobile, AT&T, Verizon).

Registration happens at two levels:

1. **Brand** -- Your business identity (EIN, legal name, vertical).
2. **Campaign** -- The specific messaging use case (marketing, customer care, notifications, etc.).

Each tenant must register a brand, then create one or more campaigns under that brand.

## Brand Registration

### Workflow

```
Create Brand (draft)
    |
Review & Submit  -->  Provider submits to TCR
    |
Pending  -->  TCR vetting (1-7 business days)
    |
Approved / Rejected
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tenants/{tid}/10dlc/brands` | Create brand (draft) |
| GET | `/api/v1/tenants/{tid}/10dlc/brands` | List brands |
| GET | `/api/v1/tenants/{tid}/10dlc/brands/{id}` | Get brand details |
| PATCH | `/api/v1/tenants/{tid}/10dlc/brands/{id}` | Update brand (draft only) |
| POST | `/api/v1/tenants/{tid}/10dlc/brands/{id}/register` | Submit to provider for TCR vetting |
| GET | `/api/v1/tenants/{tid}/10dlc/brands/{id}/status` | Poll provider for current status |

### Create Brand Request

```json
POST /api/v1/tenants/{tid}/10dlc/brands
{
  "name": "Acme Corporation",
  "ein": "12-3456789",
  "ein_issuing_country": "US",
  "brand_type": "small_business",
  "vertical": "technology",
  "website": "https://acme.example.com"
}
```

**Brand types**: `sole_proprietor`, `small_business`, `large_business`

**Required fields**: `name`, `ein`, `brand_type`, `vertical`

### Brand Statuses

| Status | Meaning |
|--------|---------|
| `draft` | Created locally, not yet submitted |
| `pending` | Submitted to provider, awaiting TCR vetting |
| `approved` | Vetting passed, can create campaigns |
| `rejected` | Vetting failed, see `rejection_reason` |

## Campaign Registration

### Workflow

```
Create Campaign (draft)
    |
Review & Submit  -->  Provider submits to carriers
    |
Pending  -->  Carrier review (1-14 business days)
    |
Approved / Rejected / Suspended
```

A campaign can only be created under an **approved** brand.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tenants/{tid}/10dlc/campaigns` | Create campaign (draft) |
| GET | `/api/v1/tenants/{tid}/10dlc/campaigns` | List campaigns |
| GET | `/api/v1/tenants/{tid}/10dlc/campaigns/{id}` | Get campaign details |
| PATCH | `/api/v1/tenants/{tid}/10dlc/campaigns/{id}` | Update campaign (draft only) |
| POST | `/api/v1/tenants/{tid}/10dlc/campaigns/{id}/register` | Submit to provider |
| GET | `/api/v1/tenants/{tid}/10dlc/campaigns/{id}/status` | Poll provider for current status |

### Create Campaign Request

```json
POST /api/v1/tenants/{tid}/10dlc/campaigns
{
  "brand_id": "uuid-of-approved-brand",
  "name": "Acme Customer Notifications",
  "use_case": "customer_care",
  "description": "Transactional notifications for support tickets and order updates",
  "sample_messages": [
    "Your support ticket #1234 has been updated. Reply HELP for help.",
    "Your order has shipped! Tracking: XYZ123. Reply STOP to opt out."
  ],
  "message_flow": "Customer initiates contact via support form. Automated notifications sent for ticket updates.",
  "help_message": "Reply HELP for support info. Contact support@acme.com for assistance.",
  "opt_out_message": "You have been unsubscribed. No more messages will be sent. Reply START to re-subscribe.",
  "opt_in_keywords": "START",
  "opt_out_keywords": "STOP",
  "help_keywords": "HELP",
  "number_pool": ["+15125551234", "+15125555678"]
}
```

**Use cases**: `marketing`, `customer_care`, `account_notifications`, `delivery_notifications`, `mixed`, `two_factor_auth`, `polling_voting`, `public_service`, `emergency`, `charity`

### Campaign Statuses

| Status | Meaning |
|--------|---------|
| `draft` | Created locally, not yet submitted |
| `pending` | Submitted to provider, awaiting carrier review |
| `approved` | Active, numbers can send under this campaign |
| `rejected` | Review failed, see `rejection_reason` |
| `suspended` | Was approved but suspended for violations |

## Compliance Documents

Carriers require supporting documentation during brand and campaign registration. Upload these before submitting for review.

### Required Documents

| Document | Purpose |
|----------|---------|
| `privacy_policy` | Your company's privacy policy covering SMS data handling |
| `terms_of_service` | Terms of service for your messaging program |
| `opt_in_form` | The form or mechanism users use to opt in to messaging |

### Upload Endpoint

```
POST /api/v1/tenants/{tid}/10dlc/compliance-docs
Content-Type: multipart/form-data

Fields:
  brand_id: uuid
  document_type: privacy_policy | terms_of_service | opt_in_form
  file: (upload)
```

Files are stored in MinIO under `tenants/{tid}/10dlc/{brand_id}/{document_type}/{filename}`.

### List Documents

```
GET /api/v1/tenants/{tid}/10dlc/compliance-docs?brand_id={brand_id}
```

## Status Checking and Monitoring

Both brands and campaigns have `/status` endpoints that poll the upstream provider (ClearlyIP or Twilio) for the latest registration status. Call these periodically or on-demand to sync local records with provider state.

```
GET /api/v1/tenants/{tid}/10dlc/brands/{id}/status
GET /api/v1/tenants/{tid}/10dlc/campaigns/{id}/status
```

These endpoints update the local database record with the provider's current status, rejection reasons, and approval timestamps.

## Common Rejection Reasons and Remediation

### Brand Rejections

| Reason | Fix |
|--------|-----|
| EIN mismatch | Verify EIN matches IRS records exactly (including dashes) |
| Business not found | Ensure business is registered with state and has a web presence |
| Insufficient web presence | Add a public website with business info, address, phone number |
| Invalid vertical | Choose the most specific vertical that matches your business |

### Campaign Rejections

| Reason | Fix |
|--------|-----|
| Insufficient opt-in description | Describe exactly how users consent to receive messages |
| Missing sample messages | Provide 2-5 realistic message examples with opt-out language |
| Use case mismatch | Ensure the use case matches your actual messaging behavior |
| Missing opt-out mechanism | Include STOP keyword handling in every message sample |
| Prohibited content | Remove any restricted content (SHAFT categories) |

## RBAC Permissions

| Permission | Roles |
|-----------|-------|
| `manage_dids` | MSP Super Admin, MSP Tech, Tenant Admin |
| `view_dids` | All roles |

10DLC endpoints use the DID permission set since they are part of the number management workflow.

## Key Source Files

| File | Purpose |
|------|---------|
| `api/src/new_phone/routers/ten_dlc.py` | 10DLC API endpoints (brands, campaigns, docs) |
| `api/src/new_phone/services/ten_dlc_service.py` | 10DLC business logic |
| `api/src/new_phone/schemas/ten_dlc.py` | Request/response schemas |
| `api/src/new_phone/models/ten_dlc.py` | Database models (brands, campaigns, docs) |
