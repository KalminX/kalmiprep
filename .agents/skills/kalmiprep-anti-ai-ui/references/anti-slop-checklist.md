# KalmiPrep Anti-AI UI 10-Point Checklist

Before committing any UI change, template, or CSS rule to KalmiPrep, verify every item below:

| # | Invariant Question | Requirement | Pass? |
| :-: | :--- | :--- | :-: |
| 1 | **No Sparkle / Magic Emojis?** | Zero `✨`, `🌟`, or magic wand icons in headers or buttons. | [ ] |
| 2 | **No Gradient Text Blobs?** | Headings use solid colors (`text-slate-900`, `text-white`, `text-brand-500`), never `bg-clip-text` rainbow gradients. | [ ] |
| 3 | **Tactile Button Depression?** | Buttons have physical borders and tangible active states (`active:translate-y-0.5 active:shadow-inner`). | [ ] |
| 4 | **No Unreadable Glassmorphism?** | Backgrounds have solid opacity ($\ge 95\%$) and defined borders (`border-slate-200 dark:border-navy-700`). | [ ] |
| 5 | **High Information Density?** | Information is compact and immediately visible without excessive empty whitespace or needless scrolling. | [ ] |
| 6 | **Authentic Exam Terminology?** | Real Nigerian exam framing: JAMB UTME, WAEC WASSCE, Post-UTME, authentic 400-point scales, ₦ kobo pricing. | [ ] |
| 7 | **Pragmatic Microcopy?** | Copy is factual, direct, and helpful. No "supercharge", "unleash", "elevate", or "game-changer". | [ ] |
| 8 | **KaTeX Formula Protection?** | Formulas reside in clean horizontal scrolling containers (`overflow-x-auto`) with no clipping or layout shifts. | [ ] |
| 9 | **WCAG AA Contrast Met?** | Text contrast against effective background is $\ge 4.5:1$ (and $\ge 7:1$ for primary reading text). | [ ] |
| 10 | **JAMB 8-Key Keyboard Shortcuts?** | Standard examination shortcuts (`A`, `B`, `C`, `D` to choose, `P` previous, `N` next, `S` submit, `R` reverse) are supported or visually indicated. | [ ] |
