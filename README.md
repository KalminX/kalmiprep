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
```

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
