import os
import mimetypes
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from django.core.management.base import BaseCommand
from django.conf import settings

R2_BUCKET = getattr(settings, "R2_BUCKET_NAME", os.getenv("R2_BUCKET_NAME", "edusphere"))
R2_ACCESS_KEY = getattr(settings, "R2_ACCESS_KEY_ID", os.getenv("R2_ACCESS_KEY_ID", ""))
R2_SECRET_KEY = getattr(settings, "R2_SECRET_ACCESS_KEY", os.getenv("R2_SECRET_ACCESS_KEY", ""))
R2_ENDPOINT = getattr(settings, "R2_ENDPOINT_URL", os.getenv("R2_ENDPOINT_URL", ""))

class Command(BaseCommand):
    help = "Sync all local question diagrams to Cloudflare R2 bucket under kalmiprep/ folder"

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=25, help="Concurrent upload threads")

    def handle(self, *args, **options):
        workers = options["workers"]
        media_dir = Path(settings.MEDIA_ROOT) / "question_diagrams"

        if not media_dir.exists():
            self.stdout.write(self.style.ERROR(f"Directory {media_dir} does not exist."))
            return

        files = [p for p in media_dir.iterdir() if p.is_file() and p.stat().st_size > 0]
        total_files = len(files)
        self.stdout.write(self.style.SUCCESS(f"Found {total_files} diagram files to sync to Cloudflare R2."))

        # Initialize boto3 client
        s3 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name="auto"
        )

        # List existing keys under kalmiprep/question_diagrams/ to skip redundant uploads
        self.stdout.write("Fetching existing keys in Cloudflare R2...")
        existing_keys = set()
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=R2_BUCKET, Prefix="kalmiprep/question_diagrams/"):
            for obj in page.get("Contents", []):
                existing_keys.add(obj["Key"])

        self.stdout.write(f"Existing files in R2 under kalmiprep/question_diagrams/: {len(existing_keys)}")

        to_upload = [p for p in files if f"kalmiprep/question_diagrams/{p.name}" not in existing_keys]
        self.stdout.write(f"Files needing upload to Cloudflare R2: {len(to_upload)}")

        uploaded = 0
        failed = 0

        def upload_file(path: Path):
            key = f"kalmiprep/question_diagrams/{path.name}"
            content_type, _ = mimetypes.guess_type(path.name)
            if not content_type:
                content_type = "image/png" if path.name.lower().endswith(".png") else "image/jpeg"

            try:
                # Thread-safe client
                client = boto3.client(
                    "s3",
                    endpoint_url=R2_ENDPOINT,
                    aws_access_key_id=R2_ACCESS_KEY,
                    aws_secret_access_key=R2_SECRET_KEY,
                    region_name="auto"
                )
                with open(path, "rb") as f:
                    client.put_object(
                        Bucket=R2_BUCKET,
                        Key=key,
                        Body=f.read(),
                        ContentType=content_type
                    )
                return True, path.name
            except Exception as e:
                return False, f"{path.name}: {e}"

        if to_upload:
            self.stdout.write(f"Starting parallel upload with {workers} threads...")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(upload_file, p): p for p in to_upload}
                for f in as_completed(futures):
                    success, msg = f.result()
                    if success:
                        uploaded += 1
                    else:
                        failed += 1
                        self.stdout.write(self.style.WARNING(f"Upload failed: {msg}"))

                    if (uploaded + failed) % 150 == 0:
                        self.stdout.write(f"Progress: {uploaded} uploaded to Cloudflare R2, {failed} failed...")

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Cloudflare R2 sync complete! Uploaded: {uploaded}, Already in R2: {len(existing_keys)}, Failed: {failed}"
            )
        )
