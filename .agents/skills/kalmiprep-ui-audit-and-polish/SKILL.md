---
name: kalmiprep-ui-audit-and-polish
description: >-
  Use this skill whenever auditing, reviewing, or polishing templates, pages, or components
  across KalmiPrep. Enforces the visual quality checklist, WCAG AA/AAA contrast standards,
  dark mode consistency, empty state illustrations, loading skeletons, and Tailwind CSS
  recompilation verification.
---

# KalmiPrep UI Audit & Polish Runbook

Follow this step-by-step checklist to evaluate any template or page in KalmiPrep before concluding a design task.

---

## 1. The Quality Checklist

1. **Dark Mode Audit**:
   - Every background element with `bg-white` or `bg-slate-...` must have an explicit `dark:bg-navy-...` counter-class.
   - Text colors must have `text-slate-800/900` paired with `dark:text-slate-100/200`.
   - Borders must have `border-slate-200` paired with `dark:border-navy-750` or `dark:border-navy-800`.
   - **Never allow pure white text on light backgrounds** or **black text on dark backgrounds**.
2. **Accessible Contrast (WCAG AA)**:
   - Body text: minimum 4.5:1 contrast against surface.
   - Large headings & badges: minimum 3:1 contrast against surface.
   - KaTeX equations: verified in both light and dark modes.
3. **Empty States**:
   - When a list has 0 items (e.g. 0 bookmarks, 0 test submissions, 0 weak topics), NEVER show a blank white void.
   - Always display an illustrated empty state:
     - Clear icon (`bookmark-minus`, `inbox`, `file-question`)
     - Friendly title: *"No Bookmarked Questions Yet"*
     - Actionable CTA: `[ Browse Question Catalog ]`
4. **Loading States & Skeletons**:
   - HTMX targets must show smooth shimmer skeletons or subtle loaders (`#page-loading-bar`) during asynchronous fetches.
5. **Icon Integrity**:
   - Verify all Lucide icon names exist (`lucide.createIcons()` must not throw console warnings).
   - Use standard stroke width: `stroke-width="1.75"` or `2`.

---

## 2. Anti-AI Slop & Automated Verification

### Step 1: Scan for AI Slop Tropes
Run the anti-slop scanner:
```bash
./.agents/skills/kalmiprep-anti-ai-ui/scripts/detect_ai_slop.sh
```
Ensures 0 sparkle emojis (`✨`), 0 neon rainbow text gradients, and 0 marketing buzzwords.

### Step 2: Automated CSS Verification
Run the verification script:
```bash
./.agents/skills/kalmiprep-ui-audit-and-polish/scripts/verify_css.sh
```
Or manually run:
```bash
npm run build:css
```
Ensure that:
1. Tailwind compiler succeeds with 0 errors.
2. The compiled `static/css/styles.css` is updated.
