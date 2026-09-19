from django import forms
from django.core.exceptions import ValidationError

from .models import Institution, Inspection, MasterVersion

class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ["name", "institution_type", "commune"]
        labels = {
            "name": "اسم المؤسسة",
            "institution_type": "نوع المؤسسة",
            "commune": "البلدية",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        query = Institution.objects.filter(name__iexact=name, active=True)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError("هذه المؤسسة موجودة مسبقًا.")
        return name

class InspectionCreateForm(forms.ModelForm):
    reference = forms.ModelChoiceField(
        label="مرجع الزيارة",
        queryset=MasterVersion.objects.none(),
        required=False,
        empty_label="بدء زيارة فارغة دون مرجع",
    )

    class Meta:
        model = Inspection
        fields = ["institution", "visit_date"]
        labels = {"institution": "المؤسسة", "visit_date": "تاريخ الزيارة"}
        widgets = {"visit_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, institutions=None, references=None, **kwargs):
        super().__init__(*args, **kwargs)
        if institutions is not None:
            self.fields["institution"].queryset = institutions
        if references is not None:
            self.fields["reference"].queryset = references
