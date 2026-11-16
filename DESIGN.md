---
name: Gestionale demolizione
description: Prototype parts-management system for a car dismantler, styled as an OEM spare-part carton with its adhesive box-end label.
colors:
  band: "#1240a8"
  band-deep: "#0b2d7a"
  band-tint: "#e3e9f7"
  ink: "#111418"
  ink-2: "#454c55"
  ink-3: "#6b727b"
  ground: "#eef0ee"
  carton: "#f7f8f6"
  label: "#ffffff"
  hair: "#c6cbd0"
  hair-soft: "#dde1e4"
  ok: "#17763a"
  ok-bg: "#dcf1e3"
  warn: "#8a5a00"
  warn-bg: "#ffe9a8"
  danger: "#b3261e"
  danger-bg: "#fbe1de"
  draft: "#5b636c"
typography:
  code-display:
    fontFamily: "Barlow Condensed, Barlow, sans-serif"
    fontSize: "clamp(44px, 12vw, 76px)"
    fontWeight: 700
    lineHeight: 0.9
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\" 1"
  headline:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.25
  body:
    fontFamily: "Barlow, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "\"tnum\" 1"
  code:
    fontFamily: "Barlow Condensed, Barlow, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.01em"
    fontFeature: "\"tnum\" 1"
  label:
    fontFamily: "Barlow Condensed, Barlow, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.025em"
rounded:
  sm: "4px"
  md: "6px"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.band}"
    textColor: "{colors.label}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.band-deep}"
  button-primary-large:
    backgroundColor: "{colors.band}"
    textColor: "{colors.label}"
    rounded: "{rounded.md}"
    padding: "0 24px"
    height: "56px"
  button-secondary:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-quiet:
    textColor: "{colors.band}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-quiet-hover:
    backgroundColor: "{colors.band-tint}"
  button-danger:
    backgroundColor: "{colors.label}"
    textColor: "{colors.danger}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  field:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "48px"
  status-chip-disponibile:
    backgroundColor: "{colors.ok-bg}"
    textColor: "{colors.ok}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "28px"
  status-chip-riservato:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "28px"
  status-chip-venduto:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.label}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "28px"
  status-chip-bozza:
    backgroundColor: "{colors.label}"
    textColor: "{colors.draft}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "28px"
  status-chip-invendibile:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "28px"
  panel:
    backgroundColor: "{colors.label}"
    rounded: "{rounded.md}"
  band-header:
    backgroundColor: "{colors.band}"
    textColor: "{colors.label}"
    typography: "{typography.code-display}"
    padding: "20px 24px"
  nav-sidebar:
    backgroundColor: "{colors.band}"
    textColor: "{colors.label}"
    width: "232px"
  nav-sidebar-item-active:
    backgroundColor: "{colors.label}"
    textColor: "{colors.band}"
    rounded: "{rounded.sm}"
    height: "44px"
  nav-bottom-bar:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink-2}"
    height: "64px"
---

# Design System: Gestionale demolizione

## Overview

**Creative North Star: "The Box-End Label"**

Every recovered part is shown the way it will be printed and stuck on it: an original-equipment spare-part carton, box-white and cool, with one saturated print blue owning the band across the top, and a white adhesive label carrying a huge condensed ID, a QR code, a barcode and a provenance line. The interface is that carton and that label. Screens are cool off-white ground with white label surfaces on it. The blue band marks the shell, the vehicle-in-work header and the primary action. Codes (vehicle IDs, part IDs, plates, OE numbers, locations, prices, counts) are set in condensed tabular numerals and carry the hierarchy.

Density is operational: yard staff work on phones outdoors in sunlight, often with gloves, and counter and warehouse staff work on desktops. Targets are large (48px default, 56px for the primary yard action, 64px bottom-bar cells), contrast is high, the theme is light only, and nothing depends on hover. Colour beyond blue, ink and grey appears only when it means a state.

Rendered packshots of parts sit on white like a parts catalogue. They are procedural Blender renders, and each one ships with a provenance sidecar.

**Key Characteristics:**
- Cool box-white ground, white adhesive-label surfaces, 1px hairline frames.
- One print blue ("blu ricambi") for the shell band, primary actions, the lifecycle line and focus.
- Condensed tabular numerals for every code; the ID is the headline.
- State colours carry meaning only: available green, reserved amber, sold ink, draft dashed grey, unsellable red.
- Large, glove-sized targets and a sticky bottom primary action on mobile.

## Colors

A cool, near-neutral carton palette with a single deep print blue, plus a strict set of semantic state pairs.

### Primary
- **Blu Ricambi** (band): the print blue of the carton. It fills the desktop sidebar, the mobile top bar, the vehicle header band, the label's top strip, primary buttons, the lifecycle progress line, the selection highlight and the 3px focus ring. It is also the browser theme colour.
- **Deep Print Blue** (band-deep): the hover and active state of primary buttons, the background of select controls on the band, and the text colour on info notices.
- **Blue Wash** (band-tint): the selected state of quiet controls, the active pill in the bottom bar, the selected category tile, and the background of info notices and "spedito" (shipped) order chips.

