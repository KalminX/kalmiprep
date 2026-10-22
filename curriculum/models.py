from django.db import models
from django.utils.text import slugify


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short identifier e.g. MATH, CHEM, PHYS")
    description = models.TextField(blank=True)
    color_theme = models.CharField(
        max_length=30,
        default="math",
        choices=[
            ("math", "Blue / Indigo (Mathematics)"),
            ("chem", "Emerald / Green (Chemistry)"),
            ("phys", "Violet / Purple (Physics)"),
        ],
    )
    icon_name = models.CharField(max_length=50, default="book-open", help_text="Lucide icon name")
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def question_count(self):
        return self.questions.filter(is_published=True).count()

    @property
    def topic_count(self):
        return self.topics.count()


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True, help_text="Syllabus overview and essential learning objectives")
    order = models.PositiveIntegerField(default=1)
    icon_name = models.CharField(max_length=50, default="folder-git-2", help_text="Lucide icon identifier")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ("subject", "slug")
        verbose_name = "Topic"
        verbose_name_plural = "Topics"

    def __str__(self):
        return f"{self.subject.name}: {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def question_count(self):
        return self.questions.filter(is_published=True).count()

    @property
    def subtopic_count(self):
        return self.subtopics.count()


class Subtopic(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="subtopics")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ("topic", "slug")
        verbose_name = "Subtopic"
        verbose_name_plural = "Subtopics"

    def __str__(self):
        return f"{self.topic.name} → {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def question_count(self):
        return self.questions.filter(is_published=True).count()
