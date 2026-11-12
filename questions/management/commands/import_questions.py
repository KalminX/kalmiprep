import os
import re
import json
import shutil
import urllib.request
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify

from curriculum.models import Subject, Topic, Subtopic
from questions.classifier import classify_question_topic
from questions.models import Question, Option


def normalize_latex(text: str) -> str:
    """Normalizes scraped math expressions and HTML entities for pristine KaTeX rendering."""
    if not text:
        return ""
    
    # Replace common HTML entities that break KaTeX
    text = text.replace("&deg;", "^\\circ")
    text = text.replace("&leq;", "\\le")
    text = text.replace("&le;", "\\le")
    text = text.replace("&geq;", "\\ge")
    text = text.replace("&ge;", "\\ge")
    text = text.replace("&theta;", "\\theta")
    text = text.replace("&alpha;", "\\alpha")
    text = text.replace("&beta;", "\\beta")
    text = text.replace("&pi;", "\\pi")
    text = text.replace("&plusmn;", "\\pm")
    text = text.replace("&times;", "\\times")
    text = text.replace("&divide;", "\\div")
    text = text.replace("&radic;", "\\sqrt")
    text = text.replace("&infin;", "\\infty")
    text = text.replace("&sim;", "\\sim")
    text = text.replace("&Delta;", "\\Delta")
    text = text.replace("&mu;", "\\mu")
    text = text.replace("&omega;", "\\omega")
    text = text.replace("&Omega;", "\\Omega")
    text = text.replace("&lambda;", "\\lambda")
    
    # Normalize nested subscripts / superscripts like T\(_{2}\) to \(T_2\)
    text = re.sub(r'([A-Za-z0-9])\\\(_{([0-9A-Za-z])}\\\)', r'\(\1_\2\)', text)
    text = re.sub(r'([A-Za-z0-9])\\\(^{([0-9A-Za-z])}\\\)', r'\(\1^\2\)', text)

    return text.strip()


def classify_topic(
    subject: Subject,
    text: str,
    preloaded_topics: list = None,
    explanation: str = "",
    options_text: str = "",
    source_id: str = None,
    raw_topic_slug: str = None,
) -> Topic:
    """Classifies a question into its canonical curriculum topic using the multi-field weighted classifier."""
    topics = preloaded_topics if preloaded_topics is not None else list(subject.topics.all())
    if not topics:
        return None

    best_slug, _, _ = classify_question_topic(
        subject_slug=subject.slug,
        question_text=text,
        explanation=explanation,
        options_text=options_text,
        source_id=source_id,
        raw_topic_slug=raw_topic_slug,
    )
    if best_slug:
        matched = next((t for t in topics if t.slug == best_slug), None)
        if matched:
            return matched
    return topics[0]


