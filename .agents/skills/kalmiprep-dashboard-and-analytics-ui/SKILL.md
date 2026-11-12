---
name: kalmiprep-dashboard-and-analytics-ui
description: >-
  Use this skill when designing or refining data dashboards, student progress tracking,
  mastery progress rings, study streaks, teacher monetization ledger, and classroom live
  monitoring in KalmiPrep. Enforces clean information architecture, motivating visual metrics,
  and transparent transaction breakdowns.
---

# KalmiPrep Dashboard & Analytics UI Standards

Students and teachers rely on KalmiPrep's dashboards to track preparation readiness, weak topics, exam projections, and monetization earnings.

---

## 1. Student Progress & Mastery Dashboard

1. **Study Streak Metric (`#streakBadge`)**:
   - Amber flame icon with animated glow for active streaks.
   - Motivates daily practice consistency.
2. **Circular Mastery Progress Rings**:
   - Clean SVG rings with stroke dashoffset representation of percentage completion.
   - Colored by subject (`#3b82f6` for Math, `#10b981` for Chem, `#8b5cf6` for Physics).
3. **Weak Topics Intervention Deck**:
   - Clear cards identifying topics where student score is below 50%.
   - Direct CTA: `[ Practice This Topic Now ]` linking to targeted drill sessions.

---

## 2. Teacher Monetization & Financial Ledger

1. **Wallet Balance Card**:
   - Prominently displays available balance in Naira (e.g. `₦42,500.00`).
   - Clear distinction between **Available Balance** and **Pending Withdrawals**.
2. **Transparent 80/20 Revenue Split**:
   - Test sales breakdown showing gross sale, teacher's 80% credit, and platform 20% share.
   - All monetary calculations stored in kobo and formatted with Nigerian Naira currency symbol (`₦`).
3. **Withdrawal Request Status Flow**:
   - Badges: `Pending` (Amber) $\to$ `Under Review` (Blue) $\to$ `Paid` (Emerald) $\to$ `Rejected` (Rose).

---

## 3. Classroom Live Activity Monitoring

1. **Live WebSocket Connectivity Pill**:
   - Green pulsing dot: `Live Updates Active`.
2. **Student Submission Roster**:
   - Shows student name, score, submission timestamp, and time spent.
   - Privacy Invariant: NEVER display student personal phone numbers or email addresses on public teacher rosters.

For widget markup and SVG circles, refer to [Dashboard Widgets Reference](./references/dashboard-widgets.md).

## Anti-AI Utilitarian Analytics Invariants
- **Data-Ink Dominance**: Eliminate decorative charts with zero actionable utility; prioritize compact stat lines, sparklines, and authentic UTME score gauges (0–400 scale).
- **Anti-Slop Copywriting**: Replace generic congratulatory fluff with specific performance metrics (e.g. "Top 4% in JAMB Chemistry • Speed: 38s/Q").
- **Authentic Nigerian Financials**: Render all wallet and test purchase earnings with proper Nigerian Naira formatting (`₦`) backed by integer kobo precision.

