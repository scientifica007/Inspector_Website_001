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
    DRAFT = "DRAFT", "مسودة"
    PUBLISHED = "PUBLISHED", "منشور"
    ARCHIVED = "ARCHIVED", "مؤرشف"

class ProposalStatus(models.TextChoices):
    PENDING = "PENDING", "قيد المراجعة"
    APPROVED = "APPROVED", "معتمد"
    REJECTED = "REJECTED", "مرفوض"
    MERGED = "MERGED", "مدمج"

class ProposalType(models.TextChoices):
    INSTITUTION = "INSTITUTION", "مؤسسة"
    NODE = "NODE", "عنصر هيكلي"
    SPECIFICATION = "SPECIFICATION", "مواصفة"
    ITEM = "ITEM", "بند"

class InstitutionVerificationStatus(models.TextChoices):
    PENDING = "PENDING", "قيد المراجعة"
    VERIFIED = "VERIFIED", "معتمدة"

class FieldType(models.TextChoices):
    SHORT_TEXT = "SHORT_TEXT", "نص قصير"
    LONG_TEXT = "LONG_TEXT", "نص طويل"
    NUMBER = "NUMBER", "عدد"
    DATE = "DATE", "تاريخ"
    BOOLEAN = "BOOLEAN", "نعم/لا"
    SINGLE_SELECT = "SINGLE_SELECT", "اختيار واحد"
    MULTI_SELECT = "MULTI_SELECT", "اختيار متعدد"

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
    number = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=16, choices=MasterStatus.choices, default=MasterStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"v{self.number} — {self.status}"

class StructureNode(models.Model):
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
    node = models.ForeignKey(StructureNode, on_delete=models.CASCADE, related_name="specifications")
    title = models.CharField(max_length=255)
    field_type = models.CharField(max_length=24, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    help_text = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

class ChecklistItem(models.Model):
    node = models.ForeignKey(StructureNode, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=500)
    guidance = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

class Inspection(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="inspections")
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inspections")
    master_version = models.ForeignKey(MasterVersion, on_delete=models.PROTECT, related_name="inspections")
    visit_date = models.DateField()
    status = models.CharField(max_length=16, choices=InspectionStatus.choices, default=InspectionStatus.DRAFT)
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
    sort_order_snapshot = models.PositiveIntegerField(default=0)
    local_addition = models.BooleanField(default=False)
    additional_observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

class SpecificationValue(models.Model):
    inspection_node = models.ForeignKey(
        InspectionNode, on_delete=models.CASCADE, related_name="specification_values"
    )
    source_specification = models.ForeignKey(
        SpecificationDefinition, null=True, blank=True, on_delete=models.SET_NULL
    )
    title_snapshot = models.CharField(max_length=255)
    field_type_snapshot = models.CharField(max_length=24, choices=FieldType.choices)
    value = models.JSONField(null=True, blank=True)
    local_addition = models.BooleanField(default=False)
    sort_order_snapshot = models.PositiveIntegerField(default=0)

class InspectionItemResult(models.Model):
    inspection_node = models.ForeignKey(InspectionNode, on_delete=models.CASCADE, related_name="item_results")
    source_item = models.ForeignKey(ChecklistItem, null=True, blank=True, on_delete=models.SET_NULL)
    title_snapshot = models.CharField(max_length=500)
    status = models.CharField(max_length=24, choices=ResultStatus.choices, default=ResultStatus.UNCHECKED)
    observation = models.TextField(blank=True)
    local_addition = models.BooleanField(default=False)
    sort_order_snapshot = models.PositiveIntegerField(default=0)

class Proposal(models.Model):
    proposal_type = models.CharField(max_length=24, choices=ProposalType.choices)
    source_inspection = models.ForeignKey(
        Inspection, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposals"
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="proposals"
    )
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.PENDING)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proposals_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
