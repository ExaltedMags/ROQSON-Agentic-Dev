# Geolocation & Real-Time Tracking Feasibility Audit — ROQSON ERPNext

**Status**: Read-only investigation. No changes made. Date: 2026-03-15
**Prerequisite**: Builds on findings from `GOOGLE_MAPS_AUDIT.md`.

---

## 1. Realtime Infrastructure Summary

### Frappe Socket.IO / Realtime

**Frappe Cloud does support Socket.IO / `frappe.realtime`** as a first-class feature. The `frappe-socketio` service runs as a standard component of all Frappe Cloud deployments. This means `frappe.publish_realtime()` can be called from Server Scripts, and client-side code can listen with `frappe.realtime.on()`.

**However, this instance has never used it.** A keyword search across all Client Scripts and Server Scripts for `realtime`, `publish_realtime`, and `socketio` returned **zero matches**. The infrastructure is available but completely untouched.

**What this means for tracking:**
- A Server Script (called on save of a `Driver Location Log` record) could push position updates to the dashboard browser via `frappe.publish_realtime("driver_position", {driver: ..., lat: ..., lng: ...})`.
- The dashboard Page can call `frappe.realtime.on("driver_position", callback)` to receive position updates without polling.
- This is the canonical Frappe pattern for live updates and is fully supported on this instance.

### Scheduler Capability

Two Scheduler Event scripts exist (both currently disabled for unrelated reasons):
- `Daily Inventory Scan` — disabled, polls Inventory Ledger via raw SQL, sends notifications to President/Stock Manager/Sales roles
- `Order Form Reserved Days` — polls reserved Order Forms, computes elapsed hours

**These confirm the scheduler architecture is functional** and can run SQL queries and update records. A `Driver Location Poller` scheduler script running every 30 seconds would be architecturally feasible.

**Constraint on Frappe Cloud shared hosting**: Custom background workers, long-running processes, Celery beat tasks, or WebSocket push from a custom daemon are **not available** without a dedicated instance or a custom app. You are limited to:
1. Frappe's built-in Scheduler Event scripts (minimum interval: every few minutes for cron-style jobs; not sub-minute)
2. `frappe.publish_realtime()` triggered by document events (on-save of a location record)
3. Client-side polling from the dashboard browser

**The minimum polling interval for Frappe Scheduler is ~1 minute for the lightest events** (`all` = every minute). Sub-minute intervals are not available in Server Script Scheduler Events. This rules out server-side tick-based geofence detection at <60s resolution.

### Rate Limits

Response headers show: `X-RateLimit-Limit: 7200000000` (7.2 billion units, likely per day). This is not a practical concern for internal GPS tracking at 12 drivers × 1 update/30s = ~35,000 requests/day.

### No CSP Restrictions

**Content-Security-Policy header is not set** on this Frappe Cloud instance. This is the most important infrastructure finding for the dashboard. There is no restriction on loading external scripts from `maps.googleapis.com` or `maps.gstatic.com`. Google Maps JavaScript API, the Visualization library (heatmap), and the Maps Static API will all load without modification.

---

## 2. Mobile Constraint Assessment

### Device Context
- **Hardware**: Samsung Galaxy Tab A9 LTE (Android)
- **Access method**: Mobile browser (Frappe web desk) — confirmed by absence of native app artifacts
- **Evidence**: No `manifest.json` (404), no `service_worker.js` (404). This Frappe instance is **not configured as a PWA**. There is no offline capability, no push notifications, no background sync.

### Hard Constraint: Background GPS in Android Browser

**Bottom line: Continuous background GPS tracking from an Android Chrome browser tab is not reliably achievable.**

The browser Geolocation API (`navigator.geolocation.watchPosition`) **works** when the tab is in the foreground and the screen is active. It stops or throttles when:
1. The screen is locked (Android suspends JavaScript timers and geolocation callbacks)
2. Chrome is backgrounded (another app comes to front)
3. Battery saver mode is active
4. The tab is not the active tab in Chrome

On Android Chrome specifically, `watchPosition` callbacks are throttled or paused when the screen goes dark. The tab must remain active, lit, and in the foreground for continuous GPS. For a delivery driver who needs to navigate, this means the tablet screen would need to stay on during the entire trip, which:
- Drains battery significantly
- Is practically not how drivers use tablets (they set them down, navigate with a separate GPS device, etc.)

**Service Workers cannot access the Geolocation API** — background geolocation is explicitly blocked in the Web Platform for privacy reasons, even in PWA service workers.

