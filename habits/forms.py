from django import forms
from .models import Habit

WEEKDAY_CHOICES = [
    (0, "Mon"),
    (1, "Tue"),
    (2, "Wed"),
    (3, "Thu"),
    (4, "Fri"),
    (5, "Sat"),
    (6, "Sun"),
]


class HabitForm(forms.ModelForm):
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Weekdays",
    )

    class Meta:
        model = Habit
        fields = (
            "title",
            "description",
            "category",
            "priority",
            "icon",
            "start_date",
            "frequency_type",
            "weekdays",
            "interval_days",
            "weekly_times",
            "target_value",
            "target_unit",
            "is_public",
            "notes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            # важно: формат для type="date", чтобы дата не сбрасывалась
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # чтобы дата корректно отображалась и принималась в Python 3.9 + HTML date input
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]

        # initial weekdays from JSONField
        if self.instance and self.instance.pk:
            self.fields["weekdays"].initial = [str(x) for x in (self.instance.weekdays or [])]

        # bootstrap styling
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxSelectMultiple):
                pass
            elif isinstance(w, forms.CheckboxInput):
                w.attrs.update({"class": "form-check-input"})
            elif isinstance(w, forms.Select):
                w.attrs.update({"class": "form-select"})
            else:
                w.attrs.update({"class": "form-control"})

        self.fields["icon"].widget.attrs.update({"placeholder": "🙂 🔥 ✅"})
        self.fields["interval_days"].help_text = "Used for 'Every N days' schedule."
        self.fields["weekly_times"].help_text = "Used for 'N times per week' schedule."
        self.fields["target_value"].help_text = "Optional (e.g., 20 minutes)."

    def clean_weekdays(self):
        data = self.cleaned_data.get("weekdays", [])
        return [int(x) for x in data]

    def save(self, commit=True):
        obj: Habit = super().save(commit=False)
        obj.weekdays = self.cleaned_data.get("weekdays", [])
        if commit:
            obj.save()
        return obj