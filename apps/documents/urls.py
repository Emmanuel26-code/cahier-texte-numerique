from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("importer/", views.importer, name="importer"),
]