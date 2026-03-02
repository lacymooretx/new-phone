# FreeSWITCH High Availability Architecture

## Overview

This document describes the high-availability (HA) architecture for FreeSWITCH in the New Phone platform. The design uses an active/standby pair behind the Rust SIP proxy service, with shared PostgreSQL for configuration and Redis for state coordination.

## Architecture

```
                    ┌──────────────────────┐
                    │    SIP Clients /      │
                    │    SIP Trunks         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   sip-proxy (Rust)   │
                    │   Active failover    │
                    │   Health monitoring   │
                    └─────┬──────────┬─────┘
                          │          │
               ┌──────────▼──┐  ┌───▼──────────┐
               │ FreeSWITCH  │  │ FreeSWITCH   │
               │  (Primary)  │  │  (Standby)   │
               └──────┬──────┘  └──────┬───────┘
                      │                │
          ┌───────────▼────────────────▼───────────┐
          │              PostgreSQL                  │
          │   (xml_curl config, CDRs, state)        │
          └──────────────────┬─────────────────────┘
                             │
          ┌──────────────────▼─────────────────────┐
          │                Redis                    │
          │   (Presence, parking, camp-on state)   │
          └────────────────────────────────────────┘
```

## Active/Standby Model

### Primary Node
- Handles all SIP signaling and media processing
- Connects to PostgreSQL via xml_curl for dynamic configuration
- Publishes ESL events consumed by the event-router service
- Stores CDRs, recordings, and voicemail to shared storage

### Standby Node
- Identical FreeSWITCH configuration
- Connected to the same PostgreSQL and Redis instances
- Not actively processing calls
- Maintained in a warm-standby state (FreeSWITCH process running, sofia profiles loaded)
- Ready to accept calls within seconds of failover

### Failover Decision
The `sip-proxy` Rust service is responsible for failover decisions:

1. Continuously health-checks both FreeSWITCH nodes via ESL (`api status`)
2. Health check interval: 5 seconds
3. Failover trigger: 3 consecutive failed health checks (15 seconds of unresponsiveness)
4. On failover, sip-proxy re-routes all new SIP traffic to the standby node
5. The standby node becomes the new primary

### Failback
Failback is manual by default to prevent flapping:

1. Operator verifies the original primary is healthy
2. Operator triggers failback via API: `POST /api/v1/admin/freeswitch/failback`
3. sip-proxy drains active calls from current primary (waits for calls to complete or timeout)
4. sip-proxy switches routing back to the original primary

## Shared PostgreSQL Backend

### Configuration via xml_curl
Both FreeSWITCH nodes use xml_curl to fetch configuration from the API:

- **Directory**: User/extension registrations (`/freeswitch/directory`)
- **Dialplan**: Call routing rules (`/freeswitch/dialplan`)
- **Configuration**: Module configs (`/freeswitch/configuration`)

Because configuration lives in PostgreSQL (served by the API), both nodes always have identical configuration. Changes made via the API are immediately available to whichever node fetches config next.

### CDR Storage
CDRs are written to PostgreSQL by the ESL event listener service, not directly by FreeSWITCH. This means CDRs are centralized regardless of which node handles the call.

### Database Replication Requirements
For HA, PostgreSQL itself must be highly available:

- **Minimum**: PostgreSQL streaming replication with a synchronous standby
- **Recommended**: Patroni cluster (3 nodes) with automatic failover
- **Connection**: Use a PostgreSQL connection pooler (PgBouncer) or virtual IP that follows the primary

Configuration parameters for PostgreSQL replication:

```
# Primary
wal_level = replica
max_wal_senders = 5
synchronous_commit = on
synchronous_standby_names = 'standby1'

# Standby
primary_conninfo = 'host=pg-primary port=5432 user=replicator'
hot_standby = on
```

## SIP Proxy Failover (sip-proxy Rust Service)

The sip-proxy service handles:

### SIP Traffic Routing
- Listens on port 5060 (TCP/UDP) and 5061 (TLS)
- Forwards SIP INVITE, REGISTER, and other requests to the active FreeSWITCH node
- Maintains a mapping of active dialogs to route mid-dialog requests correctly

### Health Monitoring
- ESL connection to both FreeSWITCH nodes
- Sends `api status` every 5 seconds
- Tracks response time and success/failure

### Configuration
Environment variables for sip-proxy:

```
FREESWITCH_PRIMARY=freeswitch-1:5061
FREESWITCH_STANDBY=freeswitch-2:5061
REDIS_URL=redis://redis:6379/0
HEALTH_CHECK_INTERVAL=5
FAILOVER_THRESHOLD=3
DRAIN_TIMEOUT=300
```

## Media Recovery Patterns

### In-Progress Calls During Failover
Active calls at the moment of failover will be lost. This is an accepted trade-off for the active/standby model. Mitigation strategies:

