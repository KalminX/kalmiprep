import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from curriculum.models import Topic


class TeacherProfile(models.Model):
    class Kind(models.TextChoices):
        TUTOR = "TUTOR", "Tutor"
        LECTURE_HOUSE = "LECTURE_HOUSE", "Lecture house"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    display_name = models.CharField(max_length=150)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class TeacherInvitation(models.Model):
    """A single-use invitation; the raw token is only ever emailed to its recipient."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    kind = models.CharField(max_length=20, choices=TeacherProfile.Kind.choices)
    display_name = models.CharField(max_length=150)
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="teacher_invitations_sent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} — {self.get_kind_display()}"

    @property
    def is_usable(self):
        from django.utils import timezone

        return not self.accepted_at and not self.revoked_at and self.expires_at > timezone.now()


class PaidTest(models.Model):
    class Randomization(models.TextChoices):
        SHARED_SET = "SHARED_SET", "Same randomly selected questions; shuffled per student"
        UNIQUE_DRAW = "UNIQUE_DRAW", "Unique random draw per student"

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="tests")
    share_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    topics = models.ManyToManyField(Topic, related_name="paid_tests")
    price_kobo = models.PositiveBigIntegerField(validators=[MinValueValidator(20000)], help_text="Minimum price: ₦200")
    question_count = models.PositiveSmallIntegerField(default=20, validators=[MinValueValidator(1)])
    time_limit_minutes = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1)])
    randomization = models.CharField(max_length=20, choices=Randomization.choices, default=Randomization.SHARED_SET)
    fixed_question_ids = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    requires_approval = models.BooleanField(
        default=False,
        help_text="Require teacher approval to start the exam before students can begin",
    )
    is_approved_for_start = models.BooleanField(
        default=False,
        help_text="Teacher has approved students to start the exam",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def can_student_start(self):
        return not self.requires_approval or self.is_approved_for_start

    @property
    def price_naira(self):
        return Decimal(self.price_kobo) / Decimal("100")

class TeacherWallet(models.Model):
    teacher = models.OneToOneField(TeacherProfile, on_delete=models.CASCADE, related_name="wallet")
    balance_kobo = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.teacher}"

    @property
    def balance_naira(self):
        return Decimal(self.balance_kobo) / Decimal("100")


class TestPurchase(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending payment"
        PAID = "PAID", "Paid"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
        REFUNDED = "REFUNDED", "Refunded"
        FAILED = "FAILED", "Payment failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(PaidTest, on_delete=models.PROTECT, related_name="purchases")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.PROTECT, related_name="test_purchases")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="paid_test_purchases")
    buyer_name = models.CharField(max_length=150)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=30, blank=True)
    amount_kobo = models.PositiveBigIntegerField()
    teacher_share_kobo = models.PositiveBigIntegerField()
    platform_share_kobo = models.PositiveBigIntegerField()
    paystack_reference = models.CharField(max_length=100, unique=True)
    paystack_transaction_id = models.CharField(max_length=40, blank=True, null=True, unique=True)
    gateway_fee_kobo = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=22, choices=Status.choices, default=Status.PENDING, db_index=True)
    access_pin_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    refunded_kobo = models.PositiveBigIntegerField(default=0)
    practice_session = models.OneToOneField(
        "practice.PracticeSession", on_delete=models.SET_NULL, null=True, blank=True, related_name="test_purchase"
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test.title} — {self.buyer_name} ({self.status})"

    @property
    def amount_naira(self):
        return Decimal(self.amount_kobo) / Decimal("100")

    @property
    def teacher_share_naira(self):
        return Decimal(self.teacher_share_kobo) / Decimal("100")

    @property
    def platform_share_naira(self):
        return Decimal(self.platform_share_kobo) / Decimal("100")


class WalletEntry(models.Model):
    class Kind(models.TextChoices):
        TEST_SALE = "TEST_SALE", "Test sale"
        REFUND = "REFUND", "Refund adjustment"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal paid"

    wallet = models.ForeignKey(TeacherWallet, on_delete=models.PROTECT, related_name="entries")
    purchase = models.ForeignKey(TestPurchase, on_delete=models.PROTECT, null=True, blank=True, related_name="wallet_entries")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    amount_kobo = models.BigIntegerField(help_text="Signed amount in kobo")
    source_reference = models.CharField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["kind", "source_reference"], name="uniq_wallet_entry_source")]
        ordering = ["-created_at"]

    @property
    def amount_naira(self):
        return Decimal(abs(self.amount_kobo)) / Decimal("100")


class TestRefund(models.Model):
    purchase = models.ForeignKey(TestPurchase, on_delete=models.PROTECT, related_name="refunds")
    provider_reference = models.CharField(max_length=140, unique=True)
    amount_kobo = models.PositiveBigIntegerField()
    processed_at = models.DateTimeField(auto_now_add=True)


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved for manual processing"
        REJECTED = "REJECTED", "Rejected"
        PAID = "PAID", "Marked paid"

    wallet = models.ForeignKey(TeacherWallet, on_delete=models.PROTECT, related_name="withdrawals")
    amount_kobo = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def amount_naira(self):
        return Decimal(self.amount_kobo) / Decimal("100")

    @property
    def teacher_share_naira(self):
        return Decimal(self.teacher_share_kobo) / Decimal("100")

    @property
    def platform_share_naira(self):
        return Decimal(self.platform_share_kobo) / Decimal("100")


class WebhookReceipt(models.Model):
    event_name = models.CharField(max_length=80)
    payload_fingerprint = models.CharField(max_length=64, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_name}: {self.payload_fingerprint[:12]}"
