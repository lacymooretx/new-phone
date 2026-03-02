# FreeSWITCH Call Parking vs Asterisk Call Parking

Date: 2026-02-25

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [FreeSWITCH Native Parking Modules](#freeswitch-native-parking-modules)
3. [Feature-by-Feature Comparison](#feature-by-feature-comparison)
4. [mod_valet_parking Deep Dive](#mod_valet_parking-deep-dive)
5. [Limitations of FreeSWITCH Parking vs Asterisk](#limitations)
6. [Design: Full-Featured External Parking Service](#external-parking-service-design)

---

## Executive Summary

FreeSWITCH has native call parking support through three mechanisms:

| Module | Purpose | BLF Support | Slot Numbers | Timeout |
|---|---|---|---|---|
| **mod_valet_parking** | Full valet-style parking with named lots and numbered slots | Yes (presence) | Yes | Yes (orbit) |
| **mod_fifo** | FIFO queue-based parking (one caller per FIFO = one slot) | Partial (SLA/BLA) | Simulated via named FIFOs | Yes (orbit_exten) |
| **mod_dptools: park** | Raw channel hold, no slot management | No | No | Yes (park_timeout) |

**mod_valet_parking** is the closest equivalent to Asterisk's res_parking and is the recommended module for traditional call parking. It covers roughly 80% of Asterisk parking functionality natively. The remaining 20% -- primarily "return to parker" on timeout, attended parking workflows, and advanced multi-lot BLF -- requires dialplan scripting or an external ESL-based service.

---

## FreeSWITCH Native Parking Modules

### mod_valet_parking (Recommended)

The primary parking module. Places a channel on hold inside the switch (not on the phone). Calls are parked into named "lots" with numbered "slots." The same extension used to park is used to retrieve -- first caller in gets parked; next caller dialing the same slot gets bridged to the parked caller.

**Key capabilities:**
- Named parking lots (e.g., `sales_lot`, `support_lot`)
- Numbered parking slots with configurable ranges
- Auto-slot selection (finds first available slot in a range)
- Slot number announcement to the parker via TTS/audio
- Parking timeout with orbit to a configurable extension
- BLF/presence support via `park+<lotname>` and `park+<slotnumber>` subscriptions
- Custom events (`valet_parking::info`) with hold/bridge/exit actions
- API command `valet_info` for querying lot/slot status
- Multi-domain support (`lotname@domain`)
- bind_meta_app support (park during active call via DTMF)

### mod_fifo

A first-in, first-out queue system. Can be repurposed for parking by creating one FIFO per parking slot (one caller per FIFO). The dialplan checks FIFO occupancy to decide whether to park or retrieve.

**Parking-relevant capabilities:**
- FIFO count check to determine park vs retrieve
- SLA/BLA presence for BLF monitoring
- Chime/music while parked
- Orbit extension on timeout (`fifo_orbit_exten`)
- FIFO-order retrieval (good for stacking calls)

**Limitations for parking use:**
- BLF requires presence_map configuration (more complex setup)
- No auto-slot assignment
- No slot number announcement
- Each "slot" is a separate named FIFO

### mod_dptools: park

The most basic option. Simply puts a channel into a held state on the switch. No slot numbering, no retrieval by extension -- calls must be retrieved via `uuid_bridge` or `uuid_transfer` commands.

**Use case:** Only useful as a building block for a fully custom external parking service.

---

## Feature-by-Feature Comparison

### 1. Park a Call to a Numbered Slot

**Asterisk (res_parking):**
- Blind transfer to `parkext` (e.g., 700) auto-assigns next slot in `parkpos` range (701-720)
- `PARKINGEXTEN` channel variable forces a specific slot
- `Park()` dialplan application with lot name parameter
- Slot assignment is automatic and sequential (`findslot=next`)

**FreeSWITCH (mod_valet_parking):**
- Blind transfer to a slot extension (e.g., 6001) parks directly in that slot
- `valet_park <lot> auto in <min> <max>` auto-assigns first available slot in range
- `valet_park <lot> <slot_number>` parks in a specific slot
- Slot assignment works but is hash-based, not strictly sequential

**Verdict:** Both platforms support this well. FreeSWITCH is slightly more flexible because you can directly target a specific slot number or use auto-assignment. Asterisk's sequential assignment is simpler for basic use.

---

### 2. Retrieve a Parked Call by Dialing the Slot Number

**Asterisk:**
- Dial the slot extension directly (e.g., dial 701 to retrieve the call parked in slot 701)
- `ParkedCall(<lot_name>,<slot>)` application
- Slot extensions are auto-created in the parking context

**FreeSWITCH:**
- Dial the same slot extension (e.g., dial 6001 -- if occupied, retrieves the parked call)
- `valet_park <lot> <slot>` -- if slot is occupied, bridges to parked caller
- `valet_park <lot> auto out <min> <max>` retrieves the longest-waiting call in range
- `valet_park <lot> ask <min> <max> <timeout> <prompt>` prompts caller to enter slot number

**Verdict:** Both handle this natively. FreeSWITCH adds the "ask" mode (prompted retrieval) and "auto out" (longest-waiting retrieval) which Asterisk lacks natively.

---

### 3. Park Timeout (Call Returns to Parker or Goes to a Destination)

**Asterisk:**
- `parkingtime` sets timeout in seconds (default 45)
- `comebacktoorigin=yes` (default) returns call to the original parker
- `comebackdialtime` sets how long to ring the parker (default 30)
- `comebackcontext` routes timed-out calls to custom dialplan when `comebacktoorigin=no`
- Automatic: no scripting required for return-to-parker behavior

**FreeSWITCH:**
- `valet_parking_timeout` channel variable sets timeout in seconds
- `valet_parking_orbit_exten` transfers to a specified extension on timeout
- `valet_parking_orbit_dialplan` and `valet_parking_orbit_context` control routing
- Does NOT automatically return to the parker -- the orbit extension must be explicitly set
- Returning to the parker requires manual implementation:
  - Store parker's extension and parked call UUID using `hash` API
  - Set orbit extension to a "recall" extension
  - That recall extension looks up the parker and rings them
  - Or use `sched_api`/`sched_transfer` to schedule a callback
  - A Lua script is recommended to cancel the scheduled callback if someone retrieves the call first

**Verdict:** Asterisk wins here. `comebacktoorigin=yes` is built-in and automatic. FreeSWITCH requires custom dialplan logic or scripting to achieve the same result.

---

### 4. BLF (Busy Lamp Field) Monitoring of Parking Slots

**Asterisk:**
- `parkinghints=yes` in res_parking.conf enables automatic hint generation
- Hints use format `park:<slot>@<lot_context>` (e.g., `park:701@parkedcalls`)
- Phones subscribe to slot extensions; BLF lights up when slot is occupied
- Pressing the BLF button retrieves the parked call (one-button park/retrieve)
- Works with all major phone brands out of the box

**FreeSWITCH:**
- mod_valet_parking fires presence events natively
- Subscribe to `park+<slotnumber>` for individual slot status
- Subscribe to `park+<lotname>` for entire lot status
- Presence states: "Holding" (parked, unbridged), "Active" (bridged), "Empty"
- Works with SIP SUBSCRIBE/NOTIFY for BLF
- Requires phone to be configured to subscribe to `park+<slot>` presence IDs
- May require SIP profile setting `presence-proto-lookup=true`

**Verdict:** Both support BLF. Asterisk's approach is slightly more turnkey (`parkinghints=yes` and done). FreeSWITCH requires understanding the `park+` presence ID format and appropriate phone provisioning, but it works well once configured.

---

### 5. Attended vs Blind Parking

**Asterisk:**
- **Blind parking:** Transfer to `parkext` (e.g., 700) or use `#72` DTMF feature code
- **Attended parking:** Use attended transfer; caller hears the slot number, can then tell the target party
- `Park()` application with options for both modes
- `K`/`k` options on `Dial()` allow calling/called party to initiate parking

**FreeSWITCH:**
- **Blind parking:** Blind transfer to a slot extension (e.g., 6001) or to auto-park extension (e.g., 8500)
- **Attended parking:** Use `bind_meta_app` to park mid-call via DTMF (e.g., `*1` during a call)
- Auto-park announces the slot number to the transferring party
- No built-in equivalent of Asterisk's `K`/`k` Dial() options, but `bind_meta_app` achieves the same effect

**Verdict:** Both support attended and blind parking. The mechanisms differ but achieve equivalent results. Asterisk's integration with the `Dial()` application is more streamlined; FreeSWITCH's `bind_meta_app` is more general-purpose.

---

### 6. Parking Lot Announcements

**Asterisk:**
- `ParkAndAnnounce()` application parks the call and announces to another channel
- Announcement template uses colon-separated audio files
- The word `PARKED` in the template is replaced with the slot number
- `PARKEDAT` channel variable holds the slot number after parking
- Can dial a page group or extension to announce the parked call

**FreeSWITCH:**
- `valet_announce_slot=true` channel variable causes the slot number to be spoken to the parker
- Auto-mode (`valet_park <lot> auto in <min> <max>`) automatically voices the slot number
- No built-in equivalent of `ParkAndAnnounce` (park + announce to a third party)
- Announcing to a third party (e.g., page group) requires custom dialplan or ESL scripting

**Verdict:** FreeSWITCH announces the slot number to the parker natively. But Asterisk's `ParkAndAnnounce` goes further by allowing announcement to a third-party channel (e.g., overhead paging). FreeSWITCH can achieve this with additional scripting.

---

### 7. Multiple Parking Lots (Departments)

**Asterisk:**
- Multiple `[parkinglot_name]` sections in `res_parking.conf`
- Each lot has its own `parkext`, `parkpos` range, `context`, and settings
- `CHANNEL(parkinglot)` variable selects lot dynamically
- Dynamic parking lots can be created at runtime via channel variables
- Each lot can have independent timeout, comebacktoorigin, and BLF settings

**FreeSWITCH:**
- Lot name is the first parameter to `valet_park` (e.g., `sales_lot`, `support_lot`)
- Different dialplan extensions can route to different lots with different slot ranges
- Multi-domain support: `lotname@${domain_name}`
- `valet_info` API can filter by lot name
- Presence subscriptions work per-lot (`park+sales_lot`) or per-slot (`park+8501`)
- No separate configuration file per lot -- all controlled via dialplan parameters

**Verdict:** Both support multiple lots. Asterisk has a more structured configuration approach (dedicated config sections per lot). FreeSWITCH is more flexible but less formalized -- lot creation is implicit via dialplan usage.

---

## mod_valet_parking Deep Dive

### Dialplan Configuration

**Auto-park with slot announcement (recommended setup):**

```xml
<!-- Park a call: transfer to 8500, system auto-selects slot 8501-8599 -->
<extension name="valet-park-in">
  <condition field="destination_number" expression="^(8500)$">
    <action application="answer"/>
    <action application="valet_park" data="main_lot auto in 8501 8599"/>
  </condition>
</extension>

<!-- Retrieve by slot: dial 8501-8599 directly -->
<extension name="valet-park-retrieve">
  <condition field="destination_number" expression="^(85\d\d)$">
    <action application="answer"/>
    <action application="valet_park" data="main_lot $1"/>
  </condition>
</extension>

<!-- Retrieve longest-waiting: dial 8600 -->
<extension name="valet-park-out-auto">
  <condition field="destination_number" expression="^(8600)$">
    <action application="answer"/>
    <action application="valet_park" data="main_lot auto out 8501 8599"/>
  </condition>
</extension>

<!-- Prompted retrieval: dial 8700, enter slot + # -->
<extension name="valet-park-ask">
  <condition field="destination_number" expression="^(8700)$">
    <action application="answer"/>
    <action application="valet_park" data="main_lot ask 1 11 10000 ivr/ivr-enter_ext_pound.wav"/>
  </condition>
</extension>
```

**With timeout and orbit:**

```xml
<extension name="valet-park-in-with-timeout">
  <condition field="destination_number" expression="^(8500)$">
    <action application="answer"/>
    <action application="set" data="valet_parking_timeout=120"/>
    <action application="set" data="valet_parking_orbit_exten=park_timeout_handler"/>
    <action application="set" data="valet_parking_orbit_context=default"/>
    <action application="set" data="valet_announce_slot=true"/>
    <action application="valet_park" data="main_lot auto in 8501 8599"/>
  </condition>
</extension>
```

**Park during active call via DTMF:**

```xml
<!-- In the Dial command, bind *1 to park the call -->
<action application="bind_meta_app" data="1 b s valet_park::main_lot auto in 8501 8599"/>
<action application="bridge" data="user/1001@${domain_name}"/>
```

### Channel Variables

| Variable | Description |
|---|---|
| `valet_parking_timeout` | Seconds before timeout (0 = indefinite) |
| `valet_parking_orbit_exten` | Extension to transfer to on timeout |
| `valet_parking_orbit_dialplan` | Dialplan for orbit (default: current) |
| `valet_parking_orbit_context` | Context for orbit (default: current) |
| `valet_parking_orbit_exit_key` | DTMF key to manually exit hold |
| `valet_hold_music` | Custom MOH stream |
| `valet_announce_slot` | true/false - announce slot number to parker |

### Events

Custom events fire with subclass `valet_parking::info`:

| Header | Values |
|---|---|
| `Action` | `hold`, `bridge`, `exit` |
| `Valet-Lot-Name` | Name of the parking lot |
| `Valet-Extension` | Slot number |
| `Bridge-To-UUID` | UUID of retrieving channel (on bridge) |

### API Commands

```
# List all lots and their parked calls
api valet_info

# List specific lot
api valet_info main_lot

# Response format (XML):
# <lots>
#   <lot name="main_lot">
#     <extension uuid="abc-123">8501</extension>
#     <extension uuid="def-456">8503</extension>
#   </lot>
# </lots>
```

### Presence/BLF

- Individual slot: phone subscribes to `park+8501` -- shows "Holding"/"Empty"
- Entire lot: phone subscribes to `park+main_lot` -- shows "Active (2 caller(s))"/"Empty"
- Presence states: confirmed (occupied), terminated (empty)

---

## Limitations of FreeSWITCH Parking vs Asterisk <a name="limitations"></a>

### Critical Gaps

1. **No automatic return-to-parker on timeout.** Asterisk's `comebacktoorigin=yes` is a single config line. FreeSWITCH requires custom dialplan + scripting (hash API + sched_api + Lua cancel script) to track who parked the call and ring them back.

2. **No ParkAndAnnounce equivalent.** Asterisk can park a call and simultaneously announce to a page group or extension. FreeSWITCH only announces the slot number to the parker; announcing to a third party requires custom development.

3. **No per-lot configuration file.** Asterisk defines each parking lot in `res_parking.conf` with its own timeout, callback behavior, and BLF settings. FreeSWITCH lots are purely dialplan-driven with no centralized configuration.

4. **No automatic hint/BLF generation.** Asterisk auto-creates hints when `parkinghints=yes`. FreeSWITCH requires phones to be provisioned with the correct `park+<slot>` subscription URIs.

5. **No DTMF feature-code parking from features.conf equivalent.** Asterisk allows `#72` (or any configured sequence) during any bridged call to park. FreeSWITCH requires `bind_meta_app` to be explicitly added to each bridge.

### Minor Gaps

6. **Sequential slot assignment.** Asterisk always assigns the next sequential slot. FreeSWITCH's auto mode finds the first available, which may not be sequential if slots were freed out of order (this is usually fine).

7. **Dynamic parking lots.** Asterisk supports creating parking lots at runtime from templates. FreeSWITCH lots are created implicitly and don't have template inheritance.

8. **Double-parking protection.** If two people simultaneously transfer to the same slot, FreeSWITCH bridges them to each other rather than preventing the collision. Asterisk handles this more gracefully.

---

## Design: Full-Featured External Parking Service <a name="external-parking-service-design"></a>

For environments requiring Asterisk-equivalent parking with full return-to-parker, ParkAndAnnounce, advanced BLF, and multi-lot management, here is a design for an external service built on FreeSWITCH ESL.

### Architecture Overview

```
+-------------------+       ESL (TCP 8021)      +----------------------+
|   FreeSWITCH      | <-----------------------> |  Parking Service     |
|                   |   Events + Commands        |  (Node.js/Python)    |
|  - mod_dptools    |                            |                      |
|  - mod_sofia      |                            |  +----------------+  |
|  - park app       |                            |  | Parking DB     |  |
|                   |                            |  | (PostgreSQL/   |  |
|                   |                            |  |  Redis)        |  |
+-------------------+                            |  +----------------+  |
        ^                                        |                      |
        |  SIP SUBSCRIBE/NOTIFY                  |  +----------------+  |
        |                                        |  | BLF/Presence   |  |
+-------------------+                            |  | Manager        |  |
|  SIP Phones       |                            |  +----------------+  |
|  (BLF buttons)    |                            +----------------------+
+-------------------+
```

### Components

#### 1. Parking Service (Core Application)

**Technology:** Node.js with `esl` package, or Python with `greenswitch`/`ESL` bindings.

**Responsibilities:**
- Manage parking slot allocation and state
- Track parker identity (who parked the call)
- Handle timeout with return-to-parker logic
- Announce to third-party channels
- Serve as single source of truth for parking state

**Database Schema (PostgreSQL or Redis):**

```sql
CREATE TABLE parking_lots (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,        -- e.g., 'sales', 'support'
    slot_min INTEGER NOT NULL,                -- e.g., 8501
    slot_max INTEGER NOT NULL,                -- e.g., 8599
    timeout_seconds INTEGER DEFAULT 120,
    comeback_to_origin BOOLEAN DEFAULT TRUE,
    comeback_dial_time INTEGER DEFAULT 30,
    fallback_extension VARCHAR(32),           -- if parker doesn't answer
    moh_stream VARCHAR(256) DEFAULT 'local_stream://moh'
);

CREATE TABLE parked_calls (
    id SERIAL PRIMARY KEY,
    lot_id INTEGER REFERENCES parking_lots(id),
    slot_number INTEGER NOT NULL,
    parked_uuid VARCHAR(64) NOT NULL,         -- UUID of the parked channel
    parker_extension VARCHAR(32),             -- who parked it (for comeback)
    parker_uuid VARCHAR(64),                  -- UUID of parker's channel
    parker_name VARCHAR(128),                 -- caller ID name of parker
    caller_id_number VARCHAR(32),             -- caller's CID for display
    caller_id_name VARCHAR(128),
    parked_at TIMESTAMP DEFAULT NOW(),
    timeout_at TIMESTAMP,                     -- when to trigger timeout
    status VARCHAR(16) DEFAULT 'parked',      -- parked, retrieving, timeout, retrieved
    retrieved_by VARCHAR(32),                 -- extension that retrieved
    UNIQUE(lot_id, slot_number)
);

CREATE TABLE parking_lot_blf (
    id SERIAL PRIMARY KEY,
    lot_id INTEGER REFERENCES parking_lots(id),
    slot_number INTEGER NOT NULL,
    presence_state VARCHAR(16) DEFAULT 'empty', -- empty, holding, ringing
    UNIQUE(lot_id, slot_number)
);
```

#### 2. ESL Event Handler

The service connects to FreeSWITCH via ESL inbound mode and subscribes to relevant events:

```javascript
// Pseudocode - Node.js ESL inbound connection
const esl = require('esl');

const conn = new esl.Connection('127.0.0.1', 8021, 'ClueCon');

conn.on('ready', () => {
    // Subscribe to parking-relevant events
    conn.subscribe([
        'CHANNEL_PARK',           // Channel entered park state
        'CHANNEL_BRIDGE',         // Two channels bridged
        'CHANNEL_HANGUP',         // Channel hung up
        'CUSTOM valet_parking::info',  // Valet parking events
        'DTMF',                   // For DTMF-based parking triggers
    ]);
});

conn.on('event', (event) => {
    const eventName = event.getHeader('Event-Name');
    const subclass = event.getHeader('Event-Subclass');

    if (subclass === 'valet_parking::info') {
        handleValetEvent(event);
    } else if (eventName === 'CHANNEL_PARK') {
        handleChannelPark(event);
    } else if (eventName === 'CHANNEL_HANGUP') {
        handleHangup(event);
    }
});
```

#### 3. Parking Workflow (ESL-Controlled)

**Option A: Hybrid (use mod_valet_parking + ESL for enhanced features)**

Keep mod_valet_parking for the core park/retrieve mechanism. The ESL service listens to `valet_parking::info` events and adds:
- Return-to-parker on timeout (via `sched_api` or service-managed timers)
- ParkAndAnnounce (originate a call to a page group after parking)
- Enhanced BLF management
- Centralized logging and slot tracking

```javascript
async function handleValetEvent(event) {
    const action = event.getHeader('Action');
    const lot = event.getHeader('Valet-Lot-Name');
    const slot = event.getHeader('Valet-Extension');
    const uuid = event.getHeader('Unique-ID');

    if (action === 'hold') {
        // Call was just parked
        const parkerExt = event.getHeader('variable_park_caller_extension');

        await db.insertParkedCall({
            lot, slot, uuid,
            parker_extension: parkerExt,
            timeout_at: new Date(Date.now() + lot.timeout_seconds * 1000)
        });

        // Schedule timeout callback
        scheduleTimeout(lot, slot, uuid, parkerExt);

        // Update BLF
        await updatePresence(slot, 'holding');

        // Optional: ParkAndAnnounce to page group
        if (lot.announce_extension) {
            announceParkedCall(lot.announce_extension, slot, parkerExt);
        }
    } else if (action === 'bridge') {
        // Call was retrieved
        await db.updateParkedCall(lot, slot, { status: 'retrieved' });
        cancelTimeout(lot, slot);
        await updatePresence(slot, 'empty');
    } else if (action === 'exit') {
        // Call exited parking (hangup or timeout)
        await db.updateParkedCall(lot, slot, { status: 'exit' });
        await updatePresence(slot, 'empty');
    }
}
```

**Option B: Fully ESL-Controlled (use mod_dptools: park + ESL for everything)**

The service takes full control. The dialplan routes parking requests to the ESL service via socket application:

```xml
<!-- Dialplan: route parking requests to external service -->
<extension name="park-request">
  <condition field="destination_number" expression="^85(\d\d)$">
    <action application="socket" data="127.0.0.1:9090 async full"/>
  </condition>
</extension>
```

The ESL service then:
1. Receives the call via outbound socket
2. Checks slot availability in the database
3. Either parks the call (`park` app) or bridges to a parked call (`uuid_bridge`)
4. Manages all state, timers, and announcements

#### 4. Return-to-Parker Implementation

```javascript
function scheduleTimeout(lot, slot, parkedUuid, parkerExtension) {
    const timeoutMs = lot.timeout_seconds * 1000;

    const timer = setTimeout(async () => {
        // Check if call is still parked
        const call = await db.getParkedCall(lot.name, slot);
        if (!call || call.status !== 'parked') return;

        if (lot.comeback_to_origin && parkerExtension) {
            // Ring the parker
            await db.updateParkedCall(lot.name, slot, { status: 'timeout' });
            await updatePresence(slot, 'ringing');

            // Originate a call to the parker, then bridge to parked call
            const originateCmd = `originate {origination_caller_id_name='Parked Call ${slot}',` +
                `origination_caller_id_number=${slot},` +
                `ignore_early_media=true}` +
                `user/${parkerExtension}@${domain} &park()`;

            conn.api(originateCmd, (res) => {
                const newUuid = res.getBody().trim().replace('+OK ', '');
                if (newUuid && !newUuid.startsWith('-ERR')) {
                    // Wait for answer, then bridge
                    waitForAnswer(newUuid, () => {
                        conn.api(`uuid_bridge ${parkedUuid} ${newUuid}`);
                        db.updateParkedCall(lot.name, slot, { status: 'retrieved' });
                        updatePresence(slot, 'empty');
                    }, () => {
                        // Parker didn't answer -- send to fallback
                        if (lot.fallback_extension) {
                            conn.api(`uuid_transfer ${parkedUuid} ${lot.fallback_extension}`);
                        }
                        updatePresence(slot, 'empty');
                    }, lot.comeback_dial_time * 1000);
                }
            });
        } else if (lot.fallback_extension) {
            // No comeback -- send to fallback extension
            conn.api(`uuid_transfer ${parkedUuid} ${lot.fallback_extension}`);
            updatePresence(slot, 'empty');
        }
    }, timeoutMs);

    // Store timer reference for cancellation
    activeTimers.set(`${lot.name}:${slot}`, timer);
}

function cancelTimeout(lot, slot) {
    const key = `${lot}:${slot}`;
    const timer = activeTimers.get(key);
    if (timer) {
        clearTimeout(timer);
        activeTimers.delete(key);
    }
}
```

#### 5. BLF/Presence Management

**Option A: Let mod_valet_parking handle it (simplest)**

mod_valet_parking already fires presence events. Phones subscribe to `park+<slot>`. This works for basic BLF (lit = occupied, dark = empty).

**Option B: Custom presence via ESL (for enhanced states)**

For richer BLF states (e.g., blinking = timeout ringing), use ESL to send custom presence events:

```javascript
async function updatePresence(slot, state) {
    // Map state to SIP presence
    const presenceMap = {
        'empty':    { status: 'Available', rpid: 'unknown' },
        'holding':  { status: 'On The Phone', rpid: 'on-the-phone' },
        'ringing':  { status: 'Ringing', rpid: 'unknown' },
    };

    const p = presenceMap[state];

    // Fire a presence event via ESL
    // This requires crafting a PRESENCE_IN event
    const eventBody = [
        `sendevent PRESENCE_IN`,
        `proto: park`,
        `login: park+${slot}`,
        `from: park+${slot}`,
        `status: ${p.status}`,
        `rpid: ${p.rpid}`,
        `event_type: presence`,
        `alt_event_type: dialog`,
        ``,
    ].join('\n');

    conn.api(`event PRESENCE_IN`, (res) => {
        // Presence event sent
    });
}
```

**Phone Provisioning for BLF:**

On SIP phones (Yealink, Polycom, Grandstream, etc.), configure BLF keys:

```
# Yealink example (auto-provisioning template)
linekey.1.type = 16            # BLF type
linekey.1.value = park+8501    # Subscribe to parking slot 8501
linekey.1.label = Park 8501
linekey.1.extension = 8501     # Dial 8501 when pressed (retrieve)
linekey.1.line = 1

linekey.2.type = 16
linekey.2.value = park+8502
linekey.2.label = Park 8502
linekey.2.extension = 8502
linekey.2.line = 1
```

#### 6. ParkAndAnnounce Implementation

```javascript
async function announceParkedCall(announceExtension, slot, parkerName) {
    // Originate a call to the announce destination (e.g., page group)
    // Play the announcement, then hang up

    const announcement = `say:en number pronounced ${slot}`;
    // Or use a pre-recorded file: `file_string:///sounds/parked_at.wav!say:en number pronounced ${slot}`

    const cmd = `originate {ignore_early_media=true,` +
        `origination_caller_id_name='Parking',` +
        `origination_caller_id_number=${slot}}` +
        `user/${announceExtension}@${domain} ` +
        `&playback(${announcement})`;

    conn.api(cmd);
}
```

### Summary: When to Use What

| Scenario | Recommendation |
|---|---|
| **Basic parking, small office** | mod_valet_parking alone is sufficient |
| **Need BLF on parking slots** | mod_valet_parking with `park+<slot>` subscriptions |
| **Need return-to-parker on timeout** | mod_valet_parking + dialplan scripting (Lua) or ESL service |
| **Need ParkAndAnnounce** | ESL service (Option A hybrid) |
| **Need full Asterisk-equivalent parking** | ESL service (Option A hybrid) with database tracking |
| **Building a hosted PBX platform** | ESL service (Option B fully controlled) for maximum flexibility |
| **Multi-tenant with per-tenant lot config** | ESL service with database-driven lot definitions |

### Recommended Approach for This Project

Use **Option A (Hybrid)**: Keep mod_valet_parking for the heavy lifting (park/retrieve/BLF) and layer an ESL service on top for:

1. **Return-to-parker**: Listen for `valet_parking::info` hold events, record the parker, schedule timers, originate callback on timeout.
2. **ParkAndAnnounce**: After parking, originate an announcement call to a page group.
3. **Centralized management**: Track all parking state in a database for reporting, monitoring, and multi-server coordination.
4. **Enhanced BLF**: Optionally override presence for richer states.

This gives you 100% of Asterisk's parking capabilities with the added benefit of FreeSWITCH's programmatic flexibility.

---

## Sources

- FreeSWITCH mod_valet_parking documentation: https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Modules/mod_valet_parking_3966447/
- FreeSWITCH Park & Retrieve examples: https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Examples/13173503/
- FreeSWITCH mod_dptools park: https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Modules/mod-dptools/6586687/
- FreeSWITCH mod_fifo: https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Modules/mod_fifo_3966031/
- FreeSWITCH mod_valet_parking source: https://github.com/signalwire/freeswitch/blob/master/src/mod/applications/mod_valet_parking/mod_valet_parking.c
- FreeSWITCH ESL documentation: https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Client-and-Developer-Interfaces/Event-Socket-Library/
- Asterisk Call Parking documentation: https://docs.asterisk.org/Configuration/Features/Call-Parking/
- Asterisk res_parking.conf sample: https://github.com/asterisk/asterisk/blob/master/configs/samples/res_parking.conf.sample
- Asterisk ParkAndAnnounce: https://docs.asterisk.org/Latest_API/API_Documentation/Dialplan_Applications/ParkAndAnnounce/
- FreeSWITCH mailing list - park and BLF: https://freeswitch-users.freeswitch.narkive.com/xEUBY8I7/park-and-blf
- FreeSWITCH mailing list - parking best practices: https://freeswitch-users.freeswitch.narkive.com/hHWdEpdp/call-parking-question-best-practice-advice
- FreeSWITCH mailing list - valet_park timeout: https://freeswitch-users.freeswitch.narkive.com/6sXPRZHK/valet-park-timeout-and-spot-announcement
