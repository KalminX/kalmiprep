import re
from django.core.management.base import BaseCommand
from questions.models import Question


class Command(BaseCommand):
    help = "Audit all questions in the database for LaTeX syntax anomalies, broken KaTeX delimiters, and malformed tags."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of questions to check (0 = check all).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        self.stdout.write(self.style.NOTICE("Starting KaTeX formula integrity audit..."))

        qs = Question.objects.prefetch_related("options").all().order_by("id")
        if limit > 0:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Auditing {total} questions across the database...")

        corrupted = []
        math_count = 0

        # Regular expressions for formula detection
        display_math_re = re.compile(r"\$\$([^$]+)\$\$|\\\[([^\]]+)\\\]")
        inline_math_re = re.compile(r"(?<!\$)\$([^$]+)\$(?!\$)|\\\(([^)]+)\\\)")

        for q in qs.iterator(chunk_size=500):
            has_math = False
            texts_to_check = [
                ("question_text", q.question_text or ""),
                ("explanation", q.explanation or ""),
            ]
            for opt in q.options.all():
                texts_to_check.append((f"option_{opt.tag}", opt.text or ""))

            for field_name, text in texts_to_check:
                if not text:
                    continue

                display_matches = display_math_re.findall(text)
                inline_matches = inline_math_re.findall(text)

                if display_matches or inline_matches:
                    has_math = True
                    # Check for unmatched curly braces inside formulas
                    formulas = [m[0] or m[1] for m in display_matches] + [m[0] or m[1] for m in inline_matches]
                    for f in formulas:
                        open_braces = f.count("{")
                        close_braces = f.count("}")
                        if open_braces != close_braces:
                            corrupted.append({
                                "question_id": q.id,
                                "field": field_name,
                                "formula": f[:80],
                                "reason": f"Unmatched curly braces: {open_braces} open vs {close_braces} close",
                            })

                # Check for stray unclosed $$ or \(
                if text.count("$$") % 2 != 0:
                    corrupted.append({
                        "question_id": q.id,
                        "field": field_name,
                        "formula": text[:80],
                        "reason": "Odd number of $$ delimiters (unclosed display math)",
                    })

            if has_math:
                math_count += 1

        self.stdout.write(self.style.SUCCESS(f"Audit completed: {total} questions scanned, {math_count} contain math equations."))

        if corrupted:
            self.stdout.write(self.style.ERROR(f"Found {len(corrupted)} questions with KaTeX syntax issues:"))
            for c in corrupted[:10]:
                self.stdout.write(f"  • Question #{c['question_id']} ({c['field']}): {c['reason']} in '{c['formula']}'")
            if len(corrupted) > 10:
                self.stdout.write(f"  ... and {len(corrupted) - 10} more.")
        else:
            self.stdout.write(self.style.SUCCESS("✓ Zero KaTeX equation errors detected across all checked questions!"))
