---
name: kalmiprep-design-system
description: >-
  Use this skill whenever creating, styling, or updating UI components across KalmiPrep.
  Covers the brand color palette (brand green, navy slate, subject accents), typography
  standards (Inter & JetBrains Mono), elevation shadows, dark mode rules, and standard
  Tailwind component recipes (buttons, badges, cards, forms, modals).
---

# KalmiPrep Design System & Component Library

KalmiPrep is a modern, high-performance examination preparation platform for Nigerian students (UTME/JAMB, WAEC, NECO). The interface must balance academic clarity, high-stakes examination focus, and tactile, premium mobile ergonomics.

---

## 1. Core Principles

1. **Academic Clarity Over Clutter**: Generous whitespace, scannable hierarchies, and distinct visual hierarchy between instructions, questions, and action buttons.
2. **True Dark Mode (Navy Scale)**: Never use pure black (`#000000`). Use rich dark navy surfaces (`#020617`, `#0f172a`, `#1e293b`) with calibrated slate text colors to eliminate eye fatigue.
3. **Subject-Specific Accent Coding**:
   - **Mathematics**: Blue (`math` / `#3b82f6`)
   - **Chemistry**: Emerald (`chem` / `#10b981`)
   - **Physics**: Purple/Violet (`phys` / `#8b5cf6`)
4. **Accessible Contrast (WCAG AA)**: Minimum 4.5:1 text-to-background contrast ratio in both light and dark modes.

---

## 2. Token Quick Reference

### Color Palette

| Token Group | Primary Shades | Usage |
| :--- | :--- | :--- |
| **`brand`** | `brand-500 (#22c55e)`, `brand-600 (#16a34a)`, `brand-700 (#15803d)` | Primary CTAs, active indicators, success states, brand wordmark |
| **`navy`** | `navy-950 (#020617)`, `navy-900 (#0f172a)`, `navy-800 (#1e293b)`, `navy-700 (#334155)` | Dark-mode body backgrounds, card surfaces, borders, dividers |
| **`slate`** | `slate-50 (#f8fafc)`, `slate-100 (#f1f5f9)`, `slate-800 (#1e293b)`, `slate-900 (#0f172a)` | Light-mode backgrounds, cards, typography |
| **`math`** | `math (#3b82f6)`, `math-light (#eff6ff)`, `math-dark (#1d4ed8)` | Mathematics exam cards, calculus badges, algebra filters |
| **`chem`** | `chem (#10b981)`, `chem-light (#ecfdf5)`, `chem-dark (#047857)` | Chemistry exam cards, periodic elements, reaction steps |
| **`phys`** | `phys (#8b5cf6)`, `phys-light (#f5f3ff)`, `phys-dark (#6d28d9)` | Physics exam cards, mechanics badges, vectors |

For detailed hex scales and alpha overlays, see [Color Tokens Reference](./references/color-tokens.md).

### Typography

- **Headings & Body**: `font-sans` (`Inter`, `-apple-system`, `sans-serif`)
- **Math, Numbers, Timers, Calculator**: `font-mono` (`"JetBrains Mono"`, `ui-monospace`, `monospace`)

---

## 3. Component Blueprints

For copy-paste ready Tailwind component recipes (Buttons, Badges, Cards, Form Inputs, Modals, and Alerts), see [Component Recipes Reference](./references/component-recipes.md).

### Quick Recipes

#### Primary Action Button
```html
<button type="button" class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 active:scale-[0.98] shadow-sm hover:shadow-md transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-navy-900">
  <i data-lucide="play" class="w-4 h-4"></i>
  <span>Start Practice</span>
</button>
```

#### Glassmorphism Surface Card
```html
<div class="p-6 rounded-2xl bg-white/80 dark:bg-navy-900/80 backdrop-blur-md border border-slate-200/80 dark:border-navy-750 shadow-card hover:shadow-elevated transition-all duration-200">
  <!-- Card content -->
</div>
```

#### Status Badge Pill
```html
<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-wide bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 border border-brand-200/80 dark:border-brand-800/60">
  <span class="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse"></span>
  JAMB UTME Ready
</span>
```

---

## 4. Verification & CSS Compilation
After editing classes in any template:
1. Recompile Tailwind CSS: `npm run build:css`
2. Inspect template in both Light Mode (`class=""`) and Dark Mode (`class="dark"`).

## Anti-AI UI & Anti-Slop Guidelines
All design tokens and component implementations must adhere to the `kalmiprep-anti-ai-ui` skill:
- **No Floating Glassmorphism**: Never use transparent blurred backgrounds without solid, high-contrast borders (`border-slate-200 dark:border-navy-700`).
- **Tactile Affordance**: Buttons and inputs must have visible physical borders and active depression states (`active:translate-y-0.5 active:shadow-inner`).
- **Zero AI Tropes**: Prohibit sparkle emojis (`✨`), decorative rainbow text gradients, and corporate Memphis illustrations.
- **High Information Density**: Prioritize compact padding (`py-2 px-3`) and clear typography hierarchy over vast empty whitespace.

