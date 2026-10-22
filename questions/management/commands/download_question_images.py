import os
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from questions.models import Question

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

class Command(BaseCommand):
    help = "Download question diagrams from myschool storage and link them to local MEDIA"

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=16, help="Concurrent download threads")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of questions to process")

    def handle(self, *args, **options):
        workers = options["workers"]
        limit = options["limit"]

        media_dir = Path(settings.MEDIA_ROOT) / "question_diagrams"
        media_dir.mkdir(parents=True, exist_ok=True)

        qs = Question.objects.filter(has_image=True).exclude(image_url="").exclude(image_url__isnull=True)
        if limit:
            qs = qs[:limit]

        total_questions = qs.count()
        self.stdout.write(self.style.SUCCESS(f"Found {total_questions} questions with diagrams to process."))

        downloaded_count = 0
        already_existed = 0
        failed_count = 0

        # Map filename to question IDs
        items_to_download = []
        for q in qs:
            raw_url = q.image_url or ""
            filename = raw_url.rstrip("/").split("/")[-1]
            if not filename or len(filename) < 4:
                continue

            dest_path = media_dir / filename
            if dest_path.exists() and dest_path.stat().st_size > 500:
                # File already on disk locally
                if not q.image or str(q.image) != f"question_diagrams/{filename}":
                    q.image = f"question_diagrams/{filename}"
                    q.save(update_fields=["image"])
                already_existed += 1
            else:
                items_to_download.append((q.id, filename, dest_path))

        self.stdout.write(f"Already downloaded / linked: {already_existed}. Need download: {len(items_to_download)}")

        def download_file(item):
            qid, fname, dest = item
            quoted_fname = urllib.parse.quote(fname)
            candidate_urls = [
                f"https://myschool.ng/storage/classroom/{quoted_fname}",
                f"https://myschool.ng/storage/serve/{quoted_fname}",
            ]
            
            for url in candidate_urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": USER_AGENTS[hash(fname) % len(USER_AGENTS)]}
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        if resp.status == 200:
                            data = resp.read()
                            if len(data) > 300:  # Valid image payload
                                dest.write_bytes(data)
                                return qid, fname, True, url
                except Exception:
                    continue
            return qid, fname, False, None

        if items_to_download:
            self.stdout.write(f"Starting multi-threaded download with {workers} workers...")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(download_file, item): item for item in items_to_download}
                for f in as_completed(futures):
                    qid, fname, success, final_url = f.result()
                    if success:
                        downloaded_count += 1
                        Question.objects.filter(id=qid).update(
                            image=f"question_diagrams/{fname}",
                            image_url=final_url or f"https://myschool.ng/storage/classroom/{fname}",
                            has_image=True
                        )
                    else:
                        failed_count += 1

                    if (downloaded_count + failed_count) % 100 == 0:
                        self.stdout.write(f"Progress: {downloaded_count} downloaded, {failed_count} failed...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Downloaded: {downloaded_count}, Already on disk: {already_existed}, Failed: {failed_count}"
            )
        )
