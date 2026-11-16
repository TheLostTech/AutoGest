---
version: 1
slug: "src-app"
primary_target: "src/app"
related_targets: []
---

# Surface brief: gestionale prototipo (app shell, campo, magazzino, vendite, vetrina)

Scope: whole Phase 1 prototype web app. Mode: Operate (shop pages: Operate with commerce clarity).
Audience/task: dismantlers on phones outdoors; intake, warehouse, manager, counter on desktop; online buyer on shop. Flow vehicle → suggested parts vs stock → photo → part record → QR label → location → publish gate → reserve/sell.
Constraints: Italian copy; synthetic demo data labelled as demo; brand name placeholder in one constant; gloves + sunlight = large targets, light theme, high contrast.
Unresolved: real brand, label printer format, real OCR/VIN providers.

## Direction contract

THESIS: The part record is the box-end label. Every unit is shown the way it will be printed and stuck on the part: huge condensed ID, QR, provenance line. Refuses the category default of grey sidebar + generic data cards with a badge.

OWN-WORLD: OEM spare-part carton. Box-white ground (#EEF0EE, cool), one saturated print blue "blu ricambi" (#1240A8) owning the shell band and primary actions, ink #111418, white adhesive labels with 1px hairline frame and 6px corners, Barlow Condensed tabular numerals for every code, Barlow for UI. State colours only for meaning: disponibile green, riservato amber, venduto ink, bozza dashed grey, invendibile red. Blender packshot renders of parts on white like a catalogue.

STORY: Staff see a vehicle once, then every part inherits it; they trust stock numbers because each unit is a labelled object with a traceable route. Client validates the flow end to end.

FIRST VIEWPORT: Mobile: blue band header with vehicle-in-work ID huge (V-0001 style) + plate, below a ranked "da recuperare" list (missing / under threshold / sufficient vs stock), sticky bottom primary "Aggiungi pezzo" (camera). Desktop: blue band top bar + left nav, dashboard of vehicles in work and parts by state.

FORM: Scatola ricambio originale (OEM carton + adhesive label), position 4 of 7 on grounded list; raises: ID-as-headline (from catalog numbering), lifecycle as route line with stations (from transit diagram), numeral scale carries hierarchy (from type specimen). seed:b06bb953cfdbf7ff

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
