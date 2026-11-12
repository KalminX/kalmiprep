# KalmiPrep

> A deliberate practice & computer-based testing (CBT) examination preparation platform designed for Nigerian students preparing for **UTME/JAMB**, **WAEC WASSCE**, and **NECO SSCE**.

---

## 🌟 Key Features

- **JAMB UTME CBT Simulation**: Authentic 4-subject, 180-question, 400-mark mock examinations with full question navigation grids, flag for review, and live synchronized countdown timers.
- **GoF-Engineered Scientific Calculator**: Standard CBT on-screen scientific calculator modal built with **Gang of Four (GoF)** design patterns:
  - **Memento Pattern**: Persists calculator state (expression, result, last answer, angle mode, memory) to local storage so page refreshes or question pagination never lose work.
  - **Command Pattern**: Encapsulates calculator operations (`append`, `clear`, `backspace`, `evaluate`, `memory`).
  - **State Pattern**: Handles calculator transitions (`Input`, `Evaluated`, `Error`) with operator chaining from previous results (`Ans`).
- **Dynamic Curriculum Cascades**: Cascading topic filtering where selecting a subject automatically updates syllabus topics in real time via HTMX.
- **Full Mathematical Rendering**: Crisp KaTeX mathematical typesetting for formulas, equations, and quantitative questions.
- **Cloudflare R2 Diagram Storage**: High-speed CDN object storage integration for past examination diagrams, circuit schematics, and geometry illustrations.
- **Micro-Buffered Question Ingestion**: High-velocity scraping and ingestion pipeline with Celery and RabbitMQ.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Django 5, Celery, Redis, PostgreSQL / SQLite
- **Frontend**: Django Templates, Tailwind CSS, HTMX, Zustand Vanilla Store, KaTeX, Lucide Icons
- **Storage & Infrastructure**: Docker, Docker Compose, WhiteNoise, Cloudflare R2 (S3-compatible)

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/KalminX/kalmiprep.git
cd kalmiprep
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/1
PAYSTACK_TEST_MODE=True
PAYSTACK_SECRET_KEY=sk_test_your_paystack_test_secret
PAID_TEST_PIN_SECRET=use-a-separate-long-random-secret-and-keep-it-stable
SITE_URL=http://127.0.0.1:8000
```

Paid teacher tests are unavailable until Paystack test credentials and `SITE_URL` are configured. For production, set `DEBUG=False`, `PAYSTACK_TEST_MODE=False`, a Paystack live secret key, a strong stable `PAID_TEST_PIN_SECRET`, and the canonical HTTPS `SITE_URL`. Keep `PAID_TEST_PIN_SECRET` stable: it derives the repeatable access PIN shown after a verified purchase. Configure Paystack to send `charge.success` and refund events to `/monetization/paystack/webhook/`.

Teacher invitations use Django email. Development sends invitation messages to the console; production needs `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` configured through the environment. The optional `TEACHER_TUTORIAL_URL` links the teacher onboarding checklist to a hosted orientation video.

Teacher class results use Django Channels over WebSockets. Production should set `REDIS_URL` so HTTP workers and ASGI workers share the Redis channel layer. The container serves `config.asgi:application` with Daphne; local development can use Django `runserver` and the in-memory channel layer.

### 3. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Database Migrations & Static Assets
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## 🧪 Testing

Run the test suite:
```bash
python manage.py test
```

---

## 📄 License

Proprietary © 2026 KalmiPrep. Built and operated by Kalmitech. All rights reserved.

## Code map

See [AGENTS.md](AGENTS.md) for the app ownership map, major request flows, and dependency boundaries. Teacher paid test behavior and operations are documented in [docs/teacher-test-monetization.md](docs/teacher-test-monetization.md).
