import csv
import json
import sys
from django.core.management.base import BaseCommand
from django.db.models import Q
from monetization.models import PaidTest, TestPurchase
from practice.models import PracticeSession


class Command(BaseCommand):
    help = "Query mock exam sessions and student performance records at will."

    def add_arguments(self, parser):
        parser.add_argument("--school", dest="school", help="Filter by school or teacher name/id")
        parser.add_argument("--test", dest="test", help="Filter by test title or share code")
        parser.add_argument("--paper-type", dest="paper_type", choices=["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"], help="Filter by paper type")
        parser.add_argument("--status", dest="status", choices=["ALL", "COMPLETED", "IN_PROGRESS", "NOT_STARTED"], default="ALL", help="Filter by session status")
        parser.add_argument("--search", dest="search", help="Search by student name or email")
        parser.add_argument("--format", dest="format", choices=["table", "json", "csv"], default="table", help="Output format")
        parser.add_argument("--limit", dest="limit", type=int, default=50, help="Maximum number of records to return")
        parser.add_argument("--out", dest="out", help="Write output directly to file path")

    def handle(self, *args, **options):
        queryset = (
            TestPurchase.objects.select_related("test", "teacher", "practice_session")
            .prefetch_related("practice_session__responses__question__subject")
            .order_by("-created_at")
        )

        if options["school"]:
            val = options["school"].strip()
            if val.isdigit():
                queryset = queryset.filter(teacher_id=int(val))
            else:
                queryset = queryset.filter(teacher__display_name__icontains=val)

        if options["test"]:
            val = options["test"].strip()
            queryset = queryset.filter(Q(test__title__icontains=val) | Q(test__share_code__icontains=val))

        if options["paper_type"]:
            queryset = queryset.filter(paper_type=options["paper_type"])

        status = options["status"]
        if status == "COMPLETED":
            queryset = queryset.filter(practice_session__status=PracticeSession.Status.COMPLETED)
        elif status == "IN_PROGRESS":
            queryset = queryset.filter(practice_session__status=PracticeSession.Status.IN_PROGRESS)
        elif status == "NOT_STARTED":
            queryset = queryset.filter(practice_session__isnull=True)

        if options["search"]:
            q = options["search"].strip()
            queryset = queryset.filter(Q(buyer_name__icontains=q) | Q(buyer_email__icontains=q))

        limit = options["limit"]
        records = list(queryset[:limit])

        data = []
        for p in records:
            s = p.practice_session
            utme_400 = s.score_out_of_400 if (s and s.is_completed) else None
            breakdown = []
            if s and s.is_completed:
                for b in s.subject_scores_breakdown:
                    breakdown.append({
                        "subject": b["subject"].name,
                        "score_100": b["score_100"],
                        "correct": b["correct"],
                        "total": b["total"],
                    })
            data.append({
                "candidate_number": p.candidate_number,
                "student_name": p.buyer_name,
                "student_email": p.buyer_email,
                "school_name": p.teacher.display_name,
                "test_title": p.test.title,
                "exam_structure": p.test.get_exam_structure_display(),
                "paper_type": p.get_paper_type_display(),
                "session_status": s.get_status_display() if s else "Not Started",
                "score": float(s.score) if s else 0.0,
                "total_questions": s.total_questions if s else p.test.question_count,
                "percentage": float(s.percentage) if s else 0.0,
                "utme_score_400": utme_400,
                "subject_breakdown": breakdown,
                "duration_spent": s.formatted_time_spent if s else "--:--",
                "completed_at": p.completed_at.isoformat() if p.completed_at else (
                    s.completed_at.isoformat() if (s and s.completed_at) else None
                ),
            })

        if options["format"] == "json":
            output_str = json.dumps(data, indent=2) + "\n"
            if options["out"]:
                with open(options["out"], "w", encoding="utf-8") as f:
                    f.write(output_str)
            else:
                self.stdout.write(output_str)
        elif options["format"] == "csv":
            import io
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                "Candidate #",
                "Student Name",
                "Email",
                "School / Institution",
                "Test Title",
                "Paper Type",
                "Status",
                "Score",
                "Total Questions",
                "Percentage (%)",
                "UTME 400",
                "Duration",
                "Completed At",
            ])
            for r in data:
                writer.writerow([
                    r["candidate_number"] or "",
                    r["student_name"],
                    r["student_email"],
                    r["school_name"],
                    r["test_title"],
                    r["paper_type"],
                    r["session_status"],
                    r["score"],
                    r["total_questions"],
                    f"{r['percentage']}%",
                    r["utme_score_400"] or "--",
                    r["duration_spent"],
                    r["completed_at"] or "--",
                ])
            output_str = buf.getvalue()
            if options["out"]:
                with open(options["out"], "w", encoding="utf-8") as f:
                    f.write(output_str)
            else:
                self.stdout.write(output_str)
        else:
            # Table format
            lines = []
            lines.append(f"\nFound {len(data)} matching mock attempt(s):\n")
            header = f"{'#':<4} | {'Student Name':<20} | {'Paper':<8} | {'Status':<12} | {'Score':<8} | {'UTME 400':<8} | {'Test Title'}"
            lines.append(header)
            lines.append("-" * len(header))
            for r in data:
                num = str(r["candidate_number"] or "-")
                score_str = f"{r['percentage']}%"
                utme_str = str(r["utme_score_400"] or "--")
                line = f"{num:<4} | {r['student_name'][:20]:<20} | {r['paper_type']:<8} | {r['session_status']:<12} | {score_str:<8} | {utme_str:<8} | {r['test_title']}"
                lines.append(line)
            lines.append("")
            output_str = "\n".join(lines)
            if options["out"]:
                with open(options["out"], "w", encoding="utf-8") as f:
                    f.write(output_str)
            else:
                self.stdout.write(output_str)
