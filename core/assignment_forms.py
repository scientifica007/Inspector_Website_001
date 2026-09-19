from django import forms

from .models import Assignment


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["title", "description"]
        labels = {
            "title": "عنوان التكليف",
            "description": "وصف/تعليمات التكليف",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class AssignmentObligationForm(forms.Form):
    scope_locked = forms.BooleanField(
        label="مقيد في النطاق",
        required=False,
    )
    completion_required = forms.BooleanField(
        label="مطلوب للإكمال",
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("scope_locked") and not cleaned.get("completion_required"):
            raise forms.ValidationError(
                "اختر «مقيد في النطاق» أو «مطلوب للإكمال» على الأقل."
            )
        return cleaned


class AssignmentRevocationForm(forms.Form):
    reason = forms.CharField(
        label="سبب الإلغاء",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
    )
