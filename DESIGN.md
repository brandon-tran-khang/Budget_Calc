---
name: Budget Calc
description: Cash Envelopes, a personal spending ledger where every category is an envelope and returned money slips back in.
colors:
  ledger-green: "#1F6B4F"
  ledger-green-night: "#2E7D5B"
  slip-green: "#3E9A74"
  rail-green: "#1F4D3A"
  rail-green-deep: "#17402F"
  rail-mint: "#5BAE8C"
  rail-ink: "#E4EFE8"
  rail-line: "#3B6A55"
  rail-night: "#0F2A20"
  rail-night-deep: "#0A1F17"
  rail-night-ink: "#D5E6DC"
  rail-night-line: "#2A4A3A"
  envelope-gold: "#D9A21B"
  cool-paper: "#F4F6F2"
  sheet-white: "#FFFFFF"
  ink: "#17201B"
  paper-line: "#DDE3DB"
  night-ground: "#101714"
  night-sheet: "#18221D"
  night-ink: "#E6EDE8"
  night-line: "#2A3830"
  debit-red: "#B3261E"
  debit-red-night: "#F2867E"
  credit-green: "#2E7D5B"
  credit-green-night: "#6CC49C"
  stock-blue: "#4F8FC0"
  stock-coral: "#E0674F"
  stock-violet: "#8C7BC4"
  stock-rose: "#D46A8C"
  stock-slate: "#46525C"
  stock-fallback: "#7A8580"
typography:
  display:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "clamp(56px, 8vw, 96px)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "26px"
    fontWeight: 600
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  title:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 600
  title-sm:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 600
  body:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.7
    fontFeature: "tnum"
  body-strong:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    fontFeature: "tnum"
  caption:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.08em"
  brand:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 800
    letterSpacing: "-0.01em"
rounded:
  flap: "2px"
  track: "3px"
  base: "6px"
  panel: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  hero-gap: "40px"
components:
  rail-nav-item:
    textColor: "{colors.rail-ink}"
    rounded: "{rounded.base}"
    padding: "2px 10px"
  rail-nav-item-active:
    backgroundColor: "{colors.cool-paper}"
    textColor: "{colors.rail-green}"
    rounded: "{rounded.base}"
    padding: "2px 10px"
  button-primary:
    backgroundColor: "{colors.ledger-green}"
    textColor: "{colors.sheet-white}"
    rounded: "{rounded.base}"
  hero-figure:
    textColor: "{colors.ink}"
    typography: "{typography.display}"
  metric-value:
    typography: "{typography.headline}"
  section-title:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
  envelope-chip:
    rounded: "{rounded.flap}"
    width: "26px"
    height: "18px"
  envelope-track:
    rounded: "{rounded.track}"
    height: "14px"
  receipts-panel:
    rounded: "{rounded.panel}"
    padding: "14px 18px"
---

# Design System: Budget Calc

## Overview

**Creative North Star: "Cash Envelopes"**

Every budget category is an envelope. Spending leaves it; refunds and reimbursements slip back in; out-of-pocket is what is really gone. The system is a bank-envelope green rail beside a cool paper ledger: navigation and filters live on the rail, and the main sheet reads like a statement, one monumental out-of-pocket figure first, then the envelopes it left from, then the receipts behind any edit.

Density is ledger-like, not dashboard-like. Hierarchy comes from scale and weight alone; metrics sit bare on the paper with no cards, rows are separated by single hairlines, and the only boxed surface is the session receipts panel. Color belongs to the categories: each envelope has one stock color that appears identically on its chip, its bar and its chart series, so the palette's loudest notes are data, never chrome. The build refuses the category default of white KPI cards, a donut and an indigo accent.

The world works in both Streamlit themes. The main sheet's custom tokens derive from the inherited text color, so they follow a light/dark toggle without a rerun; the rail stays green in both themes, deepening to a green-black at night.

**Key Characteristics:**
- Green rail carrying grouped navigation (Review, Money flow, Clean up) and filters.
- Cool paper ground, green-black ink; deep green-black ground in dark mode.
- One envelope-stock color per category, shared by chips, bars, tables and charts.
- Public Sans, self-hosted, with tabular figures on everything.
- Envelope-flap chips and the hatched slip for returned money.
- Flat paper: hairlines and a faint tint, no shadows.

## Colors

A restrained green ledger whose only saturated color comes from the category envelope stocks.

