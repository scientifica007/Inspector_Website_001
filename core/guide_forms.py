from django import forms

from .models import Guide, MasterVersion, ReferenceVisibility


class GuideCreateForm(forms.ModelForm):
    class Meta:
        model = Guide
        fields = ["name", "description", "reference"]
        labels = {
            "name": "اسم الدليل",
            "description": "وصف الدليل",
            "reference": "المرجع المشترك",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reference"].queryset = MasterVersion.objects.filter(
            visibility=ReferenceVisibility.SHARED
        ).order_by("name", "id")


class GuideEditForm(forms.ModelForm):
    class Meta:
        model = Guide
        fields = ["name", "description"]
        labels = {
            "name": "اسم الدليل",
            "description": "وصف الدليل",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
