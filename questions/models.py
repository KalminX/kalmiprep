from django.db import models
from curriculum.models import Subject, Topic, Subtopic


class Question(models.Model):
    class ExamType(models.TextChoices):
        UTME = "UTME", "UTME / JAMB"
        WAEC = "WAEC", "WAEC / WASSCE"
        NECO = "NECO", "NECO SSCE"
        GENERAL = "GENERAL", "General Practice"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Foundational / Easy"
        MEDIUM = "MEDIUM", "Standard / Medium"
        HARD = "HARD", "Advanced / Hard"

    class VerificationStatus(models.TextChoices):
        VERIFIED = "VERIFIED", "Officially Verified"
        COMMUNITY = "COMMUNITY", "Community Validated"
        UNVERIFIED = "UNVERIFIED", "Unverified / Draft"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="questions")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    subtopic = models.ForeignKey(Subtopic, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    
    exam_type = models.CharField(max_length=20, choices=ExamType.choices, default=ExamType.UTME, db_index=True)
    exam_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    question_number = models.PositiveIntegerField(null=True, blank=True)
    
    question_text = models.TextField(help_text="Formatted text including LaTeX formulas and chemical equations")
    
    has_image = models.BooleanField(default=False)
    image = models.ImageField(upload_to="question_diagrams/", blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    explanation = models.TextField(blank=True, help_text="Detailed step-by-step working solution")
    explanation_url = models.URLField(max_length=500, blank=True, null=True)
    
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MEDIUM, db_index=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.VERIFIED,
    )
    is_published = models.BooleanField(default=True, db_index=True)
    
    # Source provenance and licensing attribution
    source_platform = models.CharField(max_length=150, default="Official Exam / Past Question Archive")
    source_id = models.CharField(max_length=100, blank=True, db_index=True, help_text="ID in upstream scraper dataset")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-exam_year", "question_number", "id"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        year_str = f" ({self.exam_year})" if self.exam_year else ""
        num_str = f" Q{self.question_number}" if self.question_number else f" #{self.id}"
        return f"[{self.subject.code}] {self.get_exam_type_display()}{year_str}{num_str}"

    @property
    def correct_option(self):
        return self.options.filter(is_correct=True).first()

    @property
    def has_diagram(self):
        return bool(self.has_image and (self.image or self.image_url))

    @property
    def has_solution(self):
        return bool(self.explanation and self.explanation.strip())

    @property
    def exam_badge_label(self):
        year_str = f" {self.exam_year}" if self.exam_year else ""
        return f"{self.get_exam_type_display()}{year_str}"


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    tag = models.CharField(max_length=5, help_text="Option tag e.g. A, B, C, D, E")
    text = models.TextField(help_text="Option text or LaTeX equation")
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "tag"]
        unique_together = ("question", "tag")
        verbose_name = "Option"
        verbose_name_plural = "Options"

    def __str__(self):
        status = " (Correct)" if self.is_correct else ""
        return f"{self.tag.upper()}. {self.text[:50]}{status}"

    @property
    def label(self):
        return self.tag.upper()
