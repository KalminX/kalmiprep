# KalmiPrep Color Tokens Reference

## 1. Brand Scale (Emerald)
```css
--brand-50:  #f0fdf4;
--brand-100: #dcfce7;
--brand-200: #bbf7d0;
--brand-300: #86efac;
--brand-400: #4ade80;
--brand-500: #22c55e; /* Primary Brand */
--brand-600: #16a34a; /* Primary Hover/Buttons */
--brand-700: #15803d; /* Text on light backgrounds */
--brand-800: #166534;
--brand-900: #14532d;
--brand-950: #052e16;
```

## 2. Navy Slate Scale (Dark Theme Foundation)
```css
--navy-50:  #f8fafc;
--navy-100: #f1f5f9;
--navy-200: #e2e8f0;
--navy-300: #cbd5e1;
--navy-400: #94a3b8; /* Muted subtext */
--navy-500: #64748b;
--navy-600: #475569;
--navy-700: #334155; /* Input borders in dark mode */
--navy-750: #243247; /* Card borders in dark mode */
--navy-800: #1e293b; /* Secondary surface */
--navy-850: #162033;
--navy-900: #0f172a; /* Card surface in dark mode */
--navy-950: #020617; /* Root dark body background */
```

## 3. Subject Identity Colors
| Subject | Light Tint | Solid Accent | Dark Text Accent |
| :--- | :--- | :--- | :--- |
| **Mathematics** | `bg-blue-50 dark:bg-blue-950/40` | `bg-blue-500` | `text-blue-700 dark:text-blue-300` |
| **Chemistry** | `bg-emerald-50 dark:bg-emerald-950/40` | `bg-emerald-500` | `text-emerald-700 dark:text-emerald-300` |
| **Physics** | `bg-purple-50 dark:bg-purple-950/40` | `bg-purple-500` | `text-purple-700 dark:text-purple-300` |

## 4. Elevation Shadows
- `shadow-subtle`: `0 1px 2px 0 rgba(0, 0, 0, 0.05)` (inner dividers, secondary buttons)
- `shadow-card`: `0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)` (content cards)
- `shadow-elevated`: `0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)` (modals, dropdowns)
- `shadow-glass`: `0 8px 32px 0 rgba(0, 0, 0, 0.08)` (floating dock, calculator modal)