### Primary
- **Ledger Green** (light primary): primary buttons, the trend line and sparkline, the vendor bar series, focus rings and selection tint (through the mixed primary token). In dark mode the theme primary steps to **Ledger Green Night**.
- **Slip Green**: the base hue of the sheet's primary and "returned" tokens, mixed 75% with the current text color so it stays legible on either ground. Used for "returned $…" lines under envelope rows.

### Secondary
- **Rail Green** and **Rail Green Deep**: the navigation rail ground and its secondary surfaces (filter fields) in light mode. **Rail Night** and **Rail Night Deep** replace them in dark mode. Rail text is **Rail Ink** / **Rail Night Ink**; rail dividers are **Rail Line** / **Rail Night Line**; selected widgets on the rail use **Rail Mint**.
- **Envelope Gold**: the brand mark (a small gold envelope block before "Budget Calc") and the Groceries / Variable stock.

### Tertiary: envelope stocks
- The chart categorical sequence is Ledger Green, Envelope Gold, **Stock Blue**, **Stock Coral**, **Stock Violet**, Rail Mint, **Stock Rose**, **Stock Fallback**. Per-category stocks live in `config.py` as families: golds and corals for food, blues for car, greens for home and utilities, slates for subscriptions and fees, rose for health, violets for games and travel, a tan for Personal, deep teal for Investments. **Stock Slate** also marks "Fixed" and credit-card spend; **Stock Fallback** is any unmapped category.

### Neutral
- **Cool Paper**: the light ground, and the active rail pill in both themes. Not cream.
- **Sheet White**: Streamlit's secondary background in light mode (inputs, dataframes).
- **Ink**: body text in light mode. **Night Ink** in dark mode.
- **Paper Line** / **Night Line**: widget and table borders.
- **Night Ground** / **Night Sheet**: dark-mode ground and secondary background.
- Sheet-level derived tones (not fixed hexes): muted text is the text color at 66%, hairlines at 14%, bar tracks at 8%, the panel tint at 3%.

### Semantic
- **Credit Green** / **Credit Green Night**: income and positive deltas. **Debit Red** / **Debit Red Night**: expenses and negative deltas.

### Named Rules
**The Envelope Stock Rule.** A category has exactly one color, taken from `CATEGORY_COLORS`, and it is used identically on its chip, its bar, its table cell and its chart series. A new category gets a stock from its family; an unmapped one gets Stock Fallback. Never recolor a category per chart.

**The Data-Owns-Color Rule.** Chrome is green, paper and ink. Saturated hues are reserved for category stocks and the debit/credit semantics; no decorative accent sits outside those roles.

**The Derived Token Rule.** Sheet tokens are mixes of `currentColor` so they follow the client-side theme toggle. Never hard-code a light-only hex into sheet CSS.

## Typography

**Display Font:** Public Sans (with sans-serif), self-hosted at 400, 600 and 800.
**Body Font:** Public Sans.

**Character:** One civic sans in three weights. Hierarchy is made by size and weight alone, and every figure is tabular so columns of money line up.

### Hierarchy
- **Display** (800, clamp 56–96px, line-height 1, -0.03em): the single out-of-pocket figure at the top of Overview, with its label and period inline in 15px/600 muted text.
- **Headline** (600, 26px, -0.01em): metric values, which sit bare on the paper under a 13px/600 muted label.
- **Title** (600, 18px): section headers, with an optional 13px muted caption beneath.
- **Title Small** (600, 15px): the receipts panel heading.
- **Body / Body Strong** (400 or 600, 14px): envelope names and amounts, receipt lines, the gross · refunds · reimbursed breakdown (line-height 1.7).
- **Caption** (400, 13px, muted): section captions, the filter context line, receipt timestamps.
- **Label** (600, 11px, 0.08em, uppercase, 70% opacity): rail group headers and the rail's Filters label only.
- **Brand** (800, 18px): the rail wordmark.

### Named Rules
**The Scale-Alone Rule.** Rank by size and weight, never by color or boxes. One display figure per page; everything else steps down through 26, 18, 14 and 13px.

**The Tabular Figures Rule.** `font-variant-numeric: tabular-nums` is set on the whole app. Money is formatted with a true minus (−) and two decimals.

## Layout

The app is a fixed left rail plus a main sheet. The rail holds the wordmark, grouped navigation (Review: Overview, Vendors, Year Comparison, Forecast; Money flow: Cash Flow, Recurring; Clean up: Transactions, Reimbursements, Categories), a divider, then filters. The sheet opens 4.5rem from the top.

Overview's first viewport is a hero row (figure, breakdown, a right-aligned six-month sparkline, flex-wrapped with an 8px by 40px gap), then the Envelopes list in a wide column beside the receipts panel and metrics in a narrow one. Other pages are stacks of section header plus chart or table.

