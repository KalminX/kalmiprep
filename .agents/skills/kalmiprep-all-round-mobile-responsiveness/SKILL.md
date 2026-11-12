---
name: kalmiprep-all-round-mobile-responsiveness
description: >-
  Universal standard for end-to-end mobile responsiveness across all viewports (320px to 1440px),
  device orientations, and touch ergonomics for KalmiPrep. Enforces 44px+ touch targets, dynamic
  viewport units (100dvh), safe-area insets (env(safe-area-inset-*)), iOS 16px input zoom prevention,
  horizontal overflow protection (KaTeX math, tables, code blocks, CBT ribbons), bottom-sheet drawers,
  and zero horizontal scroll on mobile devices.
---

# KalmiPrep All-Round Mobile Responsiveness Skill

Over 75% of Nigerian students taking JAMB UTME, WAEC, and NECO exams access KalmiPrep on low-to-mid range mobile smartphones (predominantly Android devices with screen widths between 360px and 412px, alongside compact iOS devices starting at 320px/375px). 

This skill establishes the universal mobile standard across **every component, layout, modal, table, math formula, and form control** in KalmiPrep.

---

## 1. Universal Breakpoint Matrix

| Tier | Viewport Width | Typical Target Hardware in Nigeria | Key Layout Behavior |
| :--- | :--- | :--- | :--- |
| **Ultra-Compact** | `320px – 359px` | iPhone SE (1st gen), small Android Go (Itel, Tecno entry) | Single-column stack, compact tags, hidden non-essential secondary badges |
| **Standard Mobile** | `360px – 390px` | Samsung Galaxy A03/A12/A14, Tecno Spark, iPhone 12/13/14 | Standard 1-col cards, horizontal swipe ribbons for CBT questions |
| **Large Mobile / Phablet**| `412px – 430px` | Google Pixel 7/8, Samsung A54, iPhone Pro Max, Infinix Note | Enhanced typography, 2-column compact metric grids |
| **Tablet Portrait** | `768px – 1023px` | iPad mini/air, Galaxy Tab A | 2-column dashboards, hybrid side drawers |
| **Desktop / Laptop** | `1024px+` | Laptops, school computer labs, CBT exam centers | Full multi-column tables, side-by-side video theater, split panes |

---

## 2. The 7 Core Mobile Invariants

### Invariant 1: Zero Horizontal Window Scroll (`scrollWidth <= innerWidth`)
- **Rule**: The root viewport (`<html>` / `<body>`) must NEVER scroll horizontally under any circumstance.
- **Root causes prohibited**:
  - Fixed-width elements (e.g. `w-[500px]` without `max-w-full`).
  - Unwrapped data tables (`<table>` without an `overflow-x-auto` wrapper).
  - Unbounded KaTeX math formulas or equations.
  - Preformatted code blocks (`<pre>`, `<code>`) without `overflow-x-auto whitespace-pre-wrap`.
  - Negative margins (`-mx-4`) without corresponding outer clipping or padding.

### Invariant 2: Viewport-Fit & Safe-Area Inset Handling
- **Rule**: `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">` must be present on all pages.
- Fixed or sticky elements touching viewport edges must respect hardware cutouts (iPhone Dynamic Island, home gesture indicator bar, Android navigation pill):
  - Bottom docks: `padding-bottom: env(safe-area-inset-bottom, 16px)`.
  - Sticky top headers: `padding-top: env(safe-area-inset-top, 0px)`.
  - Side drawers: `padding-left: env(safe-area-inset-left, 0px)` and `padding-right: env(safe-area-inset-right, 0px)`.

### Invariant 3: iOS 16px Zoom-Prevention Invariant
- **Rule**: On mobile viewports (`max-width: 640px`), every text input (`input[type="text"]`, `input[type="email"]`, `input[type="password"]`, `input[type="number"]`, `select`, `textarea`) MUST have a computed font-size of **at least 16px**.
- **Reason**: Mobile Safari automatically zooms in the entire web page whenever an input with `font-size < 16px` receives focus. This destroys responsive positioning, cuts off submit buttons, and confuses students during timed CBT exams.
- **Implementation**: Enforced globally in `static/css/input.css` via:
  ```css
  @media (max-width: 640px) {
    input:not([type="checkbox"]):not([type="radio"]),
    select,
    textarea {
      font-size: 16px !important;
    }
  }
  ```

