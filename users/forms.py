from datetime import datetime, timezone as dt_timezone, timedelta
from zoneinfo import ZoneInfo

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})
            if name == "username":
                field.widget.attrs.update({"placeholder": "Логин"})
            if name == "email":
                field.widget.attrs.update({"placeholder": "Email"})


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["email"].widget.attrs.update({"class": "form-control"})


POPULAR_TIMEZONES = [
    ("Europe/Kaliningrad", "Калининград"),
    ("Europe/Moscow", "Москва"),
    ("Europe/Samara", "Самара"),
    ("Asia/Yekaterinburg", "Екатеринбург"),
    ("Asia/Novosibirsk", "Новосибирск"),
    ("Asia/Krasnoyarsk", "Красноярск"),
    ("Asia/Irkutsk", "Иркутск"),
    ("Asia/Yakutsk", "Якутск"),
    ("Asia/Vladivostok", "Владивосток"),
    ("Asia/Kamchatka", "Камчатка"),
    ("Europe/London", "Лондон"),
    ("Europe/Berlin", "Берлин"),
    ("America/New_York", "Нью-Йорк"),
    ("America/Chicago", "Чикаго"),
    ("America/Denver", "Денвер"),
    ("America/Los_Angeles", "Лос-Анджелес"),
]


def _fmt_utc_offset(offset: timedelta) -> str:
    if offset is None:
        offset = timedelta(0)
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def build_timezone_choices():
    now_utc = datetime.now(dt_timezone.utc)
    choices = []
    for tz_name, city in POPULAR_TIMEZONES:
        z = ZoneInfo(tz_name)
        local = now_utc.astimezone(z)
        offset_str = _fmt_utc_offset(local.utcoffset())
        time_str = local.strftime("%H:%M")
        label = f"{city} — {tz_name} ({offset_str}) · {time_str}"
        choices.append((tz_name, label))
    return choices


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("full_name", "bio", "timezone", "language_preference")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # красивые поля
        self.fields["full_name"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Имя для отображения"}
        )
        self.fields["bio"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Коротко о себе"}
        )

        # timezone как select с UTC+offset и текущим временем
        tz_choices = build_timezone_choices()
        self.fields["timezone"].widget = forms.Select(choices=tz_choices)
        self.fields["timezone"].widget.attrs.update({"class": "form-select"})

        self.fields["language_preference"].widget.attrs.update({"class": "form-select"})