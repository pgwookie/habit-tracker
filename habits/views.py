from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from zoneinfo import ZoneInfo
from users.models import Profile

from .forms import HabitForm
from .models import Habit, HabitLog


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
    return render(request, "habits/habit_detail.html", {"habit": habit})


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
def habit_detail(request, pk: int):
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)

    schedule_summary = habit.schedule_summary()
    next_date = habit.next_scheduled_date()

    goal_summary = None
    if habit.target_value:
        goal_summary = f"{habit.target_value} {habit.target_unit}"

    return render(
        request,
        "habits/habit_detail.html",
        {
            "habit": habit,
            "schedule_summary": schedule_summary,
            "next_date": next_date,
            "goal_summary": goal_summary,
        },
    )

def user_today(user):
    profile = Profile.objects.filter(user=user).first()
    tz_name = profile.timezone if profile and profile.timezone else "Europe/Moscow"
    return timezone.now().astimezone(ZoneInfo(tz_name)).date()

@login_required
def habit_toggle_today(request, pk: int):
    if request.method != "POST":
        raise Http404

    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    today = user_today(request.user)

    log = HabitLog.objects.filter(habit=habit, date=today).first()
    if log:
        log.delete()  # снять отметку
        messages.success(request, _("Marked as not done for today."))
    else:
        HabitLog.objects.create(habit=habit, date=today, is_done=True)
        messages.success(request, _("Marked as done for today."))

    return redirect("habit_detail", pk=habit.pk)
