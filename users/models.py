from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    class Language(models.TextChoices):
        EN = "en", _("English")
        RU = "ru", _("Русский")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    full_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)

    timezone = models.CharField(max_length=64, blank=True, default="Europe/Moscow")
    language_preference = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.RU,
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user})"