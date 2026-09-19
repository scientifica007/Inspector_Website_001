from django import forms


class PrivateReferenceCreateForm(forms.Form):
    name = forms.CharField(label="اسم المرجع الخاص", max_length=255)


class ReferenceCloneForm(forms.Form):
    name = forms.CharField(label="اسم النسخة الخاصة", max_length=255)


class ReferenceSubmissionReviewForm(forms.Form):
    shared_name = forms.CharField(label="اسم المرجع المشترك", max_length=255)
    resolution_note = forms.CharField(
        label="ملاحظة القرار",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
