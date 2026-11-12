---
name: kalmiprep-cbt-exam-ui
description: >-
  Use this skill whenever designing, modifying, or testing the CBT examination interface,
  practice session views, Casio calculator modal, question palette grid, or KaTeX formula
  rendering in KalmiPrep. Enforces distraction-free focus UX, keyboard shortcuts, equation
  readability, and timer urgency states.
---

# KalmiPrep CBT Examination Interface UX & Patterns

The CBT (Computer-Based Test) exam interface is KalmiPrep's mission-critical product surface. Students simulate actual JAMB UTME, WAEC, and NECO testing under timed pressure. Every millisecond of delay, layout shift, or ambiguous status reduces student confidence.

---

## 1. Ergonomic Invariants

1. **Focus Mode (Zero Header/Footer Distraction)**:
   - When in an active CBT session (`/practice/session/<uuid>/`), hide the global marketing navigation and footer.
   - Use a dedicated, fixed **CBT Exam Top Bar** containing:
     - Exam title & subject badge
     - Current question indicator (e.g. `Question 14 of 40`)
     - Persistent countdown timer (`#examTimer`)
     - Quick Calculator button (`#btnOpenCalculator`)
     - Submit Exam button (`#btnSubmitExam`)
2. **Authoritative Countdown Timer (`#examTimer`)**:
   - Time remaining is calculated from server timestamp `data-server-deadline`.
   - **Urgency Visual States**:
     - **Normal (> 5 mins)**: Neutral slate pill (`bg-slate-100 dark:bg-navy-800 text-slate-700 dark:text-slate-200`)
     - **Warning (< 5 mins)**: Amber alert (`bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-800`)
     - **Critical (< 1 min)**: Pulsing red emergency (`bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border border-rose-500 animate-pulse font-bold`)
3. **Question Palette Grid (4 Mutually Exclusive States)**:
   - **Current Question**: Glowing green ring (`ring-2 ring-brand-500 ring-offset-2 dark:ring-offset-navy-900 font-bold`)
   - **Answered**: Solid green fill (`bg-brand-500 text-white border-transparent`)
   - **Flagged for Review**: Amber pill with flag icon (`bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border-amber-300`)
   - **Unvisited**: Slate outline (`border border-slate-300 dark:border-navy-700 text-slate-600 dark:text-slate-400`)
4. **Keyboard Accessibility**:
   - `A`, `B`, `C`, `D`: Select corresponding option
   - `N` or `Right Arrow`: Next question
   - `P` or `Left Arrow`: Previous question
   - `F`: Toggle flag for review
   - `C`: Toggle calculator modal

---

## 2. KaTeX Mathematical & Chemical Formula Standards

1. **Container Styling**:
   - Formulas must be enclosed in `.katex-wrapper` with `overflow-x-auto overflow-y-hidden max-w-full`.
   - Prevent formula clipping on narrow mobile screens (360px).
   - In dark mode, ensure KaTeX math symbols render in crisp high-contrast off-white (`#f1f5f9`).
2. **Options Presentation**:
   - Each multiple choice option (`A`, `B`, `C`, `D`) must be rendered inside a full-width clickable card (`min-h-[52px]` touch target).
   - Radio buttons must update immediately with zero lag via HTMX background swap.

---

## 3. Scientific Calculator Modal (`#calculatorModal`)

- The calculator is inspired by the **Casio fx-991ES Plus** standard approved by Nigerian examination bodies.
- Features:
  - 2D MathLive input screen for natural textbook display (fractions, roots, exponents).
  - 4-way D-Pad for cursor navigation across numerator/denominator.
  - Floating, draggable or bottom-sheet dockable on mobile.
  - Must preserve calculation history throughout the practice session.

For detailed HTML structure and CSS classes, refer to [CBT Patterns Reference](./references/cbt-patterns.md).

## Anti-AI Exam Room Invariants
- **JAMB 8-Key Physical Affordances**: Options A, B, C, D must have tactile borders and distinct active/pressed styling that mirrors real test center keyboards.
- **Zero In-Exam Distraction**: No decorative banners, promotional pills, animated background orbs, or sparkle icons during active exam sessions.
- **Casio fx-991 Tactile Fidelity**: Calculator keys must depress physically (`active:scale-95 active:shadow-inner`) and maintain display state across question transitions.
- **Microcopy**: Keep countdown and question review text direct (e.g. "Question 14 of 40 • 32m remaining"), never hyperbolic.