### Viable Alternatives on Android Browser (no native app)

| Approach | GPS Continuity | UX Friction | Reliability |
|---|---|---|---|
| **Continuous `watchPosition`** (tab stays open) | True continuous (screen must stay on) | High (driver must keep screen active) | Unreliable without screen lock prevention |
| **Manual check-in buttons** ("Depart", "Arrived", "Done") | Event-based, not continuous | Low (one tap per event) | High — driver is already interacting with the form |
| **Periodic GPS snapshot** (driver taps "Update Location" every N minutes) | Periodic (semi-manual) | Medium | Medium |
| **Foreground keep-awake** (use Screen Wake Lock API to prevent sleep while trip is In Transit) | Continuous (while screen is on) | Low-medium (app keeps screen on automatically) | Good — but battery concern |

**Screen Wake Lock API** (`navigator.wakeLock.request('screen')`) is supported on Android Chrome 84+ (Galaxy Tab A9 runs Android 13 → Chrome supports this). A client script on the Trip Ticket form could acquire a wake lock when the trip enters `In Transit` and release it on `Completed` or `Failed`. This keeps the screen on and allows `watchPosition` to run continuously — at the cost of battery drain.

### Honest Verdict

For a thesis-scope system tracking 2–5 concurrent trips (as evidenced by current fleet of 2 vehicles and 5 drivers), the manual check-in approach combined with event-triggered GPS snapshots is **more reliable and appropriate** than continuous tracking. The workflow already has well-defined events (Dispatch → Arrived → Completed/Failed) with server-stamped timestamps. The value of continuous position updates between those events (the truck is somewhere on the road) is limited for this use case.

**Continuous real-time tracking on Android browser is achievable only with Screen Wake Lock + `watchPosition`**, and even then it's fragile. For a production deployment, a lightweight native app (PWA wrapped with Capacitor, or a simple Android WebView app with background geolocation permission) would be the correct infrastructure investment.

---

## 3. Proposed Data Model

### What Currently Exists (relevant to tracking)

**Driver** (5 records, ERPNext native doctype):
- Fields: `full_name`, `status` (Active/Suspended/Left), `transporter` (Link: Supplier), `employee` (Link: Employee), `cell_number`, `address` (Link: ERPNext Address), `license_number`, `expiry_date`
- **No GPS fields. No link to User account. No link to Trips.**
- Cell numbers are mostly empty (only 1 of 5 has a value).

**Trips** (Trip Ticket):
- Has `driverhelper` (Link: Driver) and `vehicle` (Link: Vehicles)
- Only 2 vehicles registered (`VHC-00001`, `VHC-00002`)
- No GPS or coordinate fields
- `dispatch_time`, `arrival_time`, `completion_time`, `proof_time_stamp` — time tracking exists but server-stamped, not continuous

**Trips Table** (child table in Trips):
- Fields: `order_no` (Link: Order Form), `sales_no` (Link: Sales), `items_preview`, `order_details_html`
- **No per-stop address reference, no per-stop GPS fields**

**Vehicles**: `license_plate`, `model`, `archived` — no GPS, no telematics link

**Roles assigned**: President, Driver, DSP, Dispatcher roles all exist. No User records were inspectable due to permissions (403), but the roles are configured in the Trips workflow.

---

### Proposed Schema for Full Tracking Support

#### New Doctype: `Driver Location Log`

```
Purpose: Periodic GPS breadcrumb trail per driver per trip
Naming: DLL-.YYYY.-.#####

Fields:
  driver          Link → Driver            (indexed)
  trip_ref        Link → Trips             (indexed)
  timestamp       Datetime                 (indexed, server-stamped)
  latitude        Float
  longitude       Float
  accuracy        Float  (meters, from Geolocation API accuracy property)
  speed           Float  (m/s, from Geolocation API speed property, nullable)
  heading         Float  (degrees, nullable)
  event_type      Select [periodic / arrived / departed / geofence_enter / geofence_exit]
  geofence_ref    Data   (name of the PH Address that triggered the geofence event, nullable)
  is_latest       Check  (flag: True for most recent row per driver, for fast dashboard queries)
```

**Indexing strategy**: Index `(driver, is_latest)` and `(trip_ref, timestamp)`. The dashboard polls for `is_latest = 1` rows to get current positions of all active drivers — this is a single-table scan of at most 12 rows.

#### Modification to `Trips` (Trip Ticket)

