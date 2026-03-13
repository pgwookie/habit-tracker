from django.urls import path
from . import views

urlpatterns = [
    path("", views.habit_list, name="habit_list"),
    path("new/", views.habit_create, name="habit_create"),
    path("<int:pk>/", views.habit_detail, name="habit_detail"),
    path("<int:pk>/edit/", views.habit_update, name="habit_update"),
    path("<int:pk>/archive/", views.habit_archive, name="habit_archive"),
    path("<int:pk>/unarchive/", views.habit_unarchive, name="habit_unarchive"),
    path("<int:pk>/delete/", views.habit_delete, name="habit_delete"),
    path("<int:pk>/", views.habit_detail, name="habit_detail"),
    path("<int:pk>/toggle-today/", views.habit_toggle_today, name="habit_toggle_today"),
]