1. **Call recovery notification**: The event-router detects the failover and notifies affected users via WebSocket that their call was dropped
2. **Auto-redial**: The web/mobile client can offer a one-click redial option
3. **CDR integrity**: Partial CDRs are written for interrupted calls with disposition `FAILOVER_DROP`

### RTP Relay Re-establishment
The rtp-relay Rust service manages media paths:

1. On failover, rtp-relay detects that the FreeSWITCH node has changed
2. New calls use the standby node's media address
3. The rtp-relay updates its NAT traversal mappings accordingly
4. No action needed for calls that were already dropped by the failover

### Recording Continuity
- Recordings in progress at failover time will be partial
- The recording file is closed and stored as-is
- A metadata flag `partial_recording=true` is set on the recording record
- The new primary starts fresh recordings for any new calls

## Deployment Checklist

### Prerequisites
- [ ] Two FreeSWITCH nodes with identical Docker images and configuration
- [ ] PostgreSQL with replication configured (or Patroni cluster)
- [ ] Redis (can be standalone for small deployments; Sentinel for HA)
- [ ] Shared storage for recordings (MinIO/S3)
- [ ] sip-proxy configured with both FreeSWITCH node addresses
- [ ] DNS or load balancer pointing SIP traffic to sip-proxy

### FreeSWITCH Node Setup
- [ ] Both nodes use the same xml_curl API endpoint
- [ ] Both nodes have the same ESL password
- [ ] Both nodes have TLS certificates configured
- [ ] Both nodes can reach PostgreSQL, Redis, and MinIO
- [ ] ESL ports are accessible from sip-proxy and event-router

### Network Configuration
- [ ] SIP TLS (5061) exposed through sip-proxy only
- [ ] WSS (7443) load-balanced or exposed on primary only
- [ ] ESL (8021) accessible only from internal network
- [ ] RTP port range (10000-10999) open on both nodes

### Validation Steps
1. Start both FreeSWITCH nodes and verify both register with PostgreSQL
2. Verify sip-proxy can reach both nodes via ESL
3. Place a test call through sip-proxy to the primary
4. Stop the primary and verify failover completes within 15 seconds
5. Place a test call to the standby (now primary)
6. Restart the original primary and verify it comes back as standby
7. Test manual failback

## Monitoring Considerations

### Metrics to Watch
- `freeswitch_up` (per node) — must be 1 for at least one node at all times
- `freeswitch_active_channels` (per node) — zero on standby, non-zero on primary
- `sip_proxy_failover_count` — should rarely increment
- `sip_proxy_active_node` — which node is currently primary
- `freeswitch_registrations_total` (per node) — registrations should follow the active node

### Alert Rules
- **Critical**: Both FreeSWITCH nodes down simultaneously
- **Critical**: Failover occurred (page on-call engineer)
- **Warning**: Standby node unreachable (degraded HA)
- **Warning**: Failover count > 2 in 1 hour (potential flapping)

### Dashboards
The Grafana telephony dashboard should include:
- Active node indicator (primary vs standby)
- Per-node channel count
- Failover event timeline
- Registration distribution across nodes

## Recovery Procedures

### Scenario: Primary Node Crash
1. sip-proxy automatically fails over to standby (within 15 seconds)
2. Verify calls are flowing to standby: check `freeswitch_active_channels`
3. Investigate and fix the crashed primary
4. Restart the primary and verify it starts as standby
5. (Optional) Trigger manual failback during a maintenance window

### Scenario: Database Failover
1. Both FreeSWITCH nodes will experience xml_curl failures
2. FreeSWITCH will use cached configuration for existing registrations
3. New registrations and config changes will fail until DB is back
4. Once PostgreSQL failover completes, both nodes reconnect automatically
5. Run `api xml_flush_cache` on both nodes to clear stale cache

### Scenario: Redis Failure
1. Parking, camp-on, and presence features will be degraded
2. Core call routing continues to work (does not depend on Redis)
3. Restore Redis from RDB/AOF backup or failover to Redis Sentinel standby
4. Services reconnect automatically on Redis recovery

### Scenario: Split Brain (Both Nodes Think They Are Primary)
This should not happen with sip-proxy as the single arbiter. If it does:
1. Immediately stop one node: `docker stop freeswitch-2`
2. Verify sip-proxy is routing to the remaining node
3. Investigate why sip-proxy lost track of node state
4. Fix and restart the stopped node as standby
5. File an incident report

## Capacity Planning

### Single Node Capacity
- 300 concurrent calls per FreeSWITCH node (conservative estimate)
- 1000 SIP registrations per node
- CPU: 4 cores recommended (8 for transcoding-heavy workloads)
- RAM: 4GB minimum, 8GB recommended
- Disk: SSD for recordings, 100GB+ depending on retention

### HA Capacity Impact
- Active/standby means total capacity = single node capacity (not doubled)
- The standby node is idle and available for maintenance, testing, or as a warm spare
- For scale-out beyond 300 channels, deploy additional FreeSWITCH pairs behind the sip-proxy with hash-based routing
