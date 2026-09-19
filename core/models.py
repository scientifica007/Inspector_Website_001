import uuid

from django.conf import settings
from django.db import models

class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    INSPECTOR = "INSPECTOR", "Inspector"

class InspectionStatus(models.TextChoices):
    DRAFT = "DRAFT", "مسودة"
    COMPLETED = "COMPLETED", "مكتملة"

class ResultStatus(models.TextChoices):
    UNCHECKED = "UNCHECKED", "غير مفحوص"
    NOT_APPLICABLE = "NOT_APPLICABLE", "غير معني"
    COMPLIANT = "COMPLIANT", "مطابق"
    OBSERVATION = "OBSERVATION", "ملاحظة"
    NON_COMPLIANT = "NON_COMPLIANT", "غير مطابق"

class MasterStatus(models.TextChoices):
    # Legacy metadata retained during A-C3 migration. New behavior must not
    # use this field to choose or supersede inspection references.
    DRAFT = "DRAFT", "مسودة قديمة"
    PUBLISHED = "PUBLISHED", "منشور قديم"
    ARCHIVED = "ARCHIVED", "مؤرشف قديم"


class ReferenceVisibility(models.TextChoices):
    SHARED = "SHARED", "مشترك"
    PRIVATE = "PRIVATE", "خاص"
    SNAPSHOT = "SNAPSHOT", "لقطة زيارة داخلية"

class ReferenceSubmissionStatus(models.TextChoices):
    PENDING = "PENDING", "قيد المراجعة"
    APPROVED = "APPROVED", "معتمد"
    REJECTED = "REJECTED", "مرفوض"
    WITHDRAWN = "WITHDRAWN", "مسحوب"


class ProposalStatus(models.TextChoices):
    PENDING = "PENDING", "قيد المراجعة"
    APPROVED = "APPROVED", "معتمد"
    REJECTED = "REJECTED", "مرفوض"
    MERGED = "MERGED", "مدمج"
    WITHDRAWN = "WITHDRAWN", "مسحوب"

class ProposalType(models.TextChoices):
    INSTITUTION = "INSTITUTION", "مؤسسة"
    NODE = "NODE", "عنصر هيكلي"
    SPECIFICATION = "SPECIFICATION", "وصف"
    ITEM = "ITEM", "بند"

class InstitutionVerificationStatus(models.TextChoices):
    PENDING = "PENDING", "قيد المراجعة"
    VERIFIED = "VERIFIED", "معتمدة"
    REJECTED = "REJECTED", "مرفوضة"

class FieldType(models.TextChoices):
    SHORT_TEXT = "SHORT_TEXT", "نص قصير"
    LONG_TEXT = "LONG_TEXT", "نص طويل"
    NUMBER = "NUMBER", "عدد"
    DATE = "DATE", "تاريخ"
    BOOLEAN = "BOOLEAN", "نعم/لا"
    SINGLE_SELECT = "SINGLE_SELECT", "اختيار واحد"
    MULTI_SELECT = "MULTI_SELECT", "اختيار متعدد"

class InspectionScopeMode(models.TextChoices):
    LEGACY_FULL = "LEGACY_FULL", "نطاق تاريخي كامل"
    SELECTIVE = "SELECTIVE", "نطاق انتقائي"

class ScopeOrigin(models.TextChoices):
    LEGACY = "LEGACY", "تاريخي"
    MANUAL = "MANUAL", "اختيار المفتش"
    GUIDE = "GUIDE", "دليل مقترح"
    ASSIGNMENT = "ASSIGNMENT", "تكليف"
    LOCAL = "LOCAL", "إضافة محلية"

class ScopeState(models.TextChoices):
    ACTIVE = "ACTIVE", "ضمن النطاق"
    EXCLUDED = "EXCLUDED", "مستبعد"

class ScopeRole(models.TextChoices):
    SELECTED = "SELECTED", "مختار"
    CONTEXT = "CONTEXT", "سياق بنيوي"

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.INSPECTOR)

    def __str__(self):
        return f"{self.user} ({self.role})"

