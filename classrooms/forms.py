from django import forms
from django.utils import timezone

from curriculum.models import Subject, Topic
from .models import ClassAssignment, TeachingClass
from .services import select_assignment_questions


FIELD_CLASS = "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"


class TeachingClassForm(forms.ModelForm):
    class Meta:
        model = TeachingClass
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "e.g. UTME Evening Class"})}


class JoinClassForm(forms.Form):
    join_code = forms.CharField(
        max_length=8,
        min_length=8,
        strip=True,
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "autocomplete": "off", "placeholder": "8-character class code"}),
    )

    def clean_join_code(self):
        return self.cleaned_data["join_code"].upper()


class ClassAssignmentForm(forms.ModelForm):
    question_count = forms.IntegerField(min_value=1, max_value=180, initial=20, required=False)
    time_limit_minutes = forms.IntegerField(min_value=0, max_value=240, initial=0, required=False)
    due_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local", "class": FIELD_CLASS}),
    )
    elective_subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = ClassAssignment
        fields = ["classroom", "title", "kind", "subject", "topic", "question_count", "time_limit_minutes", "due_at", "elective_subjects"]
        widgets = {
            "classroom": forms.Select(attrs={"class": FIELD_CLASS}),
            "title": forms.TextInput(attrs={"class": FIELD_CLASS}),
            "kind": forms.Select(attrs={"class": FIELD_CLASS}),
            "subject": forms.Select(attrs={"class": FIELD_CLASS}),
            "topic": forms.Select(attrs={"class": FIELD_CLASS}),
        }

    def __init__(self, *args, teacher, **kwargs):
        self.teacher = teacher
        super().__init__(*args, **kwargs)
        self.fields["classroom"].queryset = TeachingClass.objects.filter(teacher=teacher)
        self.fields["subject"].queryset = Subject.objects.filter(is_active=True).order_by("name")
        self.fields["topic"].queryset = Topic.objects.select_related("subject").order_by("subject__name", "order", "name")
        english = Subject.objects.filter(slug__in=["english-language", "english"]).values_list("pk", flat=True)
        self.fields["elective_subjects"].queryset = Subject.objects.filter(is_active=True).exclude(pk__in=english).order_by("name")

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        due_at = cleaned.get("due_at")
        if due_at and due_at <= timezone.now():
            self.add_error("due_at", "Choose a future due date, or leave it blank.")

        if kind == ClassAssignment.Kind.TOPIC_DRILL:
            subject, topic = cleaned.get("subject"), cleaned.get("topic")
            if not cleaned.get("question_count"):
                self.add_error("question_count", "Choose how many questions to assign.")
            if not topic:
                self.add_error("topic", "Choose a topic for this drill.")
            if topic and subject and topic.subject_id != subject.pk:
                self.add_error("topic", "Choose a topic from the selected subject.")
            if topic and not subject:
                cleaned["subject"] = topic.subject
        elif kind == ClassAssignment.Kind.UTME_MOCK:
            electives = list(cleaned.get("elective_subjects") or [])
            if len(electives) != 3:
                self.add_error("elective_subjects", "Select exactly three UTME elective subjects.")
            else:
                try:
                    cleaned["question_ids"] = select_assignment_questions(
                        kind=kind,
                        topic=None,
                        question_count=180,
                        electives=electives,
                    )
                except ValueError as exc:
                    self.add_error(None, str(exc))
            cleaned["question_count"] = 180
            cleaned["time_limit_minutes"] = 120
            cleaned["subject"] = None
            cleaned["topic"] = None
        if kind == ClassAssignment.Kind.TOPIC_DRILL and cleaned.get("topic"):
            try:
                cleaned["question_ids"] = select_assignment_questions(
                    kind=kind,
                    topic=cleaned["topic"],
                    question_count=cleaned.get("question_count", 0),
                )
            except ValueError as exc:
                self.add_error(None, str(exc))
        return cleaned

    def save(self, commit=True):
        assignment = super().save(commit=False)
        assignment.question_count = self.cleaned_data["question_count"]
        assignment.time_limit_minutes = self.cleaned_data.get("time_limit_minutes") or 0
        assignment.question_ids = self.cleaned_data.get("question_ids", [])
        if commit:
            assignment.save()
            self.save_m2m()
        return assignment
