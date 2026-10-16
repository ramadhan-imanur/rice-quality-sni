# DESIGN.md — High-Trust Modern Agritech & Sovereign Grain Standard
## Sistem Taksasi Mutu Beras Digital SNI 6128:2020 & Anti-Fraud Engine

---

## 1. Visual Atmosphere & Philosophy
- **Identity:** Sovereign Agricultural Quality Grading & Post-Harvest Metrology Laboratory.
- **Atmosphere:** High-Trust Modern Agritech — bridges the precision of an accredited ISO/IEC 17025 testing laboratory with the warm, grounded reality of Indonesian paddy fields (*sawah*) and rural milling units (*RMU/Koperasi*).
- **Core Intent:** Eliminates unilateral price depression by middlemen (*tengkulak*) through objective, cryptographic, and Computer Vision-assisted grading.
- **Design Directives:**
  - **No AI-Slop:** Zero generic purple/cyan neon gradients, zero dark SaaS clones, zero low-contrast gray cards, and zero meaningless emoji decorations.
  - **Field-Ready Contrast:** Exceeds WCAG 2.1 AA (targeting AAA 7:1 contrast) for high readability under direct equatorial sunlight.
  - **Data Precision:** Tabular numbers with monospaced clarity for physical metrics (moisture %, broken grain %, impurities) and valuation figures (`Rp/kg`).

---

## 2. Calibrated Color Palette

| Token Name | Hex Code | Functional Role |
| :--- | :--- | :--- |
| `--color-forest-deep` | `#0B3B2C` | Brand anchor, header background, institutional authority. |
| `--color-forest-surface` | `#114B39` | Header secondary, interactive hover states. |
| `--color-emerald-accent` | `#059669` | Primary action buttons, success states, camera focus indicator. |
| `--color-gold-grain` | `#D97706` | Harvest gold, pricing badges, lot valuation highlight. |
| `--color-gold-warm` | `#F59E0B` | Visual warning indicators, Medium II classification. |
| `--color-husk-canvas` | `#F8FAF6` | Canvas background — clean warm rice husk tone (no blinding #FFFFFF). |
| `--color-husk-surface` | `#FFFFFF` | Card surface container with rich crisp elevation. |
| `--color-husk-muted` | `#EDF2EB` | Subtle dividers, inactive tab pills, gauge track backgrounds. |
| `--color-soil-slate` | `#14221B` | Primary text — rich organic slate with ultra-high contrast (14.2:1). |
| `--color-soil-sub` | `#3A4D43` | Secondary text, parameter descriptions, field hints (7.1:1). |
| `--color-border-subtle` | `#D1DCD3` | Structural borders, card outlines, tabular cell borders. |
| `--color-border-strong` | `#8EA898` | Active input borders, focus ring indicators. |

### SNI 6128:2020 Quality Classification Spectrum:
- **PREMIUM:** Emerald `#065F46` on `#DCFCE7` (Highest market grade, full base price).
- **MEDIUM I:** Deep Sapphire `#1E40AF` on `#DBEAFE` (Standard commercial grade).
- **MEDIUM II:** Warm Amber `#92400E` on `#FEF3C7` (Secondary market grade).
- **SUBSTANDAR:** Terracotta `#991B1B` on `#FEE2E2` (Excess moisture/damage penalty).

---

## 3. Typographic Architecture

- **Primary UI & Navigation:**
  - Font Stack: `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
  - Characteristics: Open apertures, humanist geometric proportions, excellent rendering at 14px–16px.
- **Tabular Data, Cryptography, & Currency:**
  - Font Stack: `'JetBrains Mono', 'Space Grotesk', ui-monospace, SFMono-Regular, monospace`
  - Characteristics: Fixed-width digits preventing layout jitter during real-time calculation, distinct `0` vs `O`, clear decimal separators.

### Type Scale:
- `Display / Hero Title`: 1.75rem (28px) / line-height 1.25 / weight 800
- `Section Heading / Modal Title`: 1.25rem (20px) / line-height 1.35 / weight 700
- `Card Heading / Sub-title`: 1.05rem (16.8px) / line-height 1.4 / weight 600
- `Body Text`: 0.9375rem (15px) / line-height 1.55 / weight 400
- `Small / Field Hints`: 0.8125rem (13px) / line-height 1.45 / weight 500
- `Metric Value / Currency Anchor`: 1.625rem (26px) / tabular / weight 800

---

## 4. Component Stylings & Micro-Interactions

### A. Navigation Tabs (Segmented Agricultural Controls)
- Segmented container with `#EDF2EB` background and `#D1DCD3` subtle perimeter.
- Active pill transitions with smooth CSS transform (`transform 0.15s cubic-bezier(0.16, 1, 0.3, 1)`).
- Clear SVG icons for each user persona (*Farmer Maker*, *Lab Checker*, *Audit Archive*).

### B. Computer Vision Viewfinder (`#cv-card`)
- Camera container styled like an industrial optical sorting station:
  - Charcoal border with golden reticle corners.
  - Real-time legend badges for Grain Head (green), Broken (amber), Menir (red), and Foreign Matter (purple).
  - High-visibility action triggers for outdoor smartphone cameras.

### C. Financial & Taksasi Anchor Box (`.pricing-box`)
- Direct visual anchor on the bottom-right of the dashboard:
  - Heavy tabular price display (`Rp 15.800 / kg`).
  - Itemized deductions breakdown (drying cost deduction and moisture shrinkage penalty).
  - Truckload scale projection (`5.000 kg / 1 Truk`) to immediately ground value for farmer discussions.

### D. Focus & Accessibility
- Mandatory `:focus-visible` styling: `outline: 2px solid #059669; outline-offset: 2px;`.
- Touch target minimums: 44px × 44px for thumb tap ergonomics.

---

## 5. Layout Grid & Responsive Architecture

- **Desktop (>= 1024px):**
  - Asymmetric 2-column layout (5:7 ratio).
  - Left column: Input controls & calibration presets.
  - Right column: Real-time grade diagnosis & Bapanas pricing table.
- **Mobile (< 768px):**
  - Single column linear flow.
  - Fixed sticky navigation tab bar with smooth horizontal overflow scroll.
  - Sticky bottom preview for calculated taksasi price.

---

## 6. Official Certificate & Verification Styling (`web/verify.html`)
- Structured like a sovereign national registry portal (Bulog / Badan Pangan Nasional / Koperasi Induk):
  - Holographic verification badge with green security ring.
  - Redacted PII display for UU PDP No. 27/2022 compliance (`331101********01`).
  - Cryptographic HMAC-SHA256 fingerprint box with copy button.
  - Print stylesheet (`@media print`) rendering a formal single-page A4 Certificate of Analysis (CoA).
