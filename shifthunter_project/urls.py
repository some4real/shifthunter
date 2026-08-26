from django.urls import path

from shifthunter import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "api/shyftr/shifts",
        views.shifts_api,
        name="shifts_api",
    ),
    path(
        "api/preferences",
        views.preferences_api,
        name="preferences_api",
    ),
    path(
        "api/preferences/update",
        views.preferences_update_api,
        name="preferences_update_api",
    ),
    path(
    "api/push/subscribe",
    views.push_subscription_api,
    name="push_subscription_api",
),
]