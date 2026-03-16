# Google Maps API Feasibility Audit — ROQSON ERPNext

**Status**: Read-only investigation. No changes made. Date: 2026-03-15

---

## 1. Workflow & Doctype Summary

### The Address Chain

```
Customer Information
  ├── business_address     → Link to PH Address
  ├── residential_address  → Link to PH Address
  └── outlet_address[]     → Child table (Customer Information Outlet Address)
                                └── addresses → Link to PH Address
                                                  ├── address_line1  (Data)
                                                  ├── custom_province       → PH Province
                                                  ├── custom_citymunicipality → PH City Municipality
                                                  ├── custom_barangay       → PH Barangay
                                                  └── custom_zip_code       (Data)

Order Form
  ├── outlet               → Link to Customer Information
  ├── address              → Select (dynamic options: address_line1 display text)
  └── location             → Geolocation  ← EXISTS, completely empty, 0/177 records used

Sales
  ├── customer_link        → Link to Customer Information
  └── address              → Data (plain text, copied from Order Form.address on approval)

Trips (Trip Ticket)
  ├── outlet               → Link to Customer Information
  └── address              → Data (plain text, copied from Sales.address when order is added)
```

### Doctype Inventory

| Doctype | Records | Address/Location Fields | Notes |
|---|---|---|---|
| `PH Address` | 2,000+ | `address_line1`, province, city, barangay, zip | Canonical address record. **No lat/lng.** |
| `Customer Information` | 2,000+ | `business_address` (Link PH Address), `residential_address` (Link PH Address), `outlet_address[]` (child → PH Address) | Primary customer registry |
| `Order Form` | 177 | `address` (Select/text), `location` (Geolocation, **unused**) | 63 client + 41 server scripts |
| `Sales` | 61 | `address` (Data, plain text), `customer_link` (Link CI) | Auto-created from approved Order Form |
| `Trips` | 56 | `address` (Data, plain text), `outlet` (Link CI) | Auto-filled from Sales when orders added |
| `PH Province` | — | `province_name`, `region` | No coordinates |
| `PH City Municipality` | — | `city_municipality_name`, `province` (Link) | No coordinates |
| `PH Barangay` | — | `barangay_name`, `city_municipality` (Link), `province` (Link) | No coordinates |

### How the Address Flows Through the System

1. **Address entry**: User creates a `PH Address` record (street, barangay, city, province, zip). It's linked to a Customer Information record via the `outlet_address` child table.

2. **Order Form**: Client script `Order Form Fetch Addresses` fetches the customer's outlet_address child table, resolves each PH Address's `address_line1`, and populates a dynamic `Select` dropdown. **The selected value saved in `Order Form.address` is the display text of address_line1 only** — not the PH Address document name/ID.

3. **Sales creation**: Server script `Auto Create Sales on Approval` fires on Order Form approval. It copies `doc.address` (that plain text string) directly into `Sales.address`.

4. **Trip Ticket assignment**: Client script `Full Order Script` on Trips auto-populates `Trips.address` from the selected Sales record when the dispatcher picks orders for a trip.

**Critical architectural gap**: After step 2, the link to the PH Address document is lost. `Sales.address` and `Trips.address` store only a plain-text string with no foreign key back to PH Address. This complicates any downstream map/coordinate lookup.

---

## 2. Script Inventory

### Scripts Touching Address or Location

| Script Name | Type | DocType | Status | Key Responsibility |
|---|---|---|---|---|
| `Order Form Fetch Addresses` | Client | Order Form | Enabled | Fetches PH Address docs from customer's `outlet_address` child table. Resolves `address_line1` and builds dynamic Select dropdown. Caches outlet doc in form memory. |
| `Address Select` | Client | Order Form | Enabled | Older/parallel version of address fetch-and-populate. Same functionality as above. (Potential duplicate — both scripts run on Order Form.) |
| `Customer Info: Address Helpers` | Client | Customer Information | Enabled | "Same as…" copy buttons between business/residential/delivery address fields. Adds child rows to `outlet_address` table. |
| `Auto Create Sales on Approval` | Server | Order Form | Active (DocType Event: After Save) | On Order Form approval, creates a Sales record. **Copies `Order Form.address` → `Sales.address` as plain text.** Also copies outlet, customer_name, contact, items, totals. |
| `Full Order Script` | Client | Trips | Enabled | Main Trip Ticket controller. On order row selection (via `order_selected` Link field), auto-fills `Trips.outlet`, `Trips.contact_number`, `Trips.address` from the Sales record. Also renders item previews and status UI. |

