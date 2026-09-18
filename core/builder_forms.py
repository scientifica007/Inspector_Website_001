from django import forms
from django.core.exceptions import ValidationError

from .models import (
    ChecklistItem,
    FieldType,
    MasterStatus,
    SpecificationDefinition,
    StructureNode,
)
from .services import descendant_ids

class StructureNodeForm(forms.ModelForm):
    class Meta:
        model = StructureNode
        fields = ["title", "description", "inspectable", "parent", "sort_order", "active"]
        labels = {
            "title": "العنوان",
            "description": "الوصف",
            "inspectable": "قابل للتفتيش مباشرة",
            "parent": "العنصر الأب",
            "sort_order": "الترتيب",
            "active": "نشط",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, draft, **kwargs):
        super().__init__(*args, **kwargs)
        self.draft = draft
        if draft.status != MasterStatus.DRAFT:
            raise ValueError("يمكن تحرير النسخ المسودة فقط.")
        queryset = StructureNode.objects.filter(master_version=draft).order_by("sort_order", "id")
        if self.instance.pk:
            blocked = descendant_ids(self.instance) | {self.instance.pk}
            queryset = queryset.exclude(pk__in=blocked)
        self.fields["parent"].queryset = queryset
        self.fields["parent"].required = False

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        if parent and parent.master_version_id != self.draft.id:
            raise ValidationError("يجب أن يكون العنصر الأب ضمن المسودة نفسها.")
        if self.instance.pk and parent:
            if parent.pk == self.instance.pk or parent.pk in descendant_ids(self.instance):
                raise ValidationError("لا يمكن إنشاء دورة داخل الشجرة.")
        return parent

    def save(self, commit=True):
        node = super().save(commit=False)
        node.master_version = self.draft
        if commit:
            node.save()
        return node

class SpecificationDefinitionForm(forms.ModelForm):
    options_text = forms.CharField(
        label="الخيارات",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "خيار 1\nخيار 2"}),
        help_text="سطر واحد لكل خيار. يستخدم فقط في حقول الاختيار.",
    )

    class Meta:
        model = SpecificationDefinition
        fields = ["title", "field_type", "required", "help_text", "sort_order", "active"]
        labels = {
            "title": "عنوان المواصفة",
            "field_type": "نوع القيمة",
            "required": "إلزامية",
            "help_text": "شرح/مساعدة",
            "sort_order": "الترتيب",
            "active": "نشطة",
        }
        widgets = {"help_text": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, node, **kwargs):
        super().__init__(*args, **kwargs)
        self.node = node
        if node.master_version.status != MasterStatus.DRAFT:
            raise ValueError("يمكن تحرير النسخ المسودة فقط.")
        if self.instance.pk:
            self.fields["options_text"].initial = "\n".join(self.instance.options or [])

    def clean(self):
        cleaned = super().clean()
        field_type = cleaned.get("field_type")
        text = (cleaned.get("options_text") or "").strip()
        options = [line.strip() for line in text.splitlines() if line.strip()]
        if field_type in {FieldType.SINGLE_SELECT, FieldType.MULTI_SELECT} and not options:
            self.add_error("options_text", "أضف خيارًا واحدًا على الأقل لهذا النوع.")
        cleaned["_options"] = options
        return cleaned

    def save(self, commit=True):
        spec = super().save(commit=False)
        spec.node = self.node
        spec.options = self.cleaned_data.get("_options", [])
        if commit:
            spec.save()
        return spec

class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ["title", "guidance", "sort_order", "active"]
        labels = {
            "title": "عنوان البند",
            "guidance": "توجيه/شرح",
            "sort_order": "الترتيب",
            "active": "نشط",
        }
        widgets = {"guidance": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, node, **kwargs):
        super().__init__(*args, **kwargs)
        self.node = node
        if node.master_version.status != MasterStatus.DRAFT:
            raise ValueError("يمكن تحرير النسخ المسودة فقط.")

    def save(self, commit=True):
        item = super().save(commit=False)
        item.node = self.node
        if commit:
            item.save()
        return item
