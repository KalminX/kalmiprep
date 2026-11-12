---
name: kalmiprep-responsive-mobile-nav
description: >-
  Use this skill when optimizing mobile responsiveness, touch ergonomics, navigation bars,
  floating bottom docks, or responsive layouts in KalmiPrep. Ensures 44px+ touch targets,
  safe-area inset padding for iOS/Android, speculative navigation, and seamless table-to-card
  transformations on screens from 360px to 1440px.
---

# KalmiPrep Responsive Mobile Navigation & Ergonomics

Over 70% of Nigerian students access examination preparation on mobile devices (Android smartphones with screens between 360px and 412px width). The mobile experience must feel like a high-performance native application.

---

## 1. Mobile Design Invariants

1. **Touch Targets (Minimum 44×44px)**:
   - All interactive icons, bottom navigation tabs, buttons, and radio pills must have an active clickable bounding box of at least 44×44 CSS pixels (`min-h-[44px] min-w-[44px]`).
2. **Safe Area Inset Padding**:
   - Fixed bottom elements (`#mobileBottomNav`, calculator toolbar) must incorporate `padding-bottom: env(safe-area-inset-bottom, 16px)` to avoid overlapping modern gesture bars on Android and iOS.
3. **Floating Bottom Navigation (`bottom_nav.html`)**:
   - 4-item or 5-item dock:
     - 🏠 **Home** (`/`)
     - 📚 **Curriculum** (`/curriculum/`)
     - ⚡ **Practice** (`/practice/setup/`)
     - 📊 **Progress** (`/progress/dashboard/`)
     - 👤 **Account / Classrooms** (`/accounts/profile/` or `/classrooms/`)
   - Active state has an ambient emerald glow and active indicator dot.
4. **Card-Stack Transformation for Tables**:
   - Wide tabular data (question banks, teacher earnings ledger, student rosters) must NEVER cause horizontal page scrolling on mobile.
   - Use `hidden md:table` for the desktop table and `block md:hidden` for mobile card stacks.

---

## 2. Fast Navigation & Speculative Pre-rendering

- KalmiPrep uses HTML Speculation Rules (`<script type="speculationrules">`) to speculatively pre-render high-probability next pages (Home, Practice, Curriculum, Progress) during idle moments.
- Navigating feels instantaneous without layout shifts (CLS < 0.05).

For markup templates, refer to [Navigation Patterns Reference](./references/navigation-patterns.md).

## Anti-AI Mobile Ergonomics Invariants
- **Solid Bottom Dock**: Keep mobile navigation bars fully opaque (`bg-white dark:bg-navy-950 border-t border-slate-200 dark:border-navy-800`), avoiding translucent blurry glass that washes out icons.
- **Physical Touch Targets**: All interactive icons, bottom dock tabs, and floating actions must span at least 44x44px.
- **Zero Floating Gimmicks**: Prohibit floating animated bubbles or non-functional decorative widgets that obstruct mobile viewports.