class Command(BaseCommand):
    help = "Imports and normalizes scraped questions into KalmiPrep with KaTeX cleaning, topic mapping, and diagram management."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-path",
            type=str,
            default="/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset",
            help="Path to the myschool_dataset directory",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of questions to import (0 for all)",
        )
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force updating of existing questions and options in the database",
        )

    def handle(self, *args, **options):
        dataset_path = Path(options["dataset_path"])
        limit = options["limit"]
        self.stdout.write(self.style.NOTICE(f">> Starting KalmiPrep Question Ingestion from: {dataset_path}"))

        jsonl_path = dataset_path / "all_questions.jsonl"
        json_path = dataset_path / "all_questions.json"
        local_path = dataset_path / "local_questions.json"

        target_file = None
        is_jsonl = False
        if jsonl_path.exists() and jsonl_path.stat().st_size > 0:
            target_file = jsonl_path
            is_jsonl = True
        elif json_path.exists() and json_path.stat().st_size > 0:
            target_file = json_path
        elif local_path.exists():
            target_file = local_path

        if not target_file:
            self.stdout.write(self.style.ERROR("No dataset file found!"))
            return

        records = []
        if is_jsonl:
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        else:
            with open(target_file, "r", encoding="utf-8") as f:
                records = json.load(f)

        if limit > 0:
            records = records[:limit]

        self.stdout.write(f"Loaded {len(records)} candidate question records.")

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        images_copied = 0

        # Cache subjects
        subjects_map = {s.slug: s for s in Subject.objects.all()}
        subjects_map["maths"] = subjects_map.get("mathematics")
        subjects_map["english"] = subjects_map.get("english-language")
        subjects_map["use-of-english"] = subjects_map.get("english-language")
        subjects_map["english_language"] = subjects_map.get("english-language")
        subjects_map["bio"] = subjects_map.get("biology")
        subjects_map["chem"] = subjects_map.get("chemistry")
        subjects_map["phys"] = subjects_map.get("physics")

        # Pre-cache topics for fast O(1) in-memory resolution
        topics_by_subject = {}
        topic_lookup = {}
        for s in Subject.objects.prefetch_related("topics"):
            sub_topics = list(s.topics.all())
            topics_by_subject[s.id] = sub_topics
            for t in sub_topics:
                topic_lookup[(s.id, t.slug)] = t
                topic_lookup[(s.id, t.name.lower().strip())] = t

        # Pre-cache existing questions by source_id for instant O(1) duplicate checks
        force_update = options.get("force_update", False)
        existing_source_ids = set(
            Question.objects.exclude(source_id="").values_list("subject_id", "source_id")
        )

        media_diagrams_dir = Path("media/question_diagrams")
        media_diagrams_dir.mkdir(parents=True, exist_ok=True)
        dataset_images_dir = dataset_path / "images"

        for raw in records:
            raw_subj = (raw.get("subject") or "mathematics").lower().strip()
            subject = subjects_map.get(raw_subj)
            if not subject:
                if "chem" in raw_subj:
                    subject = subjects_map.get("chemistry")
                elif "phys" in raw_subj:
                    subject = subjects_map.get("physics")
                elif "math" in raw_subj:
                    subject = subjects_map.get("mathematics")
                elif "eng" in raw_subj:
                    subject = subjects_map.get("english-language")
                elif "bio" in raw_subj:
                    subject = subjects_map.get("biology")

            if not subject:
                self.stdout.write(self.style.WARNING(f"Skipping unknown subject: {raw_subj}"))
                skipped_count += 1
                continue

            source_id = str(raw.get("id") or "")
            if not force_update and source_id and (subject.id, source_id) in existing_source_ids:
                # Already ingested and verified, skip expensive SQL operations
                skipped_count += 1
                continue

            raw_etype = (raw.get("exam_type") or "UTME").upper().strip()
            if "JAMB" in raw_etype or "UTME" in raw_etype:
                exam_type = Question.ExamType.UTME
            elif "WAEC" in raw_etype or "WASSCE" in raw_etype:
                exam_type = Question.ExamType.WAEC
            elif "NECO" in raw_etype:
                exam_type = Question.ExamType.NECO
            else:
                exam_type = Question.ExamType.GENERAL

            raw_year = raw.get("exam_year")
            try:
                exam_year = int(raw_year) if raw_year else None
            except (ValueError, TypeError):
                exam_year = None

            q_text = normalize_latex(raw.get("question_text", ""))
            explanation = normalize_latex(raw.get("explanation", ""))
            explanation_url = raw.get("explanation_url") or ""

            if not q_text:
                skipped_count += 1
                continue

            # Classify topic using multi-field weighted classifier + ground-truth lookup
            topic_raw = raw.get("topic") or raw.get("topic_slug")
            raw_options_for_cls = raw.get("options") or []
            opts_text_for_cls = " | ".join(
                str(o.get("text") or "") for o in raw_options_for_cls if isinstance(o, dict)
            )
            topic = classify_topic(
                subject,
                q_text,
                preloaded_topics=topics_by_subject.get(subject.id, []),
                explanation=explanation,
                options_text=opts_text_for_cls,
                source_id=source_id,
                raw_topic_slug=str(topic_raw).lower().strip() if topic_raw else None,
            )

            has_image = bool(raw.get("has_image") or raw.get("image_url") or raw.get("local_image"))
            image_url = raw.get("image_url") or ""
            local_image_name = raw.get("local_image")

            # Try to handle local diagram
            image_rel_path = None
            if local_image_name and dataset_images_dir.exists():
                src_img = dataset_images_dir / local_image_name
                if src_img.exists():
                    dest_img = media_diagrams_dir / local_image_name
                    shutil.copy2(src_img, dest_img)
                    image_rel_path = f"question_diagrams/{local_image_name}"
                    images_copied += 1

            # Check if existing question matches (by source_id + subject or exact text)
            question = None
            if source_id:
                question = Question.objects.filter(subject=subject, source_id=source_id).first()
            if not question:
                question = Question.objects.filter(subject=subject, exam_type=exam_type, exam_year=exam_year, question_text=q_text).first()

            is_new = False
            if not question:
                question = Question.objects.create(
                    subject=subject,
                    topic=topic,
                    exam_type=exam_type,
                    exam_year=exam_year,
                    question_text=q_text,
                    explanation=explanation,
                    explanation_url=explanation_url,
                    has_image=has_image,
                    image_url=image_url,
                    source_id=source_id,
                    source_platform="Myschool Past Questions Archive",
                    verification_status=Question.VerificationStatus.VERIFIED if explanation else Question.VerificationStatus.COMMUNITY,
                    difficulty=Question.Difficulty.MEDIUM,
                    is_published=True,
                    image=image_rel_path or "",
                )
                if source_id:
                    existing_source_ids.add((subject.id, source_id))
                is_new = True
                imported_count += 1
            else:
                # Update existing record
                question.topic = topic or question.topic
                question.explanation = explanation or question.explanation
                question.explanation_url = explanation_url or question.explanation_url
                question.has_image = has_image or question.has_image
                if image_url:
                    question.image_url = image_url
                if image_rel_path:
                    question.image = image_rel_path
                question.save()
                updated_count += 1

            # Sync answer options
            raw_options = raw.get("options") or []
            correct_tag = (raw.get("correct_option") or "").strip().lower()

            if not is_new:
                question.options.all().delete()

            seen_tags = set()
            options_to_create = []
            for idx, opt_data in enumerate(raw_options, start=1):
                raw_tag = str(opt_data.get("tag") or chr(64 + idx)).upper().strip()
                tag = raw_tag if raw_tag and raw_tag not in seen_tags else chr(64 + idx)
                if tag in seen_tags:
                    continue
                seen_tags.add(tag)

                opt_text = normalize_latex(opt_data.get("text", ""))
                is_correct = bool(opt_data.get("is_correct") or tag.lower() == correct_tag)
                options_to_create.append(
                    Option(
                        question=question,
                        tag=tag,
                        text=opt_text,
                        is_correct=is_correct,
                        order=idx,
                    )
                )

            if options_to_create:
                Option.objects.bulk_create(options_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n>> Ingestion Complete!\n"
                f"   • Newly Imported: {imported_count}\n"
                f"   • Updated / Re-synced: {updated_count}\n"
                f"   • Skipped: {skipped_count}\n"
                f"   • Diagrams Linked: {images_copied}\n"
                f"   • Total Questions in KalmiPrep: {Question.objects.count()}"
            )
        )