### Notable: The Unused `location` Geolocation Field

`Order Form` has a `Geolocation` type field named `location`, located in the **Proof of Visit** section alongside store images and visit timestamp. It was presumably intended to capture DSP GPS coordinates at the time of order placement.

**Current status**: **Never used** — 0 of 177 Order Form records have any value in the `location` field.

The Geolocation field type in Frappe 15 uses the browser's Geolocation API; on form save, the user is prompted for location permission, and their GPS coordinates are stored (if granted). This is appropriate for DSP visit verification, not for customer delivery address location.

### No Existing Map or Geocoding Scripts

A keyword search across all Client and Server Scripts for `"location"`, `"geolocation"`, and `"map"` returned **zero matches**. There are no existing integrations with any mapping service, no geocoding placeholders, and no API key references in scripts.

---

## 3. Data Quality Assessment

### PH Address Records (n = 200 sampled from 2,000+)

| Category | Count | % |
|---|---|---|
| Has some form of street/address content (>4 chars, not single-word junk) | ~185 | ~92% |
| Vague, test data, or too short (single digit, single char, nonsense) | ~15 | ~8% |
| Empty address_line1 | 0 | 0% |

**However, the 92% figure is misleading upon closer inspection:**

**Test and placeholder data is widespread:**
- `"1800 Bygenwerth, Fear the Old Blood"` — Bloodborne reference
- `"11 Yancy Street, NYNY"` — Marvel reference (Spider-Man)
- `"dasdf"`, `"sf"`, `"a"`, `"dasd"`, `"sasdf"` — Random junk
- `"81181 EE ER"` — Gibberish

**Real production data is barangay-level, not street-level:**
The dominant real address in live Sales and Trip Ticket records is `"Brgy. Talipapa, Quezon City"` (appears in ~55 of 61 Sales records). This comes from a single test customer (`CTMR-05130`) used for all development activities. Geocoding this barangay name places a pin somewhere in the middle of Talipapa barangay (~0.5 km² area), not at a specific delivery point. The precision is insufficient for door-to-door routing.

**The composite address is never assembled:**
`PH Address` stores address components separately (street + barangay + city + province + zip). There is no computed field or display_name that concatenates them into a full geocodable string. The geocoding input would need to be assembled as:
```
address_line1 + ", " + custom_barangay + ", " + custom_citymunicipality + ", " + custom_province
```

**Sample real production addresses in Sales (all from test customer CTMR-05130):**
- `"Brgy. Talipapa, Quezon City"` (55+ records)
- `"Brgy. Marulas, Valenzuela City"` (2 records)
- `"337 Boni Serrano Avenue Cor. Katipunan Rd. Quezon City"` (1 record)
- `"36 Unit 1 Sampaguita St. Maligaya Subd."` (1 record)

The variation is minimal, and most records reference the same test location.

### Sales Address Field (all 61 records)

Effectively test data from two test customers (`CTMR-05130` and `CTMR-05131`). The addresses stored are plain text and at barangay or partial-street level, never complete routable addresses.

**Conclusion**: The production address dataset is too thin to assess real-world geocodability. The system is in development with predominantly test data.

---

## 4. Integration Assessment

### Google Maps APIs: Need Analysis

| API | Verdict | Rationale |
|---|---|---|
| **Geocoding API** | ✅ Required | Core capability: convert assembled PH Address (street + barangay + city + province) to lat/lng. Essential for any map display. |
| **Maps JavaScript API** | ✅ Required | Embed interactive maps on Customer Information (customer addresses), Trip Ticket (delivery stop), and optionally Sales (delivery location summary). |
| **Static Maps API** | ⚠️ Optional | Cheaper read-only alternative to JS API for thumbnail maps on Sales list view. Consider if quota/cost is a constraint. |
| **Directions API** | ❌ Not yet warranted | Current Trip Tickets are single-stop (one customer per trip in all sampled data). Multi-stop route optimization would require significant workflow redesign. Revisit if multi-stop trips become standard. |
| **Places Autocomplete API** | ❌ Deferred | Would improve address entry UX, but the current structured entry (province → city → barangay → street) is already in place and functional. Adding autocomplete without rethinking the whole address UX is premature. |
| **Street View Static API** | ❌ Not warranted | Street View coverage in Philippine barangays is patchy. Visual payoff is low relative to API quota cost. Not justified. |

