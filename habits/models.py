from datetime import date, timedelta
from math import ceil
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Habit(models.Model):
    # --- Choices ---
    class Category(models.TextChoices):
        HEALTH = "health", _("Health")
        STUDY = "study", _("Study")
        WORK = "work", _("Work")
        MINDFUL = "mindful", _("Mindfulness")
        HOME = "home", _("Home")
        OTHER = "other", _("Other")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

    class FrequencyType(models.TextChoices):
        DAILY = "daily", _("Daily")
        WEEKDAYS = "weekdays", _("Specific weekdays")
        INTERVAL = "interval", _("Every N days")
        WEEKLY_TIMES = "weekly_times", _("N times per week")

    class GoalUnit(models.TextChoices):
        TIMES = "times", _("times")
        MINUTES = "minutes", _("minutes")
        PAGES = "pages", _("pages")
        GLASSES = "glasses", _("glasses")
        KM = "km", _("km")

    # --- Base fields ---
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name=_("Owner"),
    )

    title = models.CharField(max_length=120, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name=_("Category"),
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priority"),
    )

    # optional emoji icon (e.g. 🔥, ✅)
    icon = models.CharField(max_length=8, blank=True, verbose_name=_("Icon (emoji)"))

    start_date = models.DateField(verbose_name=_("Start date"))
    is_archived = models.BooleanField(default=False, verbose_name=_("Archived"))

    # --- Schedule settings ---
    frequency_type = models.CharField(
        max_length=20,
        choices=FrequencyType.choices,
        default=FrequencyType.DAILY,
        verbose_name=_("Frequency"),
    )

    # For WEEKDAYS: list of integers [0..6] where 0=Mon ... 6=Sun
    weekdays = models.JSONField(default=list, blank=True, verbose_name=_("Weekdays"))

    # For INTERVAL: every N days
    interval_days = models.PositiveSmallIntegerField(default=1, verbose_name=_("Interval days"))

    # For WEEKLY_TIMES: N times per week (planning only; without logs it's informational)
    weekly_times = models.PositiveSmallIntegerField(default=3, verbose_name=_("Times per week"))

    # --- Goal settings ---
    target_value = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Target value"))
    target_unit = models.CharField(
        max_length=20,
        choices=GoalUnit.choices,
        default=GoalUnit.TIMES,
        verbose_name=_("Target unit"),
    )

    # --- Reminder settings (saving config only; sending later) ---
    reminder_enabled = models.BooleanField(default=False, verbose_name=_("Reminder enabled"))
    reminder_time = models.TimeField(null=True, blank=True, verbose_name=_("Reminder time"))

    # --- Visibility / notes ---
    is_public = models.BooleanField(default=False, verbose_name=_("Public"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.owner})"

    # ---------- helpers for displaying schedule ----------
    def weekdays_display(self) -> str:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days = sorted([d for d in (self.weekdays or []) if isinstance(d, int) and 0 <= d <= 6])
        if not days:
            return "-"
        return ", ".join(names[d] for d in days)

    def schedule_summary(self) -> str:
        if self.frequency_type == self.FrequencyType.DAILY:
            return "Daily"

        if self.frequency_type == self.FrequencyType.INTERVAL:
            step = max(1, self.interval_days)
            return f"Every {step} day(s)"

        if self.frequency_type == self.FrequencyType.WEEKLY_TIMES:
            n = max(1, self.weekly_times)
            return f"{n} time(s) per week"

        if self.frequency_type == self.FrequencyType.WEEKDAYS:
            days = self.weekdays_display()
            if days == "-":
                return "Specific weekdays (not set)"
            return f"On: {days}"

        return "Schedule"

    def next_scheduled_date(self, from_date: Optional[date] = None) -> date:
        """Returns next planned date (without considering completion logs)."""
        if from_date is None:
            from_date = date.today()

        d = max(from_date, self.start_date)

        if self.frequency_type == self.FrequencyType.DAILY:
            return d

        if self.frequency_type == self.FrequencyType.INTERVAL:
            step = max(1, self.interval_days)
            if d <= self.start_date:
                return self.start_date
            delta_days = (d - self.start_date).days
            # ceil(delta_days / step) without floats:
            k = (delta_days + step - 1) // step
            return self.start_date + timedelta(days=k * step)

        if self.frequency_type == self.FrequencyType.WEEKDAYS:
            allowed = sorted([x for x in (self.weekdays or []) if isinstance(x, int) and 0 <= x <= 6])
            if not allowed:
                return d
            for i in range(0, 14):  # search up to 2 weeks ahead
                cand = d + timedelta(days=i)
                if cand.weekday() in allowed:
                    return cand
            return d

        # WEEKLY_TIMES: without logs we can't know exact next "due" day -> show nearest
        return d


class HabitLog(models.Model):
    """Mark habit completion for a specific date (backend only for now)."""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    is_done = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["habit", "date"], name="uniq_habit_date"),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.habit.title} {self.date} done={self.is_done}"