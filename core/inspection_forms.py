from django import forms

from .models import FieldType, Inspection, ResultStatus

class InspectionNodeEntryForm(forms.Form):
    def __init__(self, *args, node, readonly=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.node = node
        self.readonly = readonly
        self.spec_values = list(
            node.specification_values.all().order_by("sort_order_snapshot", "id")
        )
        self.item_results = list(
            node.item_results.all().order_by("sort_order_snapshot", "id")
        )

        for spec in self.spec_values:
            name = f"spec_{spec.id}"
            initial = spec.value
            common = {
                "label": spec.title_snapshot,
                "required": spec.required_snapshot,
                "help_text": spec.help_text_snapshot,
                "initial": initial,
                "disabled": readonly,
            }

            if spec.field_type_snapshot == FieldType.LONG_TEXT:
                field = forms.CharField(
                    **common, widget=forms.Textarea(attrs={"rows": 4})
                )
            elif spec.field_type_snapshot == FieldType.NUMBER:
                field = forms.FloatField(**common)
            elif spec.field_type_snapshot == FieldType.DATE:
                field = forms.DateField(
                    **common, widget=forms.DateInput(attrs={"type": "date"})
                )
            elif spec.field_type_snapshot == FieldType.BOOLEAN:
                if initial is True:
                    common["initial"] = "true"
                elif initial is False:
                    common["initial"] = "false"
                else:
                    common["initial"] = ""
                field = forms.ChoiceField(
                    **common,
                    choices=[("", "—"), ("true", "نعم"), ("false", "لا")],
                )
            elif spec.field_type_snapshot == FieldType.SINGLE_SELECT:
                field = forms.ChoiceField(
                    **common,
                    choices=[("", "—")] + [(x, x) for x in spec.options_snapshot],
                )
            elif spec.field_type_snapshot == FieldType.MULTI_SELECT:
                field = forms.MultipleChoiceField(
                    **common,
                    choices=[(x, x) for x in spec.options_snapshot],
                    widget=forms.CheckboxSelectMultiple,
                )
            else:
                field = forms.CharField(**common)

            self.fields[name] = field

        for item in self.item_results:
            self.fields[f"status_{item.id}"] = forms.ChoiceField(
                label=item.title_snapshot,
                choices=ResultStatus.choices,
                initial=item.status,
                disabled=readonly,
            )
            self.fields[f"observation_{item.id}"] = forms.CharField(
                label="المعاينة / الملاحظة",
                required=False,
                initial=item.observation,
                help_text=item.guidance_snapshot,
                widget=forms.Textarea(attrs={"rows": 3}),
                disabled=readonly,
            )

        self.fields["additional_observations"] = forms.CharField(
            label="معاينات إضافية",
            required=False,
            initial=node.additional_observations,
            widget=forms.Textarea(attrs={"rows": 4}),
            disabled=readonly,
        )
        self.fields["recommendations"] = forms.CharField(
            label="توصيات هذا المجال",
            required=False,
            initial=node.recommendations,
            widget=forms.Textarea(attrs={"rows": 4}),
            disabled=readonly,
        )

    @property
    def specification_blocks(self):
        return [
            {"snapshot": spec, "field": self[f"spec_{spec.id}"]}
            for spec in self.spec_values
        ]

    @property
    def item_blocks(self):
        return [
            {
                "result": item,
                "status": self[f"status_{item.id}"],
                "observation": self[f"observation_{item.id}"],
            }
            for item in self.item_results
        ]

    def _normalized_spec_value(self, spec):
        value = self.cleaned_data[f"spec_{spec.id}"]
        if spec.field_type_snapshot == FieldType.DATE:
            return value.isoformat() if value else None
        if spec.field_type_snapshot == FieldType.BOOLEAN:
            if value == "true":
                return True
            if value == "false":
                return False
            return None
        if spec.field_type_snapshot == FieldType.MULTI_SELECT:
            return list(value or [])
        if value == "":
            return None
        return value

    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save an invalid field form.")
        if self.readonly:
            raise ValueError("Cannot save a read-only field form.")

        for spec in self.spec_values:
            spec.value = self._normalized_spec_value(spec)
            spec.save(update_fields=["value"])

        for item in self.item_results:
            item.status = self.cleaned_data[f"status_{item.id}"]
            item.observation = self.cleaned_data[f"observation_{item.id}"]
            item.save(update_fields=["status", "observation"])

        self.node.additional_observations = self.cleaned_data["additional_observations"]
        self.node.recommendations = self.cleaned_data["recommendations"]
        self.node.save(update_fields=["additional_observations", "recommendations"])

class InspectionGeneralForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = ["general_observations", "general_recommendations"]
        labels = {
            "general_observations": "معاينات عامة حول المؤسسة / الزيارة",
            "general_recommendations": "توصيات عامة",
        }
        widgets = {
            "general_observations": forms.Textarea(attrs={"rows": 6}),
            "general_recommendations": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, readonly=False, **kwargs):
        super().__init__(*args, **kwargs)
        if readonly:
            for field in self.fields.values():
                field.disabled = True

class InspectionCompletionForm(forms.Form):
    confirm = forms.BooleanField(
        label="أؤكد أنني أريد إنهاء الزيارة وجعلها للقراءة فقط.",
        required=True,
    )