### Where Things Should Live

#### 1. **Coordinate Storage — Add to `PH Address`**

Add two new Float fields to the `PH Address` DocType:
```
latitude       Float (read-only from user form)
longitude      Float (read-only from user form)
geocoded_on    Datetime (read-only, timestamp of last successful geocoding)
```

**Why `PH Address`?**
- `PH Address` is the single source of truth for all location data in the system.
- Every other doctype that needs location (Customer Information, Order Form, Sales, Trip Ticket) traces back to PH Address.
- Centralizing coordinates here means a single geocoding run benefits all downstream views.
- The hierarchical administrative doctypes (`PH Province`, `PH City Municipality`, `PH Barangay`) should **not** store coordinates. Their boundaries are administrative, not meaningful for delivery. The barangay centroid is not the same as a customer's address centroid.

#### 2. **Geocoding Trigger — Manual Button, Not Automatic**

Do not auto-geocode on PH Address save. Reasons:
- **Invalid addresses burn quota**: Test/placeholder addresses would produce wrong pinned coordinates that persist in the database.
- **Data quality is inconsistent**: The current `address_line1` field is too freeform; quality varies. Bad geocodes are worse than no geocodes.
- **Admin control is essential**: A "🌍 Geocode This Address" button on the PH Address form, with a confirmation dialog showing the resolved address and coordinates, gives the admin power to verify before storing.
- **Batch processing for backfill**: A separate admin Server Script (run once by a System Manager) should bulk-geocode all customer addresses with proper error logging and manual review.

Implementation sketch:
```javascript
// Client Script on PH Address
frappe.ui.form.on('PH Address', {
    refresh(frm) {
        frm.add_custom_button(__('Geocode This Address'), () => {
            frappe.call({
                method: 'roqson.geocoding.geocode_address',
                args: { address_name: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frm.set_value('latitude', r.message.latitude);
                        frm.set_value('longitude', r.message.longitude);
                        frm.set_value('geocoded_on', frappe.datetime.now_datetime());
                        frm.refresh();
                        frappe.show_alert({
                            message: __('Address geocoded: {0}, {1}',
                                [r.message.latitude, r.message.longitude]),
                            indicator: 'green'
                        });
                    }
                }
            });
        });
    }
});
```

#### 3. **Map Embed Candidates & Feasibility**

| DocType | Path to Coordinates | Technical Feasibility | Recommended Map UI | Complexity |
|---|---|---|---|---|
| **Customer Information** | Direct: `outlet_address[]` → PH Address → lat/lng | High | Panel showing all delivery address pins for the customer | Low: simple loop over child table rows |
| **Trip Ticket** | Path 1 (clean): `outlet` → Customer Information → outlet_address → PH Address. Path 2 (fragile): Match `Trips.address` text against PH Address records by `address_line1` | Medium–High | Show single delivery stop pin on trip map | Medium: involves text matching or reverse lookup; OR implement Risk Mitigation #1 first (add `delivery_address_ref` to Sales) |
| **Sales** | Path 1: `customer_link` → Customer Information → outlet_address → PH Address. Path 2: Match `Sales.address` text against PH Address.address_line1 | Medium | Read-only pin showing delivery location (lower priority) | Medium: same fragility as Trip Ticket |
| **Order Form** | Direct: `outlet` → Customer Information → outlet_address → PH Address. Plus: revive the unused `location` Geolocation field for DSP visit GPS | High | Interactive map + Geolocation field for visit timestamp capture | Low–Medium: field already exists, just needs enabling |

**Priority ranking:**
1. **Customer Information** — high payoff, clean data model, low complexity
2. **Trip Ticket** — high payoff, but requires fixing the address reference chain first
3. **Order Form** — medium payoff; primarily for DSP visit audit (separate use case from delivery routing)
4. **Sales** — lowest priority; read-only view, could be handled as a dashboard widget later