class Institution(models.Model):
    name = models.CharField(max_length=255)
    institution_type = models.CharField(max_length=120, blank=True)
    commune = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)
    verification_status = models.CharField(
        max_length=16,
        choices=InstitutionVerificationStatus.choices,
        default=InstitutionVerificationStatus.VERIFIED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="institutions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

class MasterVersion(models.Model):
    """
    Internal legacy class name retained during A-C3 to keep the database
    migration conservative. Product semantics are now an independent
    inspection reference, not a superseding version.
    """

    number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    visibility = models.CharField(
        max_length=16,
        choices=ReferenceVisibility.choices,
        default=ReferenceVisibility.SHARED,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_references",
    )
    status = models.CharField(max_length=16, choices=MasterStatus.choices, default=MasterStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

class StructureNode(models.Model):
    stable_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    master_version = models.ForeignKey(MasterVersion, on_delete=models.CASCADE, related_name="nodes")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    inspectable = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

class SpecificationDefinition(models.Model):
    stable_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    node = models.ForeignKey(StructureNode, on_delete=models.CASCADE, related_name="specifications")
    title = models.CharField(max_length=255)
    field_type = models.CharField(max_length=24, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    help_text = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

class ChecklistItem(models.Model):
    stable_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    node = models.ForeignKey(StructureNode, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=500)
    guidance = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

class Inspection(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="inspections")
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inspections")
    master_version = models.ForeignKey(
        MasterVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspections",
    )
    source_reference = models.ForeignKey(
        MasterVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_inspections",
    )
    reference_name_snapshot = models.CharField(max_length=255, blank=True)
    visit_date = models.DateField()
    status = models.CharField(max_length=16, choices=InspectionStatus.choices, default=InspectionStatus.DRAFT)
    scope_mode = models.CharField(
        max_length=16,
        choices=InspectionScopeMode.choices,
        default=InspectionScopeMode.SELECTIVE,
    )
    general_observations = models.TextField(blank=True)
    general_recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-visit_date", "-id"]

class InspectionNode(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="inspection_nodes")
    source_node = models.ForeignKey(StructureNode, null=True, blank=True, on_delete=models.SET_NULL)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    title_snapshot = models.CharField(max_length=255)
    description_snapshot = models.TextField(blank=True)
    inspectable_snapshot = models.BooleanField(default=True)
    sort_order_snapshot = models.PositiveIntegerField(default=0)
    scope_origin = models.CharField(
        max_length=16,
        choices=ScopeOrigin.choices,
        default=ScopeOrigin.MANUAL,
    )
    scope_state = models.CharField(
        max_length=16,
        choices=ScopeState.choices,
        default=ScopeState.ACTIVE,
    )
    scope_role = models.CharField(
        max_length=16,
        choices=ScopeRole.choices,
        default=ScopeRole.SELECTED,
    )
    scope_locked = models.BooleanField(default=False)
    additional_observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "source_node"],
                condition=models.Q(source_node__isnull=False),
                name="uq_inspection_source_node",
            ),
        ]

class SpecificationValue(models.Model):
    inspection_node = models.ForeignKey(
        InspectionNode, on_delete=models.CASCADE, related_name="specification_values"
    )
    source_specification = models.ForeignKey(
        SpecificationDefinition, null=True, blank=True, on_delete=models.SET_NULL
    )
    title_snapshot = models.CharField(max_length=255)
    field_type_snapshot = models.CharField(max_length=24, choices=FieldType.choices)
    required_snapshot = models.BooleanField(default=False)
    options_snapshot = models.JSONField(default=list, blank=True)
    help_text_snapshot = models.TextField(blank=True)
    value = models.JSONField(null=True, blank=True)
    sort_order_snapshot = models.PositiveIntegerField(default=0)
    scope_origin = models.CharField(
        max_length=16,
        choices=ScopeOrigin.choices,
        default=ScopeOrigin.MANUAL,
    )
    scope_state = models.CharField(
        max_length=16,
        choices=ScopeState.choices,
        default=ScopeState.ACTIVE,
    )
    scope_locked = models.BooleanField(default=False)
    completion_required = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["inspection_node", "source_specification"],
                condition=models.Q(source_specification__isnull=False),
                name="uq_inspection_node_source_spec",
            ),
        ]

class InspectionItemResult(models.Model):
    inspection_node = models.ForeignKey(InspectionNode, on_delete=models.CASCADE, related_name="item_results")
    source_item = models.ForeignKey(ChecklistItem, null=True, blank=True, on_delete=models.SET_NULL)
    title_snapshot = models.CharField(max_length=500)
    guidance_snapshot = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=ResultStatus.choices, default=ResultStatus.UNCHECKED)
    observation = models.TextField(blank=True)
    sort_order_snapshot = models.PositiveIntegerField(default=0)
    scope_origin = models.CharField(
        max_length=16,
        choices=ScopeOrigin.choices,
        default=ScopeOrigin.MANUAL,
    )
    scope_state = models.CharField(
        max_length=16,
        choices=ScopeState.choices,
        default=ScopeState.ACTIVE,
    )
    scope_locked = models.BooleanField(default=False)
    completion_required = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["inspection_node", "source_item"],
                condition=models.Q(source_item__isnull=False),
                name="uq_inspection_node_source_item",
            ),
        ]

class Proposal(models.Model):
    proposal_type = models.CharField(max_length=24, choices=ProposalType.choices)
    source_inspection = models.ForeignKey(
        Inspection, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposals"
    )
    source_local_id = models.PositiveBigIntegerField(null=True, blank=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="proposals"
    )
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.PENDING)
    resolution_note = models.TextField(blank=True)
    resolution_data = models.JSONField(default=dict, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proposals_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReferenceSubmission(models.Model):
    source_reference = models.ForeignKey(
        MasterVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reference_submissions",
    )
    source_name_snapshot = models.CharField(max_length=255)
    snapshot = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16,
        choices=ReferenceSubmissionStatus.choices,
        default=ReferenceSubmissionStatus.PENDING,
    )
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reference_submissions_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resulting_reference = models.ForeignKey(
        MasterVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="originating_submissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
