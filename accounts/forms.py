from django import forms
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile
from curriculum.models import Subject

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Create a secure password", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Kalmin", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. O.", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )
    target_exam = forms.ChoiceField(
        choices=StudentProfile.TargetExam.choices,
        widget=forms.Select(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password"]
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Choose a username", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                target_exam=self.cleaned_data.get("target_exam", StudentProfile.TargetExam.UTME),
            )
        return user


class StudentProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"})
    )

    class Meta:
        model = StudentProfile
        fields = ["target_exam", "target_year", "target_score", "target_course", "phone_number"]
        widgets = {
            "target_exam": forms.Select(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
            "target_year": forms.NumberInput(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
            "target_score": forms.NumberInput(attrs={"class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
            "target_course": forms.TextInput(attrs={"placeholder": "e.g. Medicine, Computer Science", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "e.g. +234 801 234 5678", "class": "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"}),
        }
