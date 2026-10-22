import json
from pathlib import Path
from django.core.management.base import BaseCommand
from questions.tasks import scrape_subject_page_task

SUBJECT_TARGET_PAGES = {
    "english-language": 1883,
    "physics": 1048,
    "chemistry": 943,
    "biology": 1079,
    "mathematics": 984,
}


class Command(BaseCommand):
    help = "Enqueues uncompleted subject pages into Celery/RabbitMQ for multi-worker distributed extraction"

    def add_arguments(self, parser):
        parser.add_argument("--subject", type=str, default="all", help="Subject slug or 'all'")
        parser.add_argument("--limit-pages", type=int, default=None, help="Max pages to queue per subject")
        parser.add_argument("--start-page", type=int, default=1, help="Page to start from")

    def handle(self, *args, **options):
        subject_arg = options["subject"]
        limit_pages = options["limit_pages"]
        start_page = options["start_page"]

        container_dir = Path("/app/myschool_dataset")
        host_dir = Path("/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset")
        dataset_dir = container_dir if container_dir.exists() else host_dir
        progress_file = dataset_dir / "scraper_progress.json"

        completed_pages = {}
        if progress_file.exists():
            try:
                with open(progress_file, "r", encoding="utf-8") as f:
                    completed_pages = json.load(f).get("completed_pages", {})
            except Exception:
                pass

        subjects_to_queue = (
            [subject_arg] if subject_arg != "all" else ["physics", "chemistry", "english-language", "biology"]
        )

        total_enqueued = 0

        for subj in subjects_to_queue:
            target_pages = SUBJECT_TARGET_PAGES.get(subj, 1000)
            done = set(completed_pages.get(subj, []))

            queued_for_subj = 0
            for page in range(start_page, target_pages + 1):
                if page in done:
                    continue

                scrape_subject_page_task.delay(subj, page)
                queued_for_subj += 1
                total_enqueued += 1

                if limit_pages and queued_for_subj >= limit_pages:
                    break

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Enqueued {queued_for_subj} pages for [{subj.upper()}] (already completed: {len(done)})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🚀 Total {total_enqueued} page tasks submitted to RabbitMQ queue 'scraping'!"
            )
        )
