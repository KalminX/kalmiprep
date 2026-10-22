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


def classify_topic(subject: Subject, text: str) -> Topic:
    """Classifies a question into a curriculum topic based on keywords in its text and explanation."""
    text_lower = text.lower()
    topics = list(subject.topics.all())
    if not topics:
        return None

    scores = {}
    for t in topics:
        scores[t] = 0

    subj_code = subject.code.upper()
    if subj_code == "MATH":
        if any(w in text_lower for w in ["base", "logarithm", "indices", "surd", "sets", "venn", "modulo", "prime", "fraction", "ratio", "percent"]):
            t = next((t for t in topics if "Number" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["polynomial", "quadratic", "equation", "inequalit", "variation", "sequence", "series", "progression", "g.p", "a.p", "matrix", "determinant", "binary"]):
            t = next((t for t in topics if "Algebra" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["triangle", "circle", "chord", "tangent", "angle", "bearing", "sin", "cos", "tan", "elevation", "depression", "polygon", "gradient", "geometry", "rhombus", "parallelogram"]):
            t = next((t for t in topics if "Geometry" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["derivative", "differentiate", "integral", "integrate", "limit", "maxima", "minima", "dy/dx"]):
            t = next((t for t in topics if "Calculus" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["mean", "median", "mode", "probability", "variance", "deviation", "frequency", "permutation", "combination", "dice", "coin"]):
            t = next((t for t in topics if "Statistics" in t.name), None)
            if t: scores[t] += 5

    elif subj_code == "CHEM":
        if any(w in text_lower for w in ["distillation", "chromatography", "filtration", "crystallization", "mixture", "purification", "sublimation"]):
            t = next((t for t in topics if "Separation" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["electron", "proton", "neutron", "isotope", "orbital", "covalent", "ionic", "electrovalent", "periodic", "bond", "valency"]):
            t = next((t for t in topics if "Atomic" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["mole", "avogadro", "molar", "empirical", "molecular formula", "titration", "mass", "volume of gas", "stoichiometry"]):
            t = next((t for t in topics if "Stoichiometry" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["acid", "base", "salt", "ph", "neutralization", "deliquescent", "efflorescent", "indicator", "litmus", "buffer"]):
            t = next((t for t in topics if "Acids" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["enthalpy", "exothermic", "endothermic", "catalyst", "equilibrium", "le chatelier", "activation energy", "kinetics"]):
            t = next((t for t in topics if "Kinetics" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["electrolysis", "faraday", "anode", "cathode", "oxidation", "reduction", "redox", "electrode"]):
            t = next((t for t in topics if "Electrochemistry" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["hydrocarbon", "alkane", "alkene", "alkyne", "benzene", "alcohol", "alkanol", "ester", "saponification", "polymer", "isomer"]):
            t = next((t for t in topics if "Organic" in t.name), None)
            if t: scores[t] += 5

    elif subj_code == "PHYS":
        if any(w in text_lower for w in ["velocity", "acceleration", "force", "newton", "momentum", "work", "energy", "power", "gravity", "circular", "elasticity", "pressure", "density", "archimedes"]):
            t = next((t for t in topics if "Mechanics" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["temperature", "thermometer", "expansion", "heat capacity", "latent heat", "boyle", "charles", "gas law", "conduction", "radiation"]):
            t = next((t for t in topics if "Thermal" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["wave", "sound", "frequency", "wavelength", "resonance", "echo", "reflection", "refraction", "lens", "mirror", "focal length", "light", "prism"]):
            t = next((t for t in topics if "Waves" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["charge", "coulomb", "electric", "current", "voltage", "resistance", "ohm", "magnetic", "solenoid", "transformer", "induction", "alternating"]):
            t = next((t for t in topics if "Electricity" in t.name), None)
            if t: scores[t] += 5
        if any(w in text_lower for w in ["nucleus", "quanta", "photon", "photoelectric", "half-life", "radioactive", "alpha", "beta", "gamma", "decay", "x-ray", "atomic"]):
            t = next((t for t in topics if "Modern" in t.name), None)
            if t: scores[t] += 5

    best_topic = max(scores, key=scores.get)
    if scores[best_topic] > 0:
        return best_topic
    return topics[0]  # default fallback


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
        # Also map alternative names
        subjects_map["maths"] = subjects_map.get("mathematics")

        media_diagrams_dir = Path("media/question_diagrams")
        media_diagrams_dir.mkdir(parents=True, exist_ok=True)
        dataset_images_dir = dataset_path / "images"

        for raw in records:
            raw_subj = (raw.get("subject") or "mathematics").lower().strip()
            subject = subjects_map.get(raw_subj)
            if not subject:
                # If subject not in DB, skip or map
                if "chem" in raw_subj:
                    subject = subjects_map.get("chemistry")
                elif "phys" in raw_subj:
                    subject = subjects_map.get("physics")
                elif "math" in raw_subj:
                    subject = subjects_map.get("mathematics")

            if not subject:
                self.stdout.write(self.style.WARNING(f"Skipping unknown subject: {raw_subj}"))
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

            source_id = str(raw.get("id") or "")
            q_text = normalize_latex(raw.get("question_text", ""))
            explanation = normalize_latex(raw.get("explanation", ""))
            explanation_url = raw.get("explanation_url") or ""

            if not q_text:
                skipped_count += 1
                continue

            # Classify topic
            topic_raw = raw.get("topic") or raw.get("topic_slug")
            topic = None
            if topic_raw:
                topic = subject.topics.filter(slug=topic_raw).first() or subject.topics.filter(name__iexact=str(topic_raw).strip()).first()
            if not topic:
                topic = classify_topic(subject, q_text + " " + explanation)

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
                question = Question(
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
                )
                if image_rel_path:
                    question.image = image_rel_path
                question.save()
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

            # Delete existing options if updating to ensure pristine state
            question.options.all().delete()

            for idx, opt_data in enumerate(raw_options, start=1):
                tag = str(opt_data.get("tag") or chr(64 + idx)).upper()
                opt_text = normalize_latex(opt_data.get("text", ""))
                is_correct = bool(opt_data.get("is_correct") or tag.lower() == correct_tag)
                Option.objects.create(
                    question=question,
                    tag=tag,
                    text=opt_text,
                    is_correct=is_correct,
                    order=idx,
                )

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
