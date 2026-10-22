import os
import json
from pathlib import Path
from collections import Counter
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Inspects the raw myschool past questions scraper dataset and reports statistics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-path",
            type=str,
            default="/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset",
            help="Path to the myschool_dataset directory",
        )

    def handle(self, *args, **options):
        dataset_path = Path(options["dataset_path"])
        self.stdout.write(self.style.NOTICE(f">> Inspecting Dataset at: {dataset_path}"))

        if not dataset_path.exists():
            self.stdout.write(self.style.ERROR(f"Error: Directory {dataset_path} does not exist."))
            return

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
            self.stdout.write(self.style.WARNING("No questions dataset file found yet."))
            return

        # Load questions
        questions = []
        if is_jsonl:
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        questions.append(json.loads(line))
        else:
            with open(target_file, "r", encoding="utf-8") as f:
                questions = json.load(f)

        total = len(questions)
        self.stdout.write(self.style.SUCCESS(f"\nTotal Question Records Found: {total}"))

        subjects_counter = Counter()
        exam_types_counter = Counter()
        years_counter = Counter()
        options_counts = Counter()
        has_image_count = 0
        has_explanation_count = 0
        has_correct_option_count = 0
        has_latex_math_count = 0
        ids = set()
        duplicates = 0

        images_dir = dataset_path / "images"
        existing_images = set(os.listdir(images_dir)) if images_dir.exists() else set()

        for q in questions:
            qid = q.get("id")
            if qid in ids:
                duplicates += 1
            else:
                ids.add(qid)

            subj = (q.get("subject") or "UNKNOWN").lower()
            subjects_counter[subj] += 1

            etype = (q.get("exam_type") or "UNKNOWN").upper()
            exam_types_counter[etype] += 1

            year = q.get("exam_year")
            years_counter[year] += 1

            opts = q.get("options") or []
            options_counts[len(opts)] += 1

            if q.get("correct_option"):
                has_correct_option_count += 1

            if q.get("explanation") and q.get("explanation").strip():
                has_explanation_count += 1

            if q.get("has_image") or q.get("image_url") or q.get("local_image"):
                has_image_count += 1

            q_text = q.get("question_text", "")
            if "\\(" in q_text or "\\[" in q_text or "\\frac" in q_text or "\\sqrt" in q_text:
                has_latex_math_count += 1

        self.stdout.write("\n=== 1. Subject Breakdown ===")
        for s, count in subjects_counter.items():
            self.stdout.write(f"  • {s.capitalize()}: {count} ({count/total*100:.1f}%)")

        self.stdout.write("\n=== 2. Exam Type Breakdown ===")
        for e, count in exam_types_counter.items():
            self.stdout.write(f"  • {e}: {count} ({count/total*100:.1f}%)")

        self.stdout.write("\n=== 3. Options Distribution ===")
        for opt_len, count in sorted(options_counts.items()):
            self.stdout.write(f"  • {opt_len} options: {count} questions")

        self.stdout.write("\n=== 4. Content Richness & Provenance ===")
        self.stdout.write(f"  • Has Verified Correct Option: {has_correct_option_count} ({has_correct_option_count/total*100:.1f}%)")
        self.stdout.write(f"  • Has Detailed Step-by-Step Solution: {has_explanation_count} ({has_explanation_count/total*100:.1f}%)")
        self.stdout.write(f"  • Has Diagram / Figure Attached: {has_image_count} ({has_image_count/total*100:.1f}%)")
        self.stdout.write(f"  • Contains LaTeX Math Expressions: {has_latex_math_count} ({has_latex_math_count/total*100:.1f}%)")
        self.stdout.write(f"  • Duplicate Scraped Records Detected: {duplicates}")
        self.stdout.write(f"  • Local Diagram Files in Image Store: {len(existing_images)}")
        self.stdout.write(self.style.SUCCESS("\nInspection Finished Successfully."))
