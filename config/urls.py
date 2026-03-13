from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect


def home(request):
    if request.user.is_authenticated:
        return redirect("habit_list")
    return redirect("login")

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("users.urls")),
    path("habits/", include("habits.urls")),
    path("i18n/", include("django.conf.urls.i18n")),

]

