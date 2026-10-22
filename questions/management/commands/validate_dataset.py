from django.core.management.base import BaseCommand
from questions.models import Question, Option


class Command(BaseCommand):
    help = "Validates the imported question dataset for answer key integrity, explanations, and diagrams."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE(">> Validating KalmiPrep Question Database Integrity..."))

        total_questions = Question.objects.count()
        missing_answers = []
        missing_explanations = []
        no_topics = []
        broken_math = []
        missing_diagram_files = []

        for q in Question.objects.select_related("subject", "topic").prefetch_related("options"):
            # Check answer key
            correct_opts = [opt for opt in q.options.all() if opt.is_correct]
            if len(correct_opts) == 0:
                missing_answers.append(q.id)

            # Check explanation
            if not q.explanation or not q.explanation.strip():
                missing_explanations.append(q.id)

            # Check topic
            if not q.topic:
                no_topics.append(q.id)

            # Check for unclosed math delimiters
            text = q.question_text + " " + q.explanation
            if text.count("\\(") != text.count("\\)") or text.count("\\[") != text.count("\\]"):
                broken_math.append(q.id)

            # Check diagram files if marked as having image
            if q.has_image and q.image:
                if not q.image.storage.exists(q.image.name):
                    missing_diagram_files.append((q.id, q.image.name))

        self.stdout.write(f"\nAudit Results ({total_questions} total questions evaluated):")
        self.stdout.write(f"  • Verified Answer Keys: {total_questions - len(missing_answers)} / {total_questions}")
        if missing_answers:
            self.stdout.write(self.style.WARNING(f"    [!] Missing Answers in Questions: {missing_answers[:10]}"))

        self.stdout.write(f"  • Explanations Attached: {total_questions - len(missing_explanations)} / {total_questions}")
        if missing_explanations:
            self.stdout.write(self.style.NOTICE(f"    [-] Missing Explanations in: {missing_explanations[:10]}"))

        self.stdout.write(f"  • Topic Assigned: {total_questions - len(no_topics)} / {total_questions}")
        self.stdout.write(f"  • Mathematical Delimiter Integrity: {total_questions - len(broken_math)} clean")
        if broken_math:
            self.stdout.write(self.style.WARNING(f"    [!] Mismatched LaTeX Delimiters: {broken_math[:10]}"))

        self.stdout.write(f"  • Diagram File Checks: {len(missing_diagram_files)} missing files on disk")

        self.stdout.write(self.style.SUCCESS("\n>> Dataset Validation Complete!"))
