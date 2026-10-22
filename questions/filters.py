import django_filters
from django import forms
from django.db.models import Q
from curriculum.models import Subject, Topic
from questions.models import Question


class QuestionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method="filter_search",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search formulas, equations, or concepts...",
                "class": "w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 shadow-sm",
            }
        ),
    )
    subject = django_filters.ModelChoiceFilter(
        queryset=Subject.objects.filter(is_active=True),
        empty_label="All Subjects",
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )
    exam_type = django_filters.ChoiceFilter(
        choices=Question.ExamType.choices,
        empty_label="All Exam Types",
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )
    topic = django_filters.ModelChoiceFilter(
        queryset=Topic.objects.all(),
        empty_label="All Topics",
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )
    has_image = django_filters.BooleanFilter(
        widget=forms.Select(
            choices=[
                ("", "All Questions"),
                ("true", "With Diagrams Only"),
                ("false", "Without Diagrams"),
            ],
            attrs={
                "class": "w-full px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )
    has_explanation = django_filters.BooleanFilter(
        method="filter_has_explanation",
        widget=forms.Select(
            choices=[
                ("", "All Questions"),
                ("true", "With Step-by-Step Solutions"),
                ("false", "Without Solutions"),
            ],
            attrs={
                "class": "w-full px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )

    class Meta:
        model = Question
        fields = ["search", "subject", "exam_type", "topic", "has_image", "has_explanation"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(question_text__icontains=value) |
            Q(explanation__icontains=value) |
            Q(topic__name__icontains=value) |
            Q(options__text__icontains=value)
        ).distinct()

    def filter_has_explanation(self, queryset, name, value):
        if value is True:
            return queryset.exclude(explanation="")
        elif value is False:
            return queryset.filter(explanation="")
        return queryset