### Neutral
- **Carton Ground** (ground): the page background behind everything.
- **Carton Face** (carton): secondary surfaces such as the demo-notice strip, the missing-photo placeholder and pressed secondary buttons.
- **Label White** (label): every working surface (panels, label sheets, fields, the bottom bar, secondary buttons). It is the adhesive label.
- **Print Ink** (ink): primary text, the QR and barcode modules, and the fill for the sold/delivered state.
- **Ink Second** (ink-2): secondary text and supporting metadata.
- **Ink Third** (ink-3): tertiary text, placeholders, table column headers and inactive lifecycle labels.
- **Hairline** (hair): 1px frames on labels, panels, fields and secondary buttons, plus the inactive lifecycle stop ring.
- **Soft Hairline** (hair-soft): row dividers inside panels, the panel header rule, the unreached lifecycle track and discarded/excess chips.

### Semantic states
- **Disponibile Green** (ok on ok-bg): available, paid, sufficient stock, verified code.
- **Riservato Amber** (warn on warn-bg): reserved, awaiting payment, below threshold, needs re-check.
- **Invendibile Red** (danger on danger-bg): unsellable, payment failed, return, field errors. The "missing" stock level uses solid danger with white text.
- **Bozza Grey** (draft): the draft state, always drawn with a dashed draft-grey border on label white.

### Named Rules
**The One Print Blue Rule.** Blue is the only brand colour. It marks the shell, the primary action, progress and focus. Do not add a second accent.

**The Meaning-Only State Rule.** Green, amber and red appear only as a state pair (strong text on its pale background) bound to a real status. They are never used as decoration.

## Typography

**Display / Code Font:** Barlow Condensed (with Barlow, sans-serif)
**Body Font:** Barlow (with system-ui, sans-serif)

**Character:** A grotesque from the world of road signs and industrial print, used in two widths. The condensed cut is the label printer and the regular cut is the operator's interface. Tabular figures are switched on globally so columns of numbers line up.

### Hierarchy
- **Code Display** (700, 40–76px, line-height 0.88–0.9, condensed): vehicle and part IDs as the headline: the vehicle header band (64px mobile, 76px desktop), the label sheet ID (clamp 44–68px), vehicle cards (40px). Prices on the shop product and checkout pages use the same treatment at 44px.
- **Headline** (Barlow 700, 28px mobile / 34px desktop, tight tracking): page titles. The shop hero goes to 48px.
- **Title** (Barlow 600, 17–18px): part names in lists, vehicle make and model.
- **Body** (Barlow 400, 15px, 1.5): running UI copy. Supporting paragraphs are capped at 70ch.
- **Code** (condensed 600–700, 17–26px): inline codes such as OE numbers, locations, counts in stock, plates and dossier numbers.
- **Label** (condensed 600, 12–13px, uppercase, 0.025–0.14em tracking): table column headers, panel headers (15px), status chips, the label's top strip and the demo-notice strip.

### Named Rules
**The ID-Is-the-Headline Rule.** When a screen is about one vehicle or one part, its internal ID in Code Display is the largest thing on the screen. Descriptive names sit below it.

**The Condensed-Means-Code Rule.** Barlow Condensed is for things that would be printed on a label: codes, numbers, states and column heads. Sentences and button labels stay in Barlow.

## Layout

The mobile layout is a single column with 16px side padding. It has a sticky blue top bar and a fixed white bottom navigation bar with four cells (64px tall, safe-area aware). Content reserves 112px of bottom padding so the sticky primary action never covers anything. The primary action ("Aggiungi pezzo") floats above the bottom bar as a full-width 56px button. From the md breakpoint up, the shell becomes a two-column grid: a fixed 232px blue sidebar plus content with 32px padding. Wide pages are capped at 72rem, and focused flows (yard, forms, checkout) are capped at 36rem, 42rem or 28rem.

The spacing rhythm is on a 4px base. 8px and 12px are the inner gaps, 16px is the panel and list-row padding, and 20–24px separates stacked panels. Lists inside panels are full-bleed rows split by soft hairlines, not separate cards. Vehicle header bands bleed to the screen edges on mobile and become rounded inset blocks on desktop.

## Elevation & Depth

The system is mostly flat and tonal. Panels separate from the ground by white-on-grey contrast and a hairline, not by shadow. The one material shadow belongs to the adhesive label sheet: a hairline lip plus a soft drop, as if the label were lifted slightly off the carton. Floating action bars over scrolled content get a deeper, still-diffuse shadow.

### Shadow Vocabulary
- **Label lift** (`box-shadow: 0 1px 0 rgb(17 20 24 / 0.04), 0 6px 18px -10px rgb(17 20 24 / 0.25)`): label sheets, meaning the part label and the selectable vehicle cards in the yard list. Removed for print.
- **Floating bar** (`box-shadow: 0 8px 24px -12px rgb(17 20 24 / 0.35)`): sticky save bars that float over form content.

### Named Rules
**The Only-Labels-Lift Rule.** Only label sheets and floating action bars cast shadows. Panels, chips and buttons sit flat.

## Shapes

