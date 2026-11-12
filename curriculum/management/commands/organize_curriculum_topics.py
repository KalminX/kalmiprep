"""
Management command to normalize curriculum topics into 14-18 canonical UTME/WAEC
syllabus topics per subject, reclassify all questions using the multi-field weighted
classifier + ground-truth lookup, and safely migrate all foreign keys.
"""
from collections import Counter
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from classrooms.models import ClassAssignment
from core.cache_utils import invalidate_all_curriculum_cache
from curriculum.models import Subject, Subtopic, Topic
from monetization.models import PaidTest
from practice.models import PracticeSession
from progress.models import TopicMastery
from questions.classifier import (
    CANONICAL_TOPICS,
    GROUND_TRUTH_TOPIC_MAP,
    classify_question_topic,
)
from questions.models import Question


class Command(BaseCommand):
    help = "Consolidate topics into 14-18 canonical syllabus topics per subject and reclassify all questions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate topic consolidation and question reclassification without modifying the database.",
        )
        parser.add_argument(
            "--subject",
            type=str,
            help="Optional subject slug to process (e.g. chemistry, mathematics, physics, biology, english-language).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        subject_filter = options.get("subject")

        subjects_to_run = (
            [subject_filter]
            if subject_filter
            else list(CANONICAL_TOPICS.keys())
        )

        mode_str = "DRY RUN" if dry_run else "LIVE EXECUTION"
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== KalmiPrep Topic Consolidation & Question Classifier ({mode_str}) ==="))

        overall_total = 0
        overall_matched = 0

        for subj_slug in subjects_to_run:
            if subj_slug not in CANONICAL_TOPICS:
                self.stderr.write(self.style.ERROR(f"Unknown subject slug: {subj_slug}"))
                continue

            subject = Subject.objects.filter(slug=subj_slug).first()
            if not subject:
                self.stderr.write(self.style.WARNING(f"Subject '{subj_slug}' not found in DB, skipping."))
                continue

            canonical_defs = CANONICAL_TOPICS[subj_slug]
            canonical_slugs = [t["slug"] for t in canonical_defs]

            questions = list(
                Question.objects.filter(subject=subject)
                .select_related("topic", "subtopic")
                .prefetch_related("options")
            )

            dist_counter = Counter()
            method_counter = Counter()
            reassignments = []

            for q in questions:
                opts_text = " | ".join(o.text for o in q.options.all())
                best_slug, score, method = classify_question_topic(
                    subject_slug=subj_slug,
                    question_text=q.question_text,
                    explanation=q.explanation or "",
                    options_text=opts_text,
                    source_id=q.source_id,
                )
                dist_counter[best_slug] += 1
                method_counter[method] += 1
                reassignments.append((q, best_slug))

            subj_total = len(questions)
            subj_matched = subj_total - method_counter["fallback"]
            overall_total += subj_total
            overall_matched += subj_matched

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\n[{subject.name.upper()}] Total Questions: {subj_total:,} | "
                    f"Matched: {subj_matched:,}/{subj_total:,} ({(subj_matched / subj_total * 100) if subj_total else 0:.1f}%) | "
                    f"Ground-Truth: {method_counter['ground_truth_source_id'] + method_counter['ground_truth_text']:,} | "
                    f"Classifier: {method_counter['weighted_classifier']:,} | "
                    f"Fallback: {method_counter['fallback']:,}"
                )
            )
            for tdef in canonical_defs:
                cnt = dist_counter[tdef["slug"]]
                self.stdout.write(f"  [{tdef['order']:2d}] {tdef['name']:64s} ({tdef['slug']}): {cnt:4d}")

            if dry_run:
                continue

            with transaction.atomic():
                # 1. Upsert canonical Topic rows with temporary high order first to avoid any unique constraint collisions
                canonical_topic_objs = {}
                for tdef in canonical_defs:
                    topic_obj = Topic.objects.filter(subject=subject, slug=tdef["slug"]).first()
                    if not topic_obj:
                        # Check if a topic with the exact name already exists for this subject
                        topic_obj = Topic.objects.filter(subject=subject, name=tdef["name"]).first()
                        if topic_obj:
                            topic_obj.slug = tdef["slug"]

                    if topic_obj:
                        topic_obj.name = tdef["name"]
                        topic_obj.description = tdef.get("description", "")
                        topic_obj.order = tdef["order"]
                        topic_obj.save()
                    else:
                        topic_obj = Topic.objects.create(
                            subject=subject,
                            slug=tdef["slug"],
                            name=tdef["name"],
                            description=tdef.get("description", ""),
                            order=tdef["order"],
                        )
                    canonical_topic_objs[tdef["slug"]] = topic_obj

                # 2. Bulk-update all Question rows for this subject
                to_update = []
                for q, target_slug in reassignments:
                    target_topic = canonical_topic_objs[target_slug]
                    needs_save = False
                    if q.topic_id != target_topic.id:
                        q.topic = target_topic
                        needs_save = True
                    if q.subtopic_id and q.subtopic and q.subtopic.topic_id != target_topic.id:
                        q.subtopic = None
                        needs_save = True
                    if needs_save:
                        to_update.append(q)

                if to_update:
                    Question.objects.bulk_update(to_update, ["topic", "subtopic"], batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"  -> Updated {len(to_update):,} questions in {subject.name}."))

                # 3. Migrate foreign keys on obsolete Topic rows and delete obsolete topics
                obsolete_topics = list(
                    Topic.objects.filter(subject=subject).exclude(
                        id__in=[t.id for t in canonical_topic_objs.values()]
                    )
                )

                for old_topic in obsolete_topics:
                    # Determine best canonical topic for migrating user progress / sessions
                    mapped_slug = GROUND_TRUTH_TOPIC_MAP.get(subj_slug, {}).get(old_topic.slug)
                    if not mapped_slug or mapped_slug not in canonical_topic_objs:
                        mapped_slug, _, _ = classify_question_topic(
                            subject_slug=subj_slug,
                            question_text=f"{old_topic.name} {old_topic.description or ''}",
                        )
                    target_topic = canonical_topic_objs.get(
                        mapped_slug, canonical_topic_objs[canonical_slugs[0]]
                    )

                    # Migrate TopicMastery (merging by user/session_key + topic)
                    for tm in TopicMastery.objects.filter(topic=old_topic):
                        existing = TopicMastery.objects.filter(
                            user=tm.user,
                            session_key=tm.session_key,
                            topic=target_topic,
                        ).first()
                        if existing:
                            existing.questions_attempted += tm.questions_attempted
                            existing.questions_correct += tm.questions_correct
                            existing.save()
                            tm.delete()
                        else:
                            tm.topic = target_topic
                            tm.save()

                    # Migrate PracticeSession
                    PracticeSession.objects.filter(topic=old_topic).update(topic=target_topic)

                    # Migrate ClassAssignment
                    ClassAssignment.objects.filter(topic=old_topic).update(topic=target_topic)

                    # Migrate PaidTest M2M
                    for pt in PaidTest.objects.filter(topics=old_topic):
                        pt.topics.add(target_topic)
                        pt.topics.remove(old_topic)

                    # Delete obsolete Subtopics and the obsolete Topic itself
                    Subtopic.objects.filter(topic=old_topic).delete()
                    old_topic.delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> Pruned {len(obsolete_topics)} obsolete topics; retained {len(canonical_topic_objs)} canonical topics."
                    )
                )

        if not dry_run:
            invalidate_all_curriculum_cache()
            cache.clear()
            self.stdout.write(self.style.SUCCESS("\nCleared Redis curriculum and question caches."))

        pct = (overall_matched / overall_total * 100.0) if overall_total else 0.0
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n=== OVERALL SUMMARY: {overall_matched:,}/{overall_total:,} ({pct:.1f}%) QUESTIONS MATCHED ==="
            )
        )
