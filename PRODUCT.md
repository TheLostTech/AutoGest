# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js (App Router) + TypeScript, chosen by the user. Prototype phase: demo data persisted in the browser (no backend yet), structured so a real database/API can replace the store in Phase 2. GitHub repository requested by the user (remote to be provided).

## Users

- **Smontatore** (dismantler): on the yard, outdoors, smartphone in hand, often dirty gloves, variable light and network. Job: open the vehicle in work, see which parts are worth recovering, photograph and catalogue each part in seconds without retyping plate or dossier.
- **Accettazione** (intake desk): registers incoming vehicles from a plate photo (OCR with manual check), VIN, dossier reference.
- **Magazziniere**: scans labels, assigns and moves locations (area/aisle/shelf/level/bin), inventories, flags anomalies.
- **Responsabile**: sets stock rules, approves part records, prices, publishes to the shop, reads statistics.
- **Vendite / banco**: searches parts, reserves, sells at the counter, handles orders, shipments, returns.
- **Acquirente online**: searches by vehicle or part, sees condition and availability, checks out.

## Product Purpose

An integrated platform for an Italian autodemolizione: one authoritative source for vehicles, parts, locations, movements, orders and sales. Identify the vehicle once; every part inherits its provenance; catalogue fast on the yard; label, locate, publish and sell without manual reconciliation. This build is the **Phase 1 validation prototype**, shown to the client on site to validate the flow vehicle → suggested parts → photo → part record → QR.

## Positioning

The vehicle is the mother record: provenance is inherited, never retyped, and every physical part is an individually tracked unit traceable to its vehicle and demolition dossier. Before dismantling, the system compares recoverable parts against real stock and thresholds, so the yard recovers what is missing instead of what is easy.

## Operating Context

Flow: vehicle intake → preliminary recovery analysis vs stock → dismantling and cataloguing on device → label print and storage → shop publication (only when commercially complete) → sale (counter, shop, marketplace) with atomic reservation, cancellations, returns. Part states: disponibile → riservato → venduto, plus bozza, invendibile, scartato, reso. Physical labels with QR/barcode carry only the unique part ID.

## Capabilities and Constraints

- Internal IDs are never confused with the official dossier/certificate number.
- No duplicate codes; label reprint keeps the ID and is audit-logged.
- A part cannot be published without price, photos and minimum validated data.
- The same part can never be sold twice.
- AI/OCR suggestions always require operator confirmation; nothing is declared certain without verification.
- No destructive deletion; history preserved.
- Undecided (prototype simulates): plate OCR provider, VIN/vehicle database, OEM catalogues, label printers, payment provider, couriers, marketplaces, fiscal documents.

## Brand Commitments

Client company name not yet provided: the prototype uses a placeholder name defined in a single config constant, to be replaced. Language: Italian.

## Evidence on Hand

Functional spec v0.1 (16 Nov 2026, draft to validate). Initial stock indicatively 3,000+ parts, not yet inventoried. No real vehicles, parts, prices, photos or customers exist: all prototype data is synthetic and must be labelled as demo.

## Product Principles

1. Identify once, inherit everywhere.
2. Fewer keystrokes on the yard: big targets, photos first, defaults from the vehicle.
3. Suggestions assist, people confirm.
4. Every state change is traceable.
5. Never sell or publish what is not certain.

## Accessibility & Inclusion

Field use outdoors: high contrast in sunlight, large touch targets usable with gloves, no reliance on hover.