Shapes are softly die-cut rectangles. Labels, panels, fields and buttons use a 6px radius, like the rounded corners of a die-cut sticker. Chips, nav items and small tabs use 4px. Full circles appear only where the object is round: lifecycle stops, the "online" dot and the active bottom-bar pill. Frames are always 1px hairlines. The draft state is the single dashed border in the system. The licence plate is drawn as a recognisable object: a white plate with blue end strips, a thin ink border and a 4px radius.

## Components

### Buttons
Solid, square-shouldered and glove-sized.
- **Shape:** 6px radius. Heights are 48px (default), 56px (large, the yard's primary action) and 36px (small, desktop-only contexts).
- **Primary:** label-white text on Blu Ricambi, semibold Barlow, 20px horizontal padding.
- **Hover / Active:** shifts to Deep Print Blue with a 150ms colour transition. Focus is the global 3px blue outline at a 2px offset. Disabled is hairline grey with ink-third text.
- **Secondary:** ink on label white with a hairline border. On hover the border darkens to ink-third, and on press the fill turns to carton.
- **Quiet:** blue text with no fill; it gets a blue wash on hover or press.
- **Danger:** danger text on label white with a 40% danger border; it gets a danger wash on hover.

### Chips
- **Style:** condensed 13px semibold uppercase, 28px tall, 4px radius, using a strong-text-on-pale-background state pair. Covers part status, order status and stock level.
- **State:** the part states are disponibile (green), riservato (amber), venduto (ink fill, white text), bozza (dashed draft border on white), invendibile (red) and scartato (soft hairline, struck through). Listing state has no chip: it is condensed coloured text, with a blue dot when the part is online.

### Cards / Containers
- **Corner Style:** 6px.
- **Background:** label white on carton ground.
- **Shadow Strategy:** flat. Only label sheets lift (see Elevation & Depth).
- **Border:** 1px hairline. The panel header is separated by a soft hairline rule.
- **Internal Padding:** 16px. Panel headers use 16px by 12px with a condensed uppercase 15px title in ink-second.

### Inputs / Fields
- **Style:** 48px minimum height, label-white fill, 1px hairline, 6px radius, 14px horizontal padding, 16px text, blue caret. Code fields (plate, scan, location) use condensed type at 18–22px.
- **Focus:** the border turns blue and a 3px blue outline appears with no offset.
- **Error / Disabled:** error text in danger at 14px below the field. Hints are ink-third.

### Navigation
- **Desktop sidebar:** a 232px Blu Ricambi column. The company name is set in condensed 26px bold uppercase. Items are 44px tall with an 18px icon and 15px semibold label, white at 90% opacity. The active item inverts to a label-white fill with blue text, and hover adds a 12% white wash. A role switcher sits at the foot on band-deep selects.
- **Mobile:** a sticky blue top bar (company name plus role select) and a fixed white bottom bar showing up to four items. Each item has a 22px icon in a pill and a 12px label. The active item is blue text with a blue-wash pill, and inactive items are ink-second.

### Part Label (signature)
The part record is the printed label. It is a white label sheet with a blue top strip (company name and category in condensed 12px uppercase with 0.12em tracking). Below the strip, the part ID is in Code Display, followed by the description, then a two-column provenance list (source vehicle, dossier, condition). A QR code and the storage location sit on the right, and a CODE128 barcode runs along the foot. The same component renders at 100 × 50 mm for print, with no radius and no shadow.

### Lifecycle Route Line (signature)
A part's lifecycle is shown as a transit line with six stations: catalogued, labelled, in warehouse, online, reserved and sold. A 4px track in soft hairline fills with Blu Ricambi up to the current station (700ms, ease-out-expo). Stations are 26px rings with 4px borders: reached stations are solid blue, the current station is a blue ring with a blue dot, and unreached stations are hairline rings. Off-route states (unsellable, discarded) appear as a danger note beneath the line.

### Vehicle Band Header
A Blu Ricambi block that leads every single-vehicle screen. It holds the vehicle ID in Code Display, then the plate object and make/model, then version, year and dossier in white at 80% opacity.

## Do's and Don'ts

### Do:
- **Do** make the internal ID (V-0001, part IDs) the largest type on any single-record screen, set in Barlow Condensed 700.
- **Do** set every code, count, price, plate and location in the condensed tabular face.
- **Do** keep primary actions at 48px or taller, and the yard's main action at 56px, full width and sticky above the bottom bar on mobile.
- **Do** use the 3px Blu Ricambi focus outline everywhere. Do not replace it with a glow.
- **Do** keep ink-third text on label white or carton surfaces. On the carton ground it falls just under 4.5:1.
- **Do** ship every raster render with a provenance sidecar naming its source script.

### Don't:
- **Don't** introduce a second accent colour or use the state colours decoratively.
- **Don't** fall back to the category default this world refuses: a grey sidebar with generic data cards, each carrying a badge.
- **Don't** add shadows to panels, chips or buttons. Lift belongs to label sheets and floating bars.
- **Don't** use dark mode or low-contrast greys on the yard surfaces. The light, high-contrast carton is a field-use requirement.
- **Don't** rely on hover to reveal actions or state.
- **Don't** set sentences or button labels in the condensed face.
