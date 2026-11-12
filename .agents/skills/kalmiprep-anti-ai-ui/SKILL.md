---
name: kalmiprep-anti-ai-ui
description: Authoritative guide and heuristics for eliminating AI slop and enforcing tactile, high-density, culturally authentic Nigerian examination UI for KalmiPrep. Use whenever designing, evaluating, refactoring, or reviewing any frontend component, template, or microcopy.
---

# KalmiPrep Anti-AI UI & Anti-Slop Skill

This skill defines the non-negotiable design principles, banned tropes, and tactile engineering standards for KalmiPrep. It ensures every interface feels like an authentic, high-precision examination terminal rather than synthetic, generic "AI-generated slop."

---

## 1. The Core Philosophy: Physicality, Utility & Authenticity

When AI models design software, they default to low-information-density cards, meaningless gradient text, floating glassmorphism blobs, and generic corporate buzzwords. 

KalmiPrep builds for real Nigerian students taking high-stakes national examinations (JAMB UTME, WAEC, NECO, Post-UTME). Our UI must embody:
1. **Physical Tactility**: Mechanical keyboard feedback, distinct borders, tangible depth over fuzzy blur. Buttons must feel like physical keys on a computer or Casio calculator.
2. **Data-Ink Dominance**: Maximize useful exam information per square inch. Zero decorative fluff, zero empty space forcing candidates to scroll during timed tests.
3. **Authentic Cultural & Exam Grounding**: Real Nigerian examination formats, JAMB 8-key shortcuts (`A`, `B`, `C`, `D`, `P`, `N`, `S`, `R`), 400-point UTME scales, and integer kobo pricing (₦).
4. **Pragmatic, Direct Microcopy**: Crisp, direct, matter-of-fact text. No synthetic marketing enthusiasm.

---

## 2. Banned AI Slop vs. Approved Anti-AI Patterns

| Category | 🚫 Banned AI Slop Pattern | ✅ Approved KalmiPrep Anti-AI Pattern |
| :--- | :--- | :--- |
| **Decorative Icons** | Sparkles (`✨`), magic wands, generic glowing orbs | Crisp Lucide technical icons (`calculator`, `timer`, `bookmark`, `check-circle-2`) |
| **Gradients** | Neon rainbow text (`bg-clip-text text-transparent bg-gradient-to-r from-purple-500 to-indigo-500`) | Solid, high-contrast headings (`text-slate-900 dark:text-white` or `text-brand-500`) |
| **Glassmorphism** | `backdrop-blur-3xl bg-white/5 border border-white/10` with zero edge contrast | Solid, high-opacity dark surfaces (`bg-slate-900` or `bg-[#0b0f19]` with `border-slate-800`) |
| **Button Feel** | Flat gradient pill buttons that offer no feedback | Tactile buttons with clear borders, active depression: `active:translate-y-px active:shadow-inner border` |
| **Spacing** | 80px padding with 1 lonely sentence in a giant card | High-density grids, compact `py-2 px-3` padding, dense question palettes |
| **Microcopy** | "Supercharge your learning journey with our AI-powered magic" | "40 Questions • 45 Mins • JAMB 2024 Past Questions" |
| **Typography** | Generic soft geometric sans for everything | Sharp sans-serif for reading (`Inter`/`Plus Jakarta Sans`), crisp monospace for timers & equations (`JetBrains Mono`) |
| **Illustrations** | Corporate Memphis/3D clay blob characters | Real exam papers, authentic past-question diagrams, clean vector formula schematics |

---

## 3. Tactile Button & Control Recipes

### The Tactile JAMB CBT Keypress Button
Every option button in CBT practice must provide instantaneous physical keyboard and click feedback:

```html
<!-- Anti-AI Tactile Option Button -->
<button type="button" 
        class="w-full text-left p-3.5 rounded-xl border-2 border-slate-200 dark:border-navy-700 bg-white dark:bg-navy-900 hover:border-brand-500 dark:hover:border-brand-500 active:translate-y-0.5 active:shadow-inner transition-all flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-brand-500">
  <span class="w-8 h-8 rounded-lg border border-slate-300 dark:border-navy-600 bg-slate-100 dark:bg-navy-800 text-slate-700 dark:text-slate-200 font-mono font-bold flex items-center justify-center text-sm group-hover:border-brand-500 group-hover:text-brand-500">
    A
  </span>
  <span class="text-slate-800 dark:text-slate-200 text-sm font-medium leading-relaxed">
    3.0 &times; 10<sup>8</sup> m/s
  </span>
</button>
```

### The Casio fx-991 Tactile Calculator Key
```html
<button type="button"
        data-calc-key="sin"
        class="h-9 rounded-md bg-slate-800 border-b-2 border-slate-950 text-slate-200 text-xs font-mono font-semibold active:border-b-0 active:translate-y-0.5 shadow-sm hover:bg-slate-700">
  sin
</button>
```

---

## 4. Anti-Slop Copywriting Guidelines

1. **Be Specific, Not Hyperbolic**:
   - 🚫 "Experience next-level exam dominance!"
   - ✅ "Full JAMB 2024 Physics Mock: 40 questions covering Mechanics to Waves."
2. **State Metrics Directly**:
   - 🚫 "You're doing fantastic, keep it up!"
   - ✅ "Score: 78% (31/40) • Time per question: 42s • Weak topic: Simple Harmonic Motion."
3. **No Decorative Placeholders**:
   - Every badge, counter, and label must correspond to real underlying data. Never insert decorative dummy badges ("HOT", "POPULAR") unless dynamically backed by query counts.

---

## 5. Automated Verification

Always run the automated anti-slop scanner before finalizing any template:
```bash
.agents/skills/kalmiprep-anti-ai-ui/scripts/detect_ai_slop.sh
```
Or run full blueprint verification:
```bash
npm run test:blueprints -- --blueprint=responsive_ui_invariants
```
