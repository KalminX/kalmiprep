import django_filters
from django import forms
from django.db.models import Q
from core.cache_utils import get_cached_filter_choices
from curriculum.models import Subject, Topic
from questions.models import Question


class QuestionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method="filter_search",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search questions, topics, formulas...",
                "class": "w-full max-w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 shadow-sm box-border",
            }
        ),
    )
    subject = django_filters.ChoiceFilter(
        method="filter_subject",
        widget=forms.Select(
            attrs={
                "class": "w-full max-w-full truncate px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
                "onchange": "if (window.syncTopicOptions) { window.syncTopicOptions(this.value, ''); }",
            }
        ),
    )
    exam_type = django_filters.ChoiceFilter(
        choices=Question.ExamType.choices,
        empty_label="All Exam Types",
        widget=forms.Select(
            attrs={
                "class": "w-full max-w-full truncate px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
            }
        ),
    )
    exam = django_filters.CharFilter(
        field_name="exam_type",
        widget=forms.HiddenInput(),
    )
    topic = django_filters.ChoiceFilter(
        method="filter_topic",
        widget=forms.Select(
            attrs={
                "class": "w-full max-w-full truncate px-3 py-2 text-sm rounded-xl border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 shadow-sm",
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
        fields = ["search", "subject", "exam_type", "exam", "topic", "has_image", "has_explanation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices_data = get_cached_filter_choices()
        
        # Build subject choices supporting both slug and id, displaying clean slugs in select
        visible_subject_choices = [("", "All Subjects")]
        allowed_subject_choices = [("", "All Subjects")]
        for item in choices_data.get("subjects", []):
            if len(item) == 3:
                sid, slug, name = item
                visible_subject_choices.append((slug, name))
                allowed_subject_choices.append((slug, name))
                allowed_subject_choices.append((str(sid), name))
            else:
                sid, name = item
                visible_subject_choices.append((str(sid), name))
                allowed_subject_choices.append((str(sid), name))

        self.filters["subject"].extra["choices"] = allowed_subject_choices
        self.filters["subject"].field.widget.choices = visible_subject_choices

        # Build topic choices supporting both slug and id
        # Filter visible topic choices dynamically if a subject is selected
        selected_subject = None
        if self.data:
            selected_subject = self.data.get("subject")
            if selected_subject:
                selected_subject = str(selected_subject).strip()

        subject_display_name = ""
        if selected_subject:
            for item in choices_data.get("subjects", []):
                if str(item[0]) == selected_subject or (len(item) >= 2 and item[1] == selected_subject):
                    subject_display_name = item[2] if len(item) >= 3 else item[1]
                    break

        default_topic_label = f"All {subject_display_name} Topics" if subject_display_name else "All Topics"
        visible_topic_choices = [("", default_topic_label)]
        allowed_topic_choices = [("", default_topic_label), ("", "All Topics")]

        for item in choices_data.get("topics", []):
            tid = item[0]
            slug = item[1]
            name = item[2]
            sid = str(item[3]) if len(item) > 3 else ""
            sslug = str(item[4]) if len(item) > 4 else ""

            # Allowed choices include all for validation
            allowed_topic_choices.append((slug, name))
            allowed_topic_choices.append((str(tid), name))

            # If a subject is selected, only display topics belonging to that subject
            if selected_subject:
                if selected_subject == sid or selected_subject == sslug:
                    visible_topic_choices.append((slug, name))
            else:
                visible_topic_choices.append((slug, name))

        self.filters["topic"].extra["choices"] = allowed_topic_choices
        self.filters["topic"].field.widget.choices = visible_topic_choices

    def filter_subject(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(subject_id=int(val_str))
        return queryset.filter(subject__slug=val_str)

    def filter_topic(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(topic_id=int(val_str))
        return queryset.filter(topic__slug=val_str)

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        if not val:
            return queryset

        import re
        from django.db import connection

        is_postgres = connection.vendor == "postgresql"

        # 1. Check for specific 4-digit exam year query (e.g. "2018", "jamb 2012")
        year_filter = None
        for word in val.split():
            if word.isdigit() and len(word) == 4 and 1970 <= int(word) <= 2030:
                year_filter = int(word)
                break

        # 2. Try PostgreSQL Full-Text Search with ranking if on PostgreSQL
        fts_qs = None
        if is_postgres and len(val) >= 2:
            try:
                from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
                vector = (
                    SearchVector("question_text", weight="A") +
                    SearchVector("topic__name", weight="A") +
                    SearchVector("subject__name", weight="B") +
                    SearchVector("explanation", weight="C")
                )
                search_query = SearchQuery(val, search_type="websearch")
                candidate_qs = queryset.annotate(
                    search_vec=vector,
                    search_rank=SearchRank(vector, search_query)
                ).filter(search_vec=search_query)

                if year_filter:
                    candidate_qs = candidate_qs.filter(exam_year=year_filter)

                if candidate_qs.exists():
                    fts_qs = candidate_qs.order_by("-search_rank", "-exam_year", "question_number").distinct()
            except Exception:
                fts_qs = None

        if fts_qs is not None:
            return fts_qs

        # 3. Hybrid Tokenized Fallback:
        # Splits multi-word phrases and searches across question_text, explanation, topic, subject, and options.
        tokens = [t for t in re.split(r'\s+', val) if len(t) >= 1]
        if not tokens:
            return queryset

        combined_q = Q()
        for tok in tokens:
            token_q = (
                Q(question_text__icontains=tok) |
                Q(explanation__icontains=tok) |
                Q(topic__name__icontains=tok) |
                Q(subject__name__icontains=tok) |
                Q(options__text__icontains=tok)
            )
            if tok.isdigit() and len(tok) == 4:
                token_q |= Q(exam_year=int(tok))

            combined_q = (combined_q & token_q) if combined_q else token_q

        if year_filter and not any(t.isdigit() and int(t) == year_filter for t in tokens):
            combined_q &= Q(exam_year=year_filter)

        return queryset.filter(combined_q).distinct()

    def filter_has_explanation(self, queryset, name, value):
        if value is True:
            return queryset.exclude(explanation="")
        elif value is False:
            return queryset.filter(explanation="")
        return queryset
