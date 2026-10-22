import os
import re
import json
import time
import random
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from celery import shared_task
from django.utils.text import slugify

from curriculum.models import Subject, Topic, Subtopic
from questions.models import Question, Option

logger = logging.getLogger("KalmiCeleryScraper")

BASE_DIR = Path("/app/myschool_dataset")
if not BASE_DIR.exists():
    BASE_DIR = Path("/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset")
BASE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

CELERY_LOG_FILE = BASE_DIR / "celery_tasks.log"
try:
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(CELERY_LOG_FILE) for h in logger.handlers):
        _fh = logging.FileHandler(CELERY_LOG_FILE, encoding="utf-8")
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(_fh)
except Exception:
    pass

BASE_URL = "https://myschool.ng"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


def get_http_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1.2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


http_session = get_http_session()


def resolve_nuxt_devalue(data: list) -> list:
    resolved_cache = {}

    def _resolve(idx, seen=None):
        if seen is None:
            seen = set()
        if isinstance(idx, int) and 0 <= idx < len(data):
            if idx in seen:
                return None
            if idx in resolved_cache:
                return resolved_cache[idx]
            val = data[idx]
            seen.add(idx)
            if isinstance(val, dict):
                res = {k: _resolve(v, seen.copy()) for k, v in val.items()}
                resolved_cache[idx] = res
                return res
            elif isinstance(val, list):
                res = [_resolve(v, seen.copy()) for v in val]
                resolved_cache[idx] = res
                return res
            resolved_cache[idx] = val
            return val
        return idx

    return [_resolve(i) for i in range(len(data))]


def extract_nuxt_payload(html: str) -> Optional[list]:
    match = re.search(r'<script[^>]*>(\[\[\"ShallowReactive\"[\s\S]*?)<\/script>', html)
    if not match:
        return None
    try:
        raw = json.loads(match.group(1))
        return resolve_nuxt_devalue(raw)
    except Exception:
        return None


def clean_html_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = (text.replace('&nbsp;', ' ')
                .replace('&amp;', '&')
                .replace('&lt;', '<')
                .replace('&gt;', '>')
                .replace('&quot;', '"')
                .replace('&#039;', "'"))
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


def normalize_latex(text: str) -> str:
    if not text:
        return ""
    text = text.replace("&deg;", "^\\circ")
    text = text.replace("&leq;", "\\le")
    text = text.replace("&le;", "\\le")
    text = text.replace("&geq;", "\\ge")
    text = text.replace("&ge;", "\\ge")
    text = text.replace("&theta;", "\\theta")
    text = text.replace("&alpha;", "\\alpha")
    text = text.replace("&beta;", "\\beta")
    text = text.replace("&pi;", "\\pi")
    text = text.replace("&times;", "\\times")
    text = text.replace("&divide;", "\\div")
    text = text.replace("&radic;", "\\sqrt")
    text = text.replace("&Delta;", "\\Delta")
    text = re.sub(r'([A-Za-z0-9])\\\(_{([0-9A-Za-z])}\\\)', r'\(\1_\2\)', text)
    text = re.sub(r'([A-Za-z0-9])\\\(^{([0-9A-Za-z])}\\\)', r'\(\1^\2\)', text)
    return text.strip()


def fetch_explanation(subject: str, q_id: int) -> tuple:
    url = f"{BASE_URL}/classroom/{subject}/{q_id}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        r = http_session.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            payload = extract_nuxt_payload(r.text)
            if payload:
                for item in payload:
                    if isinstance(item, dict) and "explanation" in item:
                        exp = clean_html_text(item.get("explanation") or "")
                        correct_tag = None
                        for o in item.get("options", []) or []:
                            if o.get("is_correct") in (1, True, "1"):
                                correct_tag = o.get("tag")
                                break
                        return exp, correct_tag
    except Exception as e:
        logger.debug(f"Failed explanation for Q#{q_id}: {e}")
    return "", None


