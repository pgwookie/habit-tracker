from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import Profile

from .forms import HabitForm
from .models import Habit, HabitLog


PRIORITY_ORDER = {
    Habit.Priority.HIGH: 0,
    Habit.Priority.MEDIUM: 1,
    Habit.Priority.LOW: 2,
}


def get_user_timezone(user):
    profile = Profile.objects.filter(user=user).only("timezone").first()
    tz_name = (profile.timezone if profile and profile.timezone else "") or getattr(settings, "TIME_ZONE", "UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(getattr(settings, "TIME_ZONE", "UTC"))


def user_today(user):
    return timezone.now().astimezone(get_user_timezone(user)).date()


def week_bounds(target_date):
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def done_dates_for_habit(habit, start_date=None, end_date=None):
    qs = HabitLog.objects.filter(habit=habit, is_done=True)
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    return set(qs.values_list("date", flat=True))


def is_habit_scheduled_for_date(habit, target_date, done_dates=None):
    if habit.is_archived or target_date < habit.start_date:
        return False

    frequency_type = habit.frequency_type

    if frequency_type == Habit.FrequencyType.DAILY:
        return True

    if frequency_type == Habit.FrequencyType.WEEKDAYS:
        return target_date.weekday() in (habit.weekdays or [])

    if frequency_type == Habit.FrequencyType.INTERVAL:
        step = max(1, habit.interval_days)
        return (target_date - habit.start_date).days % step == 0

    if frequency_type == Habit.FrequencyType.WEEKLY_TIMES:
        done_dates = done_dates or set()
        week_start, _ = week_bounds(target_date)
        active_start = max(week_start, habit.start_date)
        completed_before_day = sum(1 for day in done_dates if active_start <= day < target_date)
        return completed_before_day < max(1, habit.weekly_times)

    return False


def expected_completions_in_period(habit, start_date, end_date):
    if end_date < habit.start_date:
        return 0

    start_date = max(start_date, habit.start_date)
    if start_date > end_date:
        return 0

    if habit.frequency_type == Habit.FrequencyType.WEEKLY_TIMES:
        total = 0
        cursor = start_date - timedelta(days=start_date.weekday())
        while cursor <= end_date:
            week_start = cursor
            week_end = cursor + timedelta(days=6)
            active_start = max(start_date, habit.start_date, week_start)
            active_end = min(end_date, week_end)
            if active_start <= active_end:
                active_days = (active_end - active_start).days + 1
                total += min(max(1, habit.weekly_times), active_days)
            cursor += timedelta(days=7)
        return total

    total = 0
    cursor = start_date
    while cursor <= end_date:
        if is_habit_scheduled_for_date(habit, cursor):
            total += 1
        cursor += timedelta(days=1)
    return total


def build_period_stats(habit, done_dates, today, days):
    start_date = today - timedelta(days=days - 1)
    done_count = sum(1 for day in done_dates if start_date <= day <= today)
    expected_count = expected_completions_in_period(habit, start_date, today)
    percent = round((done_count / expected_count) * 100) if expected_count else 0
    return {
        "days": days,
        "done_count": done_count,
        "expected_count": expected_count,
        "percent": percent,
    }


def build_history_rows(habit, today, done_dates, days):
    start_date = today - timedelta(days=days - 1)
    rows = []
    cursor = start_date

    while cursor <= today:
        is_done = cursor in done_dates
        is_scheduled = is_habit_scheduled_for_date(habit, cursor, done_dates=done_dates)

        if is_done:
            badge_class = "success"
            status_label = _("Done")
        elif is_scheduled:
            badge_class = "warning"
            status_label = _("Missed")
        else:
            badge_class = "secondary"
            status_label = _("Not scheduled")

        rows.append(
            {
                "date": cursor,
                "is_done": is_done,
                "is_scheduled": is_scheduled,
                "badge_class": badge_class,
                "status_label": status_label,
            }
        )
        cursor += timedelta(days=1)

    return rows


@login_required
def habit_list(request):
    status = request.GET.get("status", "active")  # active|archived|all

    qs = Habit.objects.filter(owner=request.user)
    if status == "archived":
        qs = qs.filter(is_archived=True)
    elif status == "all":
        pass
    else:
        qs = qs.filter(is_archived=False)

    return render(request, "habits/habit_list.html", {"habits": qs, "status": status})


@login_required
def habit_create(request):
    if request.method == "POST":
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.owner = request.user
            habit.save()
            messages.success(request, _("Habit created."))
            return redirect("habit_list")
    else:
        form = HabitForm()

    return render(request, "habits/habit_form.html", {"form": form, "mode": "create"})


@login_required
def habit_update(request, pk: int):
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)

    if request.method == "POST":
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, _("Habit updated."))
            return redirect("habit_detail", pk=habit.pk)
    else:
        form = HabitForm(instance=habit)

    return render(request, "habits/habit_form.html", {"form": form, "mode": "edit", "habit": habit})