### Invariant 4: Minimum 44×44px Touch Targets & 8px Separation
- **Rule**: Every button, navigation tab, option radio pill, checkbox container, and action icon must have an interactive bounding box of at least **44×44 CSS pixels** (`min-h-[44px] min-w-[44px]`).
- Adjacent interactive controls must maintain at least **8px gap** to prevent accidental "fat-finger" mis-taps on small touchscreens.
- High-frequency actions during exams (Next, Previous, Option Select) must be placed in the **Thumb Zone** (the bottom 40% of the screen).

### Invariant 5: KaTeX Math & Chemical Formula Protection
- **Rule**: Long mathematical derivations, chemical equations, and matrices must NEVER push the page width outwards.
- Display equations must be wrapped with `.katex-scroll-wrapper`:
  ```html
  <div class="katex-scroll-wrapper overflow-x-auto overflow-y-hidden max-w-full -webkit-overflow-scrolling-touch touch-pan-x py-1">
    {{ question.question_text|safe }}
  </div>
  ```
- Long inline math must support soft hyphenation or horizontal scrolling if exceeding line length.

### Invariant 6: Tabular Data to Mobile Card-Stacks
- **Rule**: Wide tabular data (leaderboards, wallet ledger, classroom rosters, student lists) must NOT force students to pinch-zoom or pan back and forth.
- Tables must either:
  1. Transform into vertical **Card Stacks** on mobile (`block md:hidden` cards + `hidden md:table` desktop table), OR
  2. Be wrapped inside an `.overflow-x-auto` container with primary identification columns (e.g., student name or rank) styled with visual affordance.

### Invariant 7: Modals & Drawers Transform to Bottom Sheets
- **Rule**: Full-page centered desktop dialogs (e.g. CBT Exam Submit Modal, Question Review Drawer, Scientific Calculator) must render as **Bottom Sheets** on mobile screens:
  - Pinned to bottom: `fixed inset-x-0 bottom-0`.
  - Rounded top corners: `rounded-t-3xl sm:rounded-2xl`.
  - Max height: `max-h-[85dvh]` with `overflow-y-auto`.
  - Bottom clearance: `pb-safe`.

---

## 3. Dynamic Viewport Units (`100dvh`)

Mobile browsers dynamically hide and reveal their URL address bar during scrolling.
- Using `100vh` causes content jumping and cuts off bottom buttons behind mobile browser chrome.
- KalmiPrep components use `100dvh` (`min-h-[100dvh]` / `.min-h-screen-dvh`) for full-height views (e.g. CBT Exam layout, auth pages, waiting lobby).

---

## 4. Mobile Keyboard & Form Ergonomics

For numeric PIN entries, telephone numbers, and currency inputs, specify appropriate mobile keyboard modes:
```html
<!-- Test Access PIN: 10-char uppercase alphanumeric -->
<input type="text" 
       name="pin" 
       maxlength="10" 
       autocapitalize="characters" 
       autocomplete="one-time-code" 
       class="font-mono text-center text-lg sm:text-xl font-bold tracking-widest ...">

<!-- Phone Number Input -->
<input type="tel" 
       name="phone" 
       inputmode="tel" 
       autocomplete="tel" 
       enterkeyhint="next">

<!-- Currency / Number Input -->
<input type="number" 
       name="price_naira" 
       inputmode="decimal" 
       enterkeyhint="done">
```

---

## 5. Automated Verification Checklist

Before committing any UI changes:
1. Run the static mobile auditor:
   ```bash
   node .agents/skills/kalmiprep-all-round-mobile-responsiveness/scripts/audit_mobile_responsiveness.js
   ```
2. Run Playwright multi-viewport tests across 320px, 375px, and 412px:
   ```bash
   npm run test:e2e:docker
   ```
3. Verify zero horizontal scroll (`document.documentElement.scrollWidth === window.innerWidth`).
4. Verify input font-size >= 16px on viewport width <= 640px.
