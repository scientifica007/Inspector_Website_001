from django import forms

from .models import (
    FieldType,
    Institution,
    InstitutionVerificationStatus,
    ProposalType,
)

class LocalNodeForm(forms.Form):
    title = forms.CharField(label="عنوان الفرع", max_length=255)
    description = forms.CharField(
        label="الوصف", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    inspectable = forms.BooleanField(label="قابل للتفتيش مباشرة", required=False, initial=True)

class LocalSpecificationForm(forms.Form):
    title = forms.CharField(label="عنوان الوصف", max_length=255)
    field_type = forms.ChoiceField(label="نوع القيمة", choices=FieldType.choices)
    required = forms.BooleanField(label="إلزامية", required=False)
    options_text = forms.CharField(
        label="الخيارات",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "خيار 1\nخيار 2"}),
        help_text="سطر واحد لكل خيار في حقول الاختيار.",
    )
    help_text = forms.CharField(
        label="شرح/مساعدة", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def clean(self):
        cleaned = super().clean()
        field_type = cleaned.get("field_type")
        options = [
            line.strip()
            for line in (cleaned.get("options_text") or "").splitlines()
            if line.strip()
        ]
        if field_type in {FieldType.SINGLE_SELECT, FieldType.MULTI_SELECT} and not options:
            self.add_error("options_text", "أضف خيارًا واحدًا على الأقل.")
        cleaned["options"] = options
        return cleaned

class LocalItemForm(forms.Form):
    title = forms.CharField(label="عنوان البند", max_length=500)
    guidance = forms.CharField(
        label="توجيه/شرح", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

class ProposalModerationForm(forms.Form):
    resolution_note = forms.CharField(
        label="ملاحظة القرار",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, proposal, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal = proposal
        payload = proposal.payload or {}

        if proposal.proposal_type == ProposalType.INSTITUTION:
            self.fields["name"] = forms.CharField(
                label="اسم المؤسسة", max_length=255, initial=payload.get("name", "")
            )
            self.fields["institution_type"] = forms.CharField(
                label="نوع المؤسسة", max_length=120, required=False,
                initial=payload.get("institution_type", "")
            )
            self.fields["commune"] = forms.CharField(
                label="البلدية", max_length=120, required=False,
                initial=payload.get("commune", "")
            )
            local_id = payload.get("institution_id")
            self.fields["merge_target"] = forms.ModelChoiceField(
                label="دمج مع مؤسسة معتمدة",
                required=False,
                queryset=Institution.objects.filter(
                    active=True,
                    verification_status=InstitutionVerificationStatus.VERIFIED,
                ).exclude(pk=local_id),
            )

        elif proposal.proposal_type == ProposalType.NODE:
            self.fields["title"] = forms.CharField(
                label="العنوان", max_length=255, initial=payload.get("title", "")
            )
            self.fields["description"] = forms.CharField(
                label="الوصف", required=False,
                initial=payload.get("description", ""),
                widget=forms.Textarea(attrs={"rows": 3}),
            )
            self.fields["inspectable"] = forms.BooleanField(
                label="قابل للتفتيش مباشرة",
                required=False,
                initial=payload.get("inspectable", True),
            )
            self.fields["sort_order"] = forms.IntegerField(
                label="الترتيب", min_value=0, initial=payload.get("sort_order", 0)
            )

        elif proposal.proposal_type == ProposalType.SPECIFICATION:
            self.fields["title"] = forms.CharField(
                label="العنوان", max_length=255, initial=payload.get("title", "")
            )
            self.fields["field_type"] = forms.ChoiceField(
                label="نوع القيمة",
                choices=FieldType.choices,
                initial=payload.get("field_type", FieldType.SHORT_TEXT),
            )
            self.fields["required"] = forms.BooleanField(
                label="إلزامية", required=False, initial=payload.get("required", False)
            )
            self.fields["options_text"] = forms.CharField(
                label="الخيارات",
                required=False,
                initial="\n".join(payload.get("options", [])),
                widget=forms.Textarea(attrs={"rows": 4}),
            )
            self.fields["help_text"] = forms.CharField(
                label="شرح/مساعدة",
                required=False,
                initial=payload.get("help_text", ""),
                widget=forms.Textarea(attrs={"rows": 3}),
            )
            self.fields["sort_order"] = forms.IntegerField(
                label="الترتيب", min_value=0, initial=payload.get("sort_order", 0)
            )

        elif proposal.proposal_type == ProposalType.ITEM:
            self.fields["title"] = forms.CharField(
                label="العنوان", max_length=500, initial=payload.get("title", "")
            )
            self.fields["guidance"] = forms.CharField(
                label="توجيه/شرح",
                required=False,
                initial=payload.get("guidance", ""),
                widget=forms.Textarea(attrs={"rows": 3}),
            )
            self.fields["sort_order"] = forms.IntegerField(
                label="الترتيب", min_value=0, initial=payload.get("sort_order", 0)
            )

    def clean(self):
        cleaned = super().clean()
        if self.proposal.proposal_type == ProposalType.SPECIFICATION:
            options = [
                line.strip()
                for line in (cleaned.get("options_text") or "").splitlines()
                if line.strip()
            ]
            if cleaned.get("field_type") in {
                FieldType.SINGLE_SELECT,
                FieldType.MULTI_SELECT,
            } and not options:
                self.add_error("options_text", "أضف خيارًا واحدًا على الأقل.")
            cleaned["options"] = options
        return cleaned

    def updated_payload(self):
        payload = dict(self.proposal.payload or {})
        if self.proposal.proposal_type == ProposalType.INSTITUTION:
            payload.update({
                "name": self.cleaned_data["name"].strip(),
                "institution_type": self.cleaned_data["institution_type"].strip(),
                "commune": self.cleaned_data["commune"].strip(),
            })
        elif self.proposal.proposal_type == ProposalType.NODE:
            payload.update({
                "title": self.cleaned_data["title"].strip(),
                "description": self.cleaned_data["description"].strip(),
                "inspectable": self.cleaned_data["inspectable"],
                "sort_order": self.cleaned_data["sort_order"],
            })
        elif self.proposal.proposal_type == ProposalType.SPECIFICATION:
            payload.update({
                "title": self.cleaned_data["title"].strip(),
                "field_type": self.cleaned_data["field_type"],
                "required": self.cleaned_data["required"],
                "options": self.cleaned_data["options"],
                "help_text": self.cleaned_data["help_text"].strip(),
                "sort_order": self.cleaned_data["sort_order"],
            })
        elif self.proposal.proposal_type == ProposalType.ITEM:
            payload.update({
                "title": self.cleaned_data["title"].strip(),
                "guidance": self.cleaned_data["guidance"].strip(),
                "sort_order": self.cleaned_data["sort_order"],
            })
        return payload

class PublishConfirmationForm(forms.Form):
    confirm = forms.BooleanField(
        label="أؤكد نشر هذه المسودة وإغلاقها أمام التعديل.",
        required=True,
    )