---

## 5. Risks and Blockers

### Risk 1: Broken Address Reference Chain (High Impact 🔴)

**Problem**: `Sales.address` and `Trips.address` store plain text (e.g., `"Brgy. Talipapa, Quezon City"`), not a Link to the PH Address document. To show a map on a Sales or Trip Ticket record, you cannot simply join to PH Address — you must either:

1. **Option A (Fragile)**: Match the stored text against `PH Address.address_line1` using a like-query.
   - Risk: Breaks if the text differs by even a space or punctuation.
   - Risk: Multiple PH Address records might have the same `address_line1` but different zip codes or details.

2. **Option B (Expensive)**: Trace back through a 5-hop chain:
   ```
   Sales → order_ref → Order Form → outlet → Customer Information
     → outlet_address[...] → PH Address → lat/lng
   ```
   - Risk: Slow on large datasets; expensive database query.
   - Risk: If the Order Form is deleted, the link breaks.

3. **Option C (Correct)**: Add a `delivery_address_ref` Link field to `Sales` (pointing to PH Address) and populate it when `Auto Create Sales on Approval` runs.
   ```
   frappe.get_doc('Order Form', doc.name)
   # Extract which outlet_address was selected
   # Find matching PH Address in Customer Information.outlet_address[]
   sales.delivery_address_ref = matching_ph_address.name
   ```

**Mitigation**: Implement Option C as part of any map integration. Add the field to Sales, update the server script to populate it, and then Trip Ticket maps become trivial (lookup via Sales → delivery_address_ref → lat/lng).

---

### Risk 2: Address Data Quality — Barangay-Level Only (High Impact 🔴)

**Problem**: Real production delivery addresses appear to be stored at barangay level only (`"Brgy. Talipapa, Quezon City"`). Geocoding a barangay name returns the centroid of the barangay polygon, not a specific routable delivery point.

**Accuracy implications**:
- Barangay size: ~0.5–2.0 km² depending on the barangay
- Geocoded pin placement: Dead center of barangay, not the actual customer location
- Routing impact: Cannot use the coordinates for turn-by-turn navigation; the driver still needs the full address text

**Root cause**: The `address_line1` field on PH Address is a free-text Data field with no validation or required subfields (street number, building name, etc.). Users enter whatever they want, and the system accepts it.

**Mitigation options**:
1. Redesign address entry UX to enforce minimum input (street number/name required, not just barangay).
2. Run a data cleanup campaign: audit existing addresses, contact customers, fill in missing street-level details.
3. For now, geocode what exists but clearly label map pins as "approximate location (barangay-level)" in the UI.

This is a data governance problem, not a technical one.

---

### Risk 3: 63-Script Order Form Collision Risk (Medium Impact 🟡)

**Problem**: Order Form has 63 Client Scripts and 41 Server Scripts. It is heavily scripted. Adding any map-related behavior to Order Form carries high risk of conflict with existing scripts, particularly:
- `Order Form Fetch Addresses` (selects delivery address)
- `Address Select` (older parallel version)

Both scripts do essentially the same thing — there is likely dead code here.

**Mitigation**:
1. Before adding map functionality, audit and consolidate the two address-selection scripts. Keep one, disable the other.
2. Run the test suite (if one exists) after any Order Form changes.
3. Add new map functionality in a separate client script rather than merging into an existing bloated script.

---

### Risk 4: No API Key Storage Mechanism (Low Impact 🟡, Easy Fix)

**Problem**: No custom Single doctype exists for ROQSON configuration. The `.env` file (checked into the repo) only has `ROQSON_API_KEY` and `ROQSON_API_SECRET` for the Frappe Cloud REST API.

A Google Maps API key stored in `.env` is accessible to Python scripts running locally, but **not** to Server Scripts executing in RestrictedPython on the Frappe Cloud.

**Mitigation**:
1. Create a new Single DocType called `ROQSON Settings` (or `Google Maps Settings`) with:
   - `google_maps_api_key` (Data, password field to hide it)
   - `google_maps_enabled` (Check box)
   - Restricted to System Manager role only
