from decimal import Decimal

from django import forms
from curriculum.models import Topic
from django.db.models import Sum

from .models import PaidTest, TeacherProfile, WithdrawalRequest

FIELD_CLASS = "w-full rounded-xl border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm px-4 py-2.5"


class TeacherApplicationForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ["kind", "display_name"]
        widgets = {
            "kind": forms.Select(attrs={"class": FIELD_CLASS}),
            "display_name": forms.TextInput(attrs={"class": FIELD_CLASS}),
        }


class TeacherInvitationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": FIELD_CLASS}))
    kind = forms.ChoiceField(choices=TeacherProfile.Kind.choices, widget=forms.Select(attrs={"class": FIELD_CLASS}))
    display_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))


class InvitationAccountForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={"class": FIELD_CLASS}))

    def clean_username(self):
        from django.contrib.auth import get_user_model

        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username


class PaidTestForm(forms.ModelForm):
    price_naira = forms.DecimalField(min_value=Decimal("200"), decimal_places=2, max_digits=10, label="Price (₦)")
    topics = forms.ModelMultipleChoiceField(queryset=Topic.objects.none(), widget=forms.CheckboxSelectMultiple)
    requires_approval = forms.BooleanField(
        required=False,
        initial=False,
        label="Exam Proctoring / Start Gate",
        help_text="Require teacher approval before students can begin. Students with valid PINs will wait in a live lobby.",
    )

    class Meta:
        model = PaidTest
        fields = [
            "title",
            "description",
            "topics",
            "price_naira",
            "question_count",
            "time_limit_minutes",
            "randomization",
            "requires_approval",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": FIELD_CLASS}),
            "description": forms.Textarea(attrs={"class": FIELD_CLASS, "rows": 3}),
            "question_count": forms.NumberInput(attrs={"class": FIELD_CLASS, "min": 1}),
            "time_limit_minutes": forms.NumberInput(attrs={"class": FIELD_CLASS, "min": 1}),
            "randomization": forms.Select(attrs={"class": FIELD_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topics"].queryset = Topic.objects.select_related("subject").order_by("subject__name", "order", "name")
        self.fields["topics"].label_from_instance = lambda topic: f"{topic.subject.name} — {topic.name}"

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.price_kobo = int(self.cleaned_data["price_naira"] * 100)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class TestCheckoutForm(forms.Form):
    name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": FIELD_CLASS}))
    phone = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={"class": FIELD_CLASS}))


class PinForm(forms.Form):
    pin = forms.RegexField(regex=r"^[A-Z0-9]{10}$", max_length=10, min_length=10, widget=forms.TextInput(attrs={"class": FIELD_CLASS, "autocomplete": "one-time-code"}))


class WithdrawalForm(forms.Form):
    amount_naira = forms.DecimalField(min_value=Decimal("1"), decimal_places=2, max_digits=12, label="Withdrawal amount (₦)")

    def __init__(self, *args, wallet, **kwargs):
        self.wallet = wallet
        super().__init__(*args, **kwargs)
        self.fields["amount_naira"].widget.attrs.update({"class": FIELD_CLASS, "min": "1", "step": "0.01"})

    def clean_amount_naira(self):
        amount = int(self.cleaned_data["amount_naira"] * 100)
        reserved = self.wallet.withdrawals.filter(
            status__in=[WithdrawalRequest.Status.REQUESTED, WithdrawalRequest.Status.APPROVED]
        ).aggregate(total=Sum("amount_kobo"))["total"] or 0
        if amount + reserved > self.wallet.balance_kobo:
            raise forms.ValidationError("This amount exceeds your available wallet balance.")
        return amount