Envelope rows are a three-column grid: name (130–190px), bar (fluid), amount (96px, right-aligned), with 16px column gap and 12px row padding. The list is a size container: below 440px of its own width the bar drops under the name and amount. Below 640px viewport the hero's label wraps under the figure.

Spacing steps are 4, 8, 12 and 16px, with 40px reserved for the hero gap.

## Elevation & Depth

Flat paper. There are no shadows anywhere. Depth comes from 1px hairlines (text color at 14%) between rows, a 3% tint plus hairline on the one boxed panel, and the rail's solid green against the paper. Charts have transparent paper and plot backgrounds with faint gridlines.

### Named Rules
**The Flat Paper Rule.** Surfaces are flat. Separate with a hairline or a 3% tint; never with a drop shadow or a card stack.

## Shapes

Small, papery corners. The theme base radius (6px) governs widgets, buttons and rail pills; the receipts panel uses 8px; bar tracks 3px; envelope chips 2px. The signature silhouette is the envelope chip: a 26 by 18px block of the category stock with a darker triangular flap (a borderless triangle at 18% black) across its top. The brand mark is a 14 by 10px gold block in the same family.

## Components

### Envelope Row (signature)
- **Character:** a ledger line, one per category, sorted by net spend.
- **Structure:** chip and name, a 14px bar track, the net amount right-aligned. A hairline above each row.
- **Bar:** the solid segment is net spend in the category stock; the following hatched slip (135°, 2px stroke every 6px, 70% opacity, same stock) is money that came back. Widths are shares of the largest envelope's spend.
- **Returned line:** "returned $…" in 12px Slip Green under the bar, only when something came back.
- **Reserved:** a 2px ink limit marker is wired for future per-category budgets; there is no budget data yet.
- **Motion:** bars draw in once, scaling from the left over 420ms on `cubic-bezier(.16,1,.3,1)`, staggered 30ms per row up to the eighth.

### Hero Figure
- One display-size out-of-pocket amount with "out of pocket · period" inline, the breakdown line below in muted 14px with bold values, and an SVG sparkline in the primary token.

### Metrics
- Streamlit metrics with no card, border or padding: 13px/600 muted label over a 26px headline value. Deltas use the credit/debit semantics.

### Buttons
- **Shape:** base radius (6px).
- **Primary:** Ledger Green fill (Ledger Green Night in dark mode), used only for the save or confirm action of a cleanup form, always with a Material icon.
- **Secondary:** Streamlit default outline buttons for downloads and popovers, also with Material icons.
- **Focus:** a 2px primary-token outline offset 2px on every focusable element; colors transition over 150ms.

### Navigation (Rail)
- Items are 6px-rounded rows with Material icons. Hover is an 8% white wash. The active item is a Cool Paper pill with Rail Green text at 600, in both themes. Group headers use the Label style.

### Receipts Panel
- "Changes this session": a 3% tinted, hairlined, 8px-rounded panel listing the last five edits, each a bold line with a muted timestamp and detail. Empty state explains what will appear.

### Section Header
- An 18px/600 title with an optional 13px muted caption; Streamlit's anchor link is hidden.

### Inputs and Tables
- Native Streamlit selectboxes, multiselects, data editors and dataframes, themed only through the config: Sheet White or Night Sheet fields, Paper Line or Night Line borders, 6px radius. On the rail they take Rail Green Deep fields.

## Do's and Don'ts

### Do:
- **Do** color every category from `CATEGORY_COLORS`, the same way in chips, bars, tables and charts (The Envelope Stock Rule).
- **Do** draw returned money as the hatched slip in the category's own stock, never as a separate hue.
- **Do** call `receipt()` after every saved edit so it toasts and lands in the session receipts panel.
- **Do** keep metrics bare: no border, no card, hierarchy by size.
- **Do** build sheet colors from the `--bc-*` tokens so light and dark both work.
- **Do** honor reduced motion: every animation and transition is removed under `prefers-reduced-motion: reduce`.
- **Do** pair color with a text label (category name, legend) so categories never separate by hue alone.

### Don't:
- **Don't** wrap metrics in white KPI cards, reach for a donut chart, or introduce an indigo accent; the thesis refuses all three.
- **Don't** add drop shadows; depth is hairlines and tint (The Flat Paper Rule).
- **Don't** add a second display-size figure to a page.
- **Don't** hard-code light-only hexes into sheet CSS; derive from `currentColor`.
- **Don't** load another typeface or a fourth weight; Public Sans 400/600/800 is the whole kit.
