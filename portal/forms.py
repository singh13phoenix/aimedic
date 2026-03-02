from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import AppointmentRequest, RefillRequest

class RoleLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
            field.widget.attrs.setdefault("placeholder", name.replace("_", " ").title())

class AppointmentRequestForm(forms.ModelForm):
    class Meta:
        model = AppointmentRequest
        fields = ["type", "preferred_time_1", "preferred_time_2", "reason_text"]
        widgets = {
            "preferred_time_1": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "preferred_time_2": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "reason_text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if name == "type":
                field.widget.attrs["class"] = (css + " form-select").strip()
            else:
                field.widget.attrs["class"] = (css + " form-control").strip()

class RefillRequestForm(forms.ModelForm):
    class Meta:
        model = RefillRequest
        fields = ["medication_name", "dosage", "frequency", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