@login_required
def habit_detail(request, pk: int):
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    today = user_today(request.user)
    history_start = today - timedelta(days=35)
    done_dates = done_dates_for_habit(habit, start_date=history_start, end_date=today)

    goal_summary = None
    if habit.target_value:
        goal_summary = f"{habit.target_value} {habit.get_target_unit_display()}"

    context = {
        "habit": habit,
        "today": today,
        "is_done_today": today in done_dates,
        "schedule_summary": habit.schedule_summary(),
        "next_date": habit.next_scheduled_date(from_date=today),
        "goal_summary": goal_summary,
        "stats_7": build_period_stats(habit, done_dates, today, 7),
        "stats_30": build_period_stats(habit, done_dates, today, 30),
        "history_14": build_history_rows(habit, today, done_dates, 14),
        "history_30": build_history_rows(habit, today, done_dates, 30),
    }
    return render(request, "habits/habit_detail.html", context)


@login_required
def habit_archive(request, pk: int):
    if request.method != "POST":
        raise Http404

    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    habit.is_archived = True
    habit.save(update_fields=["is_archived"])
    messages.success(request, _("Habit archived."))
    return redirect("habit_list")


@login_required
def habit_unarchive(request, pk: int):
    if request.method != "POST":
        raise Http404

    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    habit.is_archived = False
    habit.save(update_fields=["is_archived"])
    messages.success(request, _("Habit restored."))
    return redirect("habit_list")


@login_required
def habit_delete(request, pk: int):
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)

    if request.method == "POST":
        habit.delete()
        messages.success(request, _("Habit deleted."))
        return redirect("habit_list")

    return render(request, "habits/habit_confirm_delete.html", {"habit": habit})


@login_required
def habit_today_view(request):
    today = user_today(request.user)
    habits = list(
        Habit.objects.filter(owner=request.user, is_archived=False, start_date__lte=today).order_by("title")
    )

    today_done_ids = set(
        HabitLog.objects.filter(habit__in=habits, date=today, is_done=True).values_list("habit_id", flat=True)
    )

    week_start, _ = week_bounds(today)
    weekly_done_counts = dict(
        HabitLog.objects.filter(habit__in=habits, date__range=(week_start, today), is_done=True)
        .values("habit_id")
        .annotate(total=Count("id"))
        .values_list("habit_id", "total")
    )

    habit_cards = []
    for habit in habits:
        is_done_today = habit.pk in today_done_ids

        if habit.frequency_type == Habit.FrequencyType.WEEKLY_TIMES:
            completed_before_today = weekly_done_counts.get(habit.pk, 0) - (1 if is_done_today else 0)
            is_due_today = is_done_today or completed_before_today < max(1, habit.weekly_times)
            week_progress = _("%(done)s of %(target)s this week") % {
                "done": weekly_done_counts.get(habit.pk, 0),
                "target": max(1, habit.weekly_times),
            }
        else:
            is_due_today = is_habit_scheduled_for_date(habit, today)
            week_progress = None

        if not (is_due_today or is_done_today):
            continue

        habit_cards.append(
            {
                "habit": habit,
                "is_done_today": is_done_today,
                "schedule_summary": habit.schedule_summary(),
                "week_progress": week_progress,
            }
        )

    habit_cards.sort(
        key=lambda item: (
            item["is_done_today"],
            PRIORITY_ORDER.get(item["habit"].priority, 99),
            item["habit"].title.lower(),
        )
    )

    done_count = sum(1 for item in habit_cards if item["is_done_today"])
    total_count = len(habit_cards)
    remaining_count = max(total_count - done_count, 0)
    completion_percent = round((done_count / total_count) * 100) if total_count else 0

    context = {
        "today": today,
        "habit_cards": habit_cards,
        "done_count": done_count,
        "total_count": total_count,
        "remaining_count": remaining_count,
        "completion_percent": completion_percent,
    }
    return render(request, "habits/habit_today.html", context)


@login_required
def habit_toggle_today(request, pk: int):
    if request.method != "POST":
        raise Http404

    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    if habit.is_archived:
        messages.warning(request, _("Archived habits cannot be updated."))
        return redirect("habit_detail", pk=habit.pk)

    today = user_today(request.user)

    log = HabitLog.objects.filter(habit=habit, date=today).first()
    if log:
        log.delete()
        messages.success(request, _("Marked as not done for today."))
    else:
        HabitLog.objects.create(habit=habit, date=today, is_done=True)
        messages.success(request, _("Marked as done for today."))

    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)

    return redirect(reverse("habit_detail", kwargs={"pk": habit.pk}))