def download_diagram(image_name: str) -> Optional[str]:
    if not image_name:
        return None
    dest_path = IMAGES_DIR / f"diag_{image_name}"
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return str(dest_path.relative_to(BASE_DIR))
    
    url = f"{BASE_URL}/uploads/{image_name}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        r = http_session.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return str(dest_path.relative_to(BASE_DIR))
    except Exception:
        pass
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=5, rate_limit="5/s", queue="scraping")
def scrape_subject_page_task(self, subject: str, page: int):
    """
    Celery task to fetch a single page of questions for a subject,
    parse questions & explanations in parallel, persist to per-subject JSONL,
    and trigger batch ingestion into PostgreSQL.
    """
    url = f"{BASE_URL}/classroom/{subject}?page={page}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        r = http_session.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning(f"[{subject}] Page {page} returned status {r.status_code}")
            return {"status": "error", "page": page, "code": r.status_code}

        payload = extract_nuxt_payload(r.text)
        if not payload:
            logger.warning(f"[{subject}] Page {page} payload extraction failed")
            return {"status": "no_payload", "page": page}

        # Find questions array
        q_list = []
        for item in payload:
            if isinstance(item, dict) and "practice_questions" in item:
                q_list = item["practice_questions"].get("data", []) or []
                break

        if not q_list:
            logger.info(f"[{subject}] Page {page}: No question records")
            return {"status": "empty", "page": page, "questions": 0}

        # Fetch explanations in parallel
        candidate_qs = [q for q in q_list if q.get("id")]
        explanations_map = {}
        if candidate_qs:
            with ThreadPoolExecutor(max_workers=min(5, len(candidate_qs))) as executor:
                future_to_qid = {
                    executor.submit(fetch_explanation, subject, q["id"]): q["id"]
                    for q in candidate_qs
                }
                for future in future_to_qid:
                    qid = future_to_qid[future]
                    try:
                        explanations_map[qid] = future.result()
                    except Exception:
                        explanations_map[qid] = ("", None)

        parsed_batch = []
        for q in q_list:
            q_id = q.get("id")
            if not q_id:
                continue

            collection = q.get("collection") or {}
            raw_image = q.get("image")
            local_img = download_diagram(raw_image) if raw_image else None
            image_url = f"{BASE_URL}/uploads/{raw_image}" if raw_image else None

            options = []
            correct_tag = None
            for opt in q.get("options", []):
                is_corr = bool(opt.get("is_correct"))
                if is_corr:
                    correct_tag = opt.get("tag")
                options.append({
                    "tag": opt.get("tag", "").upper(),
                    "text": clean_html_text(opt.get("description", "")),
                    "is_correct": is_corr,
                })

            explanation, exp_correct_tag = explanations_map.get(q_id, ("", None))
            if exp_correct_tag and not correct_tag:
                correct_tag = exp_correct_tag

            exam_type_str = collection.get("exam_type", "UTME")
            if exam_type_str.lower() in ("jamb", "utme"):
                exam_type_clean = "UTME"
            elif exam_type_str.lower() == "waec":
                exam_type_clean = "WAEC"
            elif exam_type_str.lower() == "neco":
                exam_type_clean = "NECO"
            else:
                exam_type_clean = "UTME"

            exam_year_val = collection.get("exam_year") or 2024

            record = {
                "id": q_id,
                "subject": subject,
                "exam_type": exam_type_clean,
                "exam_year": exam_year_val,
                "question_number": q.get("question_number", 1),
                "question_text": clean_html_text(q.get("question", "")),
                "has_image": bool(raw_image),
                "image_url": image_url,
                "local_image": local_img,
                "options": options,
                "correct_option": correct_tag,
                "explanation": explanation,
                "explanation_url": f"{BASE_URL}/classroom/{subject}/{q_id}",
            }
            parsed_batch.append(record)

        # Append to persistent JSONL
        jsonl_file = BASE_DIR / "all_questions.jsonl"
        with open(jsonl_file, "a", encoding="utf-8") as f:
            for rec in parsed_batch:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Update scraper progress
        progress_file = BASE_DIR / "scraper_progress.json"
        try:
            curr_progress = {}
            if progress_file.exists():
                with open(progress_file, "r", encoding="utf-8") as f:
                    curr_progress = json.load(f).get("completed_pages", {})
            done_set = set(curr_progress.get(subject, []))
            done_set.add(page)
            curr_progress[subject] = list(done_set)
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump({"completed_pages": curr_progress}, f, indent=2)
        except Exception:
            pass

        # Ingest directly into PostgreSQL via Celery ingestion task
        ingest_question_batch_task.delay(parsed_batch)

        logger.info(f"[{subject.upper()}] Celery page {page} completed: {len(parsed_batch)} questions extracted.")
        return {"status": "success", "subject": subject, "page": page, "count": len(parsed_batch)}

    except Exception as exc:
        logger.error(f"Error scraping {subject} page {page}: {exc}")
        raise self.retry(exc=exc)


@shared_task(queue="ingestion")
def ingest_question_batch_task(records: List[Dict[str, Any]]):
    """
    Celery task for safe, decoupled batch insertion of parsed questions into PostgreSQL.
    """
    if not records:
        return 0

    ingested_count = 0
    # Map subject slugs to Subject models
    slug_to_subj = {s.slug: s for s in Subject.objects.all()}

    # Cache preloaded topics
    topics_by_subj = {}
    for s in slug_to_subj.values():
        topics_by_subj[s.id] = list(s.topics.all())

    for rec in records:
        subj_slug = rec.get("subject")
        subject = slug_to_subj.get(subj_slug)
        if not subject:
            continue

        q_id = rec.get("id")
        q_text = normalize_latex(rec.get("question_text") or rec.get("question", ""))
        exp_text = normalize_latex(rec.get("explanation", ""))
        exam_type = rec.get("exam_type", "UTME")
        exam_year = rec.get("exam_year", 2024)
        q_num = rec.get("question_number", 1)

        # Fallback topic: assign first topic if no classifier matches
        subj_topics = topics_by_subj.get(subject.id, [])
        topic = subj_topics[0] if subj_topics else None

        # Upsert Question
        q_obj, created = Question.objects.update_or_create(
            subject=subject,
            exam_type=exam_type,
            exam_year=exam_year,
            question_number=q_num,
            defaults={
                "topic": topic,
                "question_text": q_text,
                "explanation": exp_text,
                "is_published": True,
            }
        )

        # Upsert Options
        for opt in rec.get("options", []):
            Option.objects.update_or_create(
                question=q_obj,
                tag=opt.get("tag", "A").upper(),
                defaults={
                    "text": normalize_latex(opt.get("text", "")),
                    "is_correct": bool(opt.get("is_correct", False)),
                }
            )

        ingested_count += 1

    logger.info(f"[POSTGRES-SYNC] Celery batch inserted/updated {ingested_count} questions into PostgreSQL.")
    return ingested_count
