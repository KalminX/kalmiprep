---
name: kalmiprep-workflow-tester
description: Automated workflow and nuance test runner for KalmiPrep. Use when verifying CBT exam mechanics, teacher monetization splits, student curriculum flows, and responsive UI invariants.
---

# KalmiPrep Workflow Tester

This skill provides the authoritative guide and instructions for running and maintaining KalmiPrep's living workflow blueprints.

## Purpose

Raw code and basic unit tests often miss domain-level invariants and hidden nuances—such as:
- Authoritative server timer synchronization vs visual clock drift.
- CBT question palette 4-state transitions (`unvisited`, `visited_unanswered`, `answered`, `flagged`).
- KaTeX formula parsing errors and horizontal layout blowouts.
- Precise 80/20 teacher/platform revenue splits calculated in integer kobo.
- Paystack webhook duplicate idempotency.
- WCAG AA dark mode contrast and touch target bounding boxes.
- Anti-AI UI tropes (prohibiting sparkles, neon text gradients, unreadable glassmorphism).

KalmiPrep maintains machine-readable blueprints in `.agents/blueprints/*.yaml` that capture both happy paths and edge nuances.

## Directory Structure

```
.agents/
  blueprints/
    cbt_exam_workflow.yaml         # Exam lifecycle, palette, timer, KaTeX, calculator
    teacher_monetization.yaml      # Paystack, 80/20 kobo splits, access PINs, idempotency
    student_curriculum.yaml        # Subject hierarchy, search debounce, bookmarks
    responsive_ui_invariants.yaml  # Contrast >=4.5:1, min 44px touch targets, mobile viewport
tests/
  e2e/
    blueprint_runner.js            # Automated blueprint scenario executor
    helpers/
      nuance_assertions.js         # KaTeX, WCAG contrast, kobo math, black prohibition
      auth_fixtures.js             # Test roles (student, teacher, staff)
```

## Running the Blueprints

### 1. Run all blueprints
```bash
docker run --rm -v "$(pwd):/app" -w /app node:20-alpine node tests/e2e/blueprint_runner.js
# Or via npm script:
npm run test:blueprints
```

### 2. Run a specific blueprint
```bash
npm run test:blueprints -- --blueprint=cbt_exam_workflow
npm run test:blueprints -- --blueprint=teacher_monetization
npm run test:blueprints -- --blueprint=responsive_ui_invariants
```

### 3. Run Real Playwright Browser E2E Tests (Full Chromium)
```bash
# Execute turnkey inside Docker on the webproxy network:
docker run --rm --network webproxy -e BASE_URL=http://kalmiprep-app:8000 -v "$(pwd):/app" kalmiprep-playwright:latest node tests/e2e/playwright_blueprint_executor.js
# Or via npm script:
npm run test:e2e:docker
```

### 3. Headed UI validation (Local browser)
```bash
npm run test:blueprints:headed
```

## Modifying or Adding Blueprints

When adding a new feature or workflow to KalmiPrep:
1. Locate or create a YAML file in `.agents/blueprints/<domain>.yaml`.
2. Define the invariant under `invariants:` with an ID (e.g., `INV-CBT-06`), descriptive rule, and severity level (`critical`, `high`, `medium`, `low`).
3. Add step-by-step verification under `scenarios:` specifying the route `path`, `prerequisites`, and `steps` (`action`, `target`, `assert_nuance`, `expected`).
4. Add any domain-specific formula or regex to `tests/e2e/helpers/nuance_assertions.js`.
5. Run `npm run test:blueprints` to ensure invariants pass.
