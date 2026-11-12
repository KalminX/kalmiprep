# KalmiPrep contributor map

## Project shape

KalmiPrep is a Django project. `config/` owns settings and root URL routing; each domain app owns its models, forms, views, templates, and tests. Keep code close to the domain that owns its data and expose HTTP routes through that app's `urls.py`.

| App | Responsibility | Main entry points |
| --- | --- | --- |
| `core` | Landing page, shared cache helpers, context processors, signals, template tags | `core/urls.py`, `core/views.py`, `core/cache_utils.py` |
| `accounts` | Authentication, student profile | `accounts/urls.py`, `accounts/views.py`, `accounts/forms.py` |
| `curriculum` | Subjects, topics, subtopics and curriculum pages | `curriculum/models.py`, `curriculum/urls.py` |
| `questions` | Question bank, filters, study pages, ingestion and maintenance commands | `questions/models.py`, `questions/filters.py`, `questions/tasks.py`, `questions/management/commands/` |
| `practice` | Practice sessions, CBT attempts, scoring and results | `practice/models.py`, `practice/urls.py`, `practice/views.py` |
| `progress` | Bookmarks, topic mastery and student progress pages | `progress/models.py`, `progress/urls.py`, `progress/views.py` |
| `monetization` | Teacher applications, paid tests, Paystack, wallet ledger and leaderboard | `monetization/models.py`, `monetization/services.py`, `monetization/views/`, `monetization/urls.py` |
| `classrooms` | Teacher-owned classes, student enrollment, free assignments and live class results | `classrooms/models.py`, `classrooms/services.py`, `classrooms/views.py`, `classrooms/consumers.py` |

## Important boundaries

- `monetization/views/teacher.py` handles teacher dashboard, publishing and results; `checkout.py` handles purchase and test access; `webhooks.py` handles provider callbacks.
- Put purchase access decisions in `monetization/access.py`. `practice` may depend on this policy, but should not import request handlers from monetization.
- `monetization/services.py` owns payment verification, idempotent ledger writes, refunds, PINs, test-attempt creation and withdrawal state changes. Do not credit a wallet from browser input or an unverified callback. Keep webhook work retry-safe and ledger entries unique.
- `practice` owns attempt execution and scoring; `monetization` associates paid purchases with a practice session. Avoid moving scoring rules into payment code.
- `classrooms` snapshots a shared question set per assignment and links individual attempts to existing `PracticeSession` records. Keep teacher roster/results scoped to the owning class and do not expose student contact details.
- Classroom completion and enrollment events are broadcast through `classrooms/realtime.py`; the authenticated ASGI websocket consumer checks assignment ownership before sending teacher-only result snapshots. Keep the HTTP page as the initial render and websocket transport as the live update path.
- `core/cache_utils.py` is the shared cache boundary. Curriculum and question writes invalidate cached catalog/filter data through `core/signals.py`.
- Templates are grouped by app under `templates/`; shared shell and navigation live under `templates/components/`.

## Where to look next

- Django tests are co-located as `<app>/tests.py` (plus the calculator integration module under `practice/`). The root `tests/` directory contains JavaScript calculator tests.
- Runtime configuration is in `config/settings.py`; local secrets belong in environment configuration and must never be committed.
- Feature and operational notes are under `docs/`. See `docs/teacher-test-monetization.md` for existing test pricing, revenue split, checkout, refunds and manual withdrawal behavior.
- Before deleting code, search for URL names, imports, template references, signals, admin registrations and management-task callers. Treat migrations as permanent history.