2. For Client-side use (Maps JS API), the key must have **HTTP referrer restrictions** configured in the Google Cloud Console (restricted to `https://roqson-industrial-sales.s.frappe.cloud`).
3. Server-side geocoding scripts fetch the key from `frappe.get_value('ROQSON Settings', 'ROQSON Settings', 'google_maps_api_key')`.

---

### Risk 5: Geolocation Field Already Exists But Is Unused (Low Impact 🟡, Opportunity)

**Observation**: The `location` (Geolocation) field on Order Form was added but never used. This field captures the DSP's GPS coordinates at time of order placement (via browser Geolocation API), not the customer's delivery address.

**Current state**: 0 of 177 records have data.

**Opportunity**:
- Revive this field for **DSP visit verification** (independent of delivery mapping).
- Add a client script that prompts the DSP to enable geolocation when they submit an order, stamping their GPS as proof of visit.
- Store this separately from address mapping — it's an audit trail, not an address.

**Do not conflate**: Visit location (DSP's GPS at order time) and delivery location (customer's address for fulfillment) are different data. The `location` field is for the former; address mapping is for the latter.

---

### Risk 6: Licensing and ToS Compliance (Low Impact 🟡, Verify Before Launch)

**Constraint**: Google Maps Platform Terms of Service allow caching geocoded coordinates when tied to a specific place associated with your business service (e.g., customer registered addresses). What is prohibited is:
- Building a competing geocoding product
- Reselling geocoded data to third parties
- Caching real-time user location data (e.g., GPS from delivery driver's phone)

Storing lat/lng in `PH Address` for internal delivery operations is within normal TOS bounds.

**Mitigation**:
1. Review the [Google Maps Platform ToS](https://cloud.google.com/maps-platform/terms) before launch.
2. Ensure Google Maps attribution is displayed on any map view per TOS requirements.
3. Do not allow data export of coordinates; restrict to internal use only.

---

## Summary & Recommendations

### Preconditions (Do First)

Before building any map UI, resolve these foundational issues:

1. **Add coordinate fields to `PH Address`**: Add `latitude`, `longitude` (Float) and `geocoded_on` (Datetime) fields. Implement a manual "Geocode This Address" button, not automatic on-save.

2. **Restore the address reference chain**: Add a `delivery_address_ref` Link field to the `Sales` DocType (pointing to PH Address). Update `Auto Create Sales on Approval` server script to populate this field by finding the PH Address that was selected in Order Form.

3. **Create API key storage**: Build a custom Single DocType (`ROQSON Settings`) with a `google_maps_api_key` field, restricted to System Manager.

4. **Consolidate address scripts on Order Form**: Audit and merge or disable duplicate address-selection scripts to reduce collision risk.

### Phased Implementation Roadmap

**Phase 1 (Foundation)**:
- Implement the three preconditions above
- Build the geocoding button and one batch-geocoding script
- Test with a sample of real customer addresses; assess actual geocoding quality

**Phase 2 (Maps UI — Priority 1)**:
- Customer Information form: Add a map panel showing all delivery address pins
- Trip Ticket form: Add map showing the delivery stop pin (now feasible via restored reference chain)

**Phase 3 (Maps UI — Priority 2)**:
- Sales form: Add read-only delivery location pin
- Order Form: Revive the `location` Geolocation field for DSP visit capture (separate use case)

**Phase 4 (Optional, Future)**:
- Directions API integration (only if multi-stop trips are implemented)
- Places Autocomplete (only if address entry UX is redesigned)

### Expected Payoffs

- ✅ **Visibility**: Dispatchers can see all orders on a map, verify correct addresses, identify clustering
- ✅ **Quality check**: Manual geocoding approval catches bad addresses before they persist
- ✅ **Audit trail**: Visit GPS timestamps (via revived `location` field) provide DSP accountability
- ❌ **Routing optimization**: Not achievable with current barangay-level address data; requires address quality improvement first

### Known Limitations

- Delivery accuracy will be barangay-level (~0.5 km radius) unless address data is upgraded to street level
- No turn-by-turn routing without additional data enrichment
- System is currently too immature (mostly test data) to assess production geocodability; real-world results depend on customer address data quality

---

**Report Status**: Complete. Audit performed without making any system changes.
