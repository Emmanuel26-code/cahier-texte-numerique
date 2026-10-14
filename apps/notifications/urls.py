from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("<int:pk>/lue/", views.marquer_lue, name="marquer_lue"),
    path("tout-lire/", views.tout_marquer_lu, name="tout_lire"),
]