Add fields:
```
warehouse_lat     Float  (read-only, set on dispatch from ROQSON Settings)
warehouse_lng     Float  (read-only)
delivery_lat      Float  (read-only, set from delivery_address_ref → PH Address)
delivery_lng      Float  (read-only)
geofence_radius   Int    (meters, default 150, configurable per trip)
```

#### Modification to `Driver` (ERPNext native — handle carefully)

The native `Driver` doctype can be extended with Custom Fields:
```
user_account      Link → User     (which ERPNext login does this driver use?)
current_trip      Link → Trips    (denormalized: current active trip, for fast lookup)
last_seen_lat     Float           (last known position, for dashboard fallback)
last_seen_lng     Float
last_seen_at      Datetime
```

**Warning**: `Driver` is an ERPNext standard doctype. Adding Custom Fields is the correct approach — do not modify the DocType definition directly.

#### Modification to `ROQSON Settings` (to be created per Google Maps Audit)

Add:
```
warehouse_lat     Float
warehouse_lng     Float
warehouse_name    Data   ("ROQSON Warehouse")
geofence_radius_default  Int  (meters, default 150)
```

---

### Workflow State Mapping to Real-World Events

The `Time in Time out` Workflow (active on Trips) has these states and transitions:

```
Pending ──[Dispatch]──► In Transit ──[Mark Delivered]──► Completed
                    └──[Mark Delivery Failed]──► Failed
                    └──[Cancel]──► Cancelled

Pending → Cancelled  (Dispatcher, Admin, Manager, President)
Draft → Cancelled    (same roles)
In Transit → Cancelled (same roles)

States defined but with NO clear transition INTO them from normal flow:
  Arrived   (exists in states list, transitions reference it, but not reachable from Pending)
  Delivered (same situation — ghost state)
  Received  (3 live records have this state — likely legacy)
```

**Critical finding**: The `Arrived` and `Delivered` workflow states exist in the state list and have `Mark Delivered / Mark Delivery Failed` transitions from them, but there is **no transition that leads INTO** `Arrived` from `In Transit`. The current live flow is: `Pending → In Transit → Completed` (skipping `Arrived`). The `Time in Time out` server script stamps `custom_arrival_time` when entering `Arrived`, but drivers never reach that state through the current workflow.

This means the Time In (arrival stamp) mechanism is **partially broken by design** — the workflow doesn't route through `Arrived`. The `Timestamping` API script handles `time_in` and `time_out` as separate actions outside the workflow transitions.

For GPS geofencing to work cleanly, the `Pending → Arrived → Completed` path needs to be activated or the workflow redesigned to include a `Time In` transition from `In Transit → Arrived`.

---

## 4. Dashboard Feasibility

### Existing Dashboard Infrastructure

**Custom Pages**: Zero. All 16 pages in the system are standard ERPNext pages (backups, BOM comparison, permission manager, POS, stock balance, etc.). There is no existing operations monitoring page.

**Custom Dashboards**: One — `Sales Dashboard` — created 2025-09-02, contains: Sales Order Trends, Top Customers, Profit and Loss charts. This is a standard ERPNext Dashboard (chart containers), not a custom HTML page. It cannot host a map.

**Custom Reports**: Three, all inventory-related (Cost Tier Inventory, Inventory Balance, Reserved Stock by Order). No Sales/delivery reports. No geographic reports.

### The President Role

The `President` role is confirmed in the system (found in Trips workflow transitions — can cancel trips). The role appears in the `Daily Inventory Scan` scheduler script's notification target list alongside System Manager, Stock Manager, and Sales. This suggests the President receives stock notifications, implying they use the system actively.

The President cannot directly access `DocPerm` API (403 from the audit query), so explicit DocPerm listing wasn't possible. Based on workflow membership and notification targeting, the President has at minimum: read access to Trips, read access to inventory data, ability to cancel trips.

### Technical Requirements for the Live Map Page

A custom Frappe `Page` is the correct container for the President's dashboard. Pages in ERPNext are full HTML/JS/CSS documents loaded in the Frappe desk shell. They have access to all `frappe.*` client-side APIs.

**What is needed:**
1. A `Page` DocType record with an HTML template + JS controller
2. A whitelisted API endpoint (Server Script, type: API) that returns current driver positions
3. The Maps JavaScript API loaded from `maps.googleapis.com`
4. A polling loop OR a `frappe.realtime.on` listener for position updates

**Feasibility: HIGH.** No CSP blocks external scripts. Frappe Pages support arbitrary HTML/JS. `frappe.publish_realtime` is available for push updates.

**Implementation sketch:**
```javascript
// Frappe Page JS
frappe.pages['operations-map'].on_page_load = function(wrapper) {
    // Load Maps JS API
    const script = document.createElement('script');
    script.src = 'https://maps.googleapis.com/maps/api/js?key=KEY&libraries=visualization&callback=initMap';
    document.head.appendChild(script);

    // Listen for realtime position updates
    frappe.realtime.on('driver_position', (data) => {
        updateDriverMarker(data.driver, data.lat, data.lng, data.status);
    });

    // Polling fallback (every 15s) for when driver device is offline
    setInterval(() => {
        frappe.call({
            method: 'get_active_driver_positions',  // API-type Server Script
            callback(r) { r.message.forEach(updateDriverMarker); }
        });
    }, 15000);
};
```

**The `get_active_driver_positions` API script** would query `Driver Location Log` where `is_latest = 1` and the associated trip is in `In Transit` state — returning at most 12 rows for the dashboard.

### Rendering 12 Markers

The Maps JavaScript API handles 12 animated markers trivially. Options:
- **Standard markers** with custom SVG icons (truck icon, color-coded by status)
- **InfoWindow** on marker click: driver name, current trip, last updated timestamp, delivery address
- **Polyline** showing last N breadcrumb points per driver

At 12 concurrent drivers, there are no performance concerns with the Maps JS API.

### Peak Concurrency Estimate

Based on the Trip record timestamps and current fleet size:
- **Current fleet**: 2 vehicles, 5 drivers
- **Peak observed on 2026-03-14**: 7 trips in `In Transit` simultaneously (all test data, but demonstrates testing scale)
- **Realistic production peak**: 2–5 concurrent active trips (limited by 2 vehicles)
- **Target requirement (12 drivers)**: Would require fleet expansion to at least 8–10 vehicles. The system can support this; the schema should be designed for 12 from the start.

---

## 5. Analytics Readiness

### Current State

No geographic analytics exist. The three custom reports (Cost Tier Inventory, Inventory Balance, Reserved Stock by Order) are all inventory-focused. There are no reports aggregating Sales data by customer area, territory, or geography.

The `Territories` doctype exists (referenced in Customer Information's `territory` field), but:
- It is not used in any report
- It has no geographic definition or coordinates
- Its relationship to `PH Barangay` / `PH Province` is undefined

### Data Shape Needed for Heatmap Analytics

For a customer heatmap by order volume or revenue, the required data shape is:
```
[ { lat: float, lng: float, weight: float }, ... ]
```

Assembled from:
```
Sales → customer_link → Customer Information → outlet_address[] → PH Address → (lat, lng)
Sales → grand_total → (weight)
```

This join is **not currently executable** because PH Address has no lat/lng fields yet. Once Phase 1 (lat/lng on PH Address) is complete, the data pipeline is straightforward.

### Maps JS Visualization Library (Heatmap Layer)

The `visualization` library is loaded as a parameter to the Maps JS API URL: `?libraries=visualization`. Since there is no CSP, this loads without issue. A `google.maps.visualization.HeatmapLayer` can render 2,000+ customer address points efficiently in the browser.

### PH Barangay Boundary Data

The `PH Barangay` doctype has **2,000 records** with only three fields: `barangay_name`, `city_municipality` (Link), `province` (Link). **No geometry or boundary polygon data exists.**

The Philippines has approximately **42,045 barangays** nationwide. The 2,000 records loaded represent a partial dataset — likely the service areas relevant to Metro Manila and nearby provinces based on the customer data patterns observed.

**For territory mapping by barangay boundary**, an external GeoJSON source is required. Options:
- **GADM** (gadm.org): Free GeoJSON of Philippine administrative boundaries at barangay level (Level 4). ~80MB GeoJSON file.
- **PSA (Philippine Statistics Authority)**: Official shapefiles, requires conversion to GeoJSON.
- **OpenStreetMap**: Barangay relations available but inconsistent coverage.

**This is a non-trivial data engineering task.** Integrating boundary GeoJSON with the `PH Barangay` doctype would require:
1. Adding a `boundary_geojson` Text field to PH Barangay (or a separate linked doctype)
2. A batch import script to match GeoJSON features to existing PH Barangay records by name
3. Name matching is error-prone (spelling variants: "Brgy. Talipapa" vs "Talipapa" vs "Barangay Talipapa")

For the thesis scope, a **point heatmap** (lat/lng dots with weight) is a much more practical analytics visualization than barangay-boundary choropleth maps.

---

## 6. Build vs. Defer Recommendation

### Sub-Feature Verdict Table

| Feature | Verdict | Rationale |
|---|---|---|
| **API key storage** (ROQSON Settings doctype) | **Build now** | Prerequisite for everything else. Low effort (1 Single DocType). |
| **Lat/lng on PH Address + manual geocoding button** | **Build now** | Phase 1 prerequisite. Needed for all map and analytics features. |
| **`delivery_address_ref` on Sales** | **Build now** | Fixes broken address chain. Required for Trip map and analytics. |
| **Driver Location Log doctype** | **Build now** (schema only) | Schema design + creation is cheap. No GPS data flows until tracking is implemented, but the schema needs to exist before anything else. |
| **`user_account` Custom Field on Driver** | **Build now** | Cheap (Custom Field), required to associate a Driver record with the ERPNext login used on the tablet. |
| **GPS breadcrumb collection** (browser `watchPosition` → API POST → Driver Location Log) | **Build now** (client-side on Trip Ticket) | Works in foreground browser. Screen Wake Lock API can keep screen on while In Transit. Acceptable for 2-5 concurrent drivers. |
| **Realtime push via `frappe.publish_realtime`** | **Build now** | Infrastructure is available, never used. Pairing GPS POST Server Script with `publish_realtime` is trivial. |
| **President's Live Map Page** (custom Frappe Page) | **Build now** | No CSP blocks, full Maps JS API support, `frappe.realtime` available, 12-marker rendering is trivial. |
| **Automatic geofence trigger** (arrived at destination) | **Build now** (client-side) | Client-side distance calculation (`haversine`) comparing live position vs. `delivery_lat/lng` from Trips. Triggers "Time In" API on geofence entry. No server-side polling needed. |
| **Warehouse departure geofence** (driver has left ROQSON) | **Build now** (client-side) | Same client-side pattern. Requires `warehouse_lat/lng` in ROQSON Settings. |
| **Fix `Arrived` state reachability in Trips workflow** | **Build now** | Currently a dead state — no transition leads into it. GPS-triggered `Arrived` detection needs this transition (`In Transit → Arrived`) to exist. |
| **Point heatmap** (customer orders/revenue by location) | **Build later** — after lat/lng geocoding is populated | Data pipeline is straightforward once PH Address has coordinates. But needs real geocoded data first — not worth building on test data. |
| **Territory analytics overlay** | **Build later** | Territories doctype has no geographic definition. Would need external GeoJSON + data matching. Not thesis-critical. |
| **Barangay-boundary choropleth** | **Defer** (out of thesis scope) | External GeoJSON dataset, complex name-matching import, weeks of data engineering. Out of scope. |
| **Directions API / route optimization** | **Defer** | Single-stop trips with 2 vehicles. No multi-stop routing needed until fleet scales significantly. |
| **Native Android app** for background GPS | **Out of scope for ERPNext** | Screen Wake Lock + foreground browser is sufficient for 2–5 drivers and thesis purposes. Native app is a separate project. |
| **Sub-minute server-side geofence polling** | **Not feasible on Frappe Cloud** | Frappe Scheduler minimum interval is ~1 minute. Client-side geofencing is the correct architecture anyway. |
| **Custom background worker / daemon process** | **Not feasible on Frappe Cloud shared** | Requires dedicated instance or separate infrastructure. Not needed if client-side geofencing is used. |

---

## 7. Dependency Map

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1 FOUNDATION                        │
│  (From Google Maps Audit — must be done first)              │
│                                                              │
│  ① ROQSON Settings doctype (API key, warehouse coords)      │
│  ② lat/lng fields on PH Address + geocoding button          │
│  ③ delivery_address_ref on Sales                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ depends on ①②③
         ┌─────────────┴───────────────────────────────┐
         ▼                                             ▼
┌─────────────────────┐                   ┌──────────────────────────┐
│   PHASE 2: MAPS UI  │                   │  PHASE 3: GPS TRACKING   │
│                     │                   │                          │
│  Customer Info map  │                   │  ④ Driver Location Log   │
│  Trip Ticket map    │                   │     doctype (new)        │
│  (delivery pin)     │                   │                          │
│                     │                   │  ⑤ user_account on       │
│  DEPENDS ON: ②③     │                   │     Driver (Custom Field)│
└─────────────────────┘                   │                          │
                                          │  ⑥ Fix Arrived state in  │
                                          │     Trips workflow        │
                                          └──────────┬───────────────┘
                                                     │ depends on ①④⑤⑥
                                         ┌───────────┴───────────────┐
                                         ▼                           ▼
                             ┌───────────────────┐   ┌──────────────────────────┐
                             │  PHASE 3a:        │   │  PHASE 3b:               │
                             │  GPS COLLECTION   │   │  LIVE DASHBOARD          │
                             │                   │   │                          │
                             │  watchPosition    │   │  ⑦ President's Map Page  │
                             │  + Wake Lock      │   │     (custom Frappe Page) │
                             │  on Trip Ticket   │   │                          │
                             │  form             │   │  ⑧ publish_realtime in   │
                             │                   │   │     location POST script │
                             │  Client-side      │   │                          │
                             │  geofencing       │   │  DEPENDS ON: ④⑦⑧         │
                             │  (Arrived trigger)│   └──────────────────────────┘
                             │                   │
                             │  DEPENDS ON: ①④⑤⑥│
                             └───────────────────┘
                                       │
                              (needs real geocoded
                               customer data first)
                                       │
                                       ▼
                             ┌───────────────────┐
                             │  PHASE 4:         │
                             │  ANALYTICS        │
                             │                   │
                             │  Customer         │
                             │  heatmap          │
                             │                   │
                             │  DEPENDS ON: ②③   │
                             │  + populated       │
                             │  lat/lng data      │
                             └───────────────────┘
```

### What Is Fully Independent (can build in parallel with Phase 1)

These items have no dependency on the Google Maps Phase 1 work and can begin immediately:

| Item | Why Independent |
|---|---|
| `Driver Location Log` schema creation | No address data needed; it's a new doctype |
| `user_account` Custom Field on Driver | Simple Custom Field, no dependencies |
| ROQSON Settings doctype | It IS Phase 1, but can be created first |
| Fix Trips workflow (`In Transit → Arrived` transition) | Pure workflow configuration |
| President's Map Page (skeleton/layout) | Can build the page structure before GPS data flows |

### Critical Path to Minimum Viable Live Map

The shortest path to showing 1 driver on the President's map:

1. Create `ROQSON Settings` with warehouse coords + Google Maps key
2. Create `Driver Location Log` doctype (schema from above)
3. Add `user_account` Custom Field to Driver; link test driver to a user account
4. Build GPS POST endpoint (API-type Server Script: accepts lat/lng/trip_ref, creates Driver Location Log row, calls `frappe.publish_realtime`)
5. Add `watchPosition` JavaScript to the Trip Ticket client script (fires when workflow_state = "In Transit", acquires Screen Wake Lock)
6. Build President's Map Page: loads Maps JS API, listens for realtime events, renders marker
7. Test end-to-end with one driver on one trip

This critical path does **not** require PH Address geocoding or the delivery_address_ref fix. Those are needed for the delivery pin (destination marker) on the map, but the driver-tracking marker is independent.

---

## Summary

**What Frappe Cloud can do natively:**
- `frappe.publish_realtime` push (Socket.IO) from Server Scripts to dashboard browsers
- Server-side GPS data storage (Driver Location Log created on API call from browser)
- Custom Page hosting the President's live map
- Client-side geofencing (distance calculation in browser JS)
- Scheduler jobs for analytics aggregation (not for sub-minute polling)

**What requires the Android browser + Screen Wake Lock workaround:**
- Continuous GPS tracking while the driver's tablet screen is locked: **not possible without native app**
- Continuous GPS tracking with screen forced on (Wake Lock API): **possible, practical for 2–5 drivers**

**What is not feasible on Frappe Cloud shared hosting:**
- Sub-minute server-side geofence polling (Frappe Scheduler minimum ~1 minute)
- Long-running background processes or custom daemons
- Native push notifications to Android devices (no service worker configured)

**The MVP is achievable** with only Frappe's existing tools: foreground GPS collection on Trip Ticket, `frappe.publish_realtime` for push updates, and a custom Page for the President's map. The architecture is sound for the thesis scope (2–5 concurrent drivers, ≤12 maximum). The primary caveat is that GPS continuity depends on the driver's tablet screen staying on, which is enforced via Screen Wake Lock and operational discipline (keep the app open during trips).
