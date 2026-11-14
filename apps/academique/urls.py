from django.urls import path

from . import views

app_name = "academique"

urlpatterns = [
    path("affectations/", views.affectations, name="affectations"),
    path("referentiels/", views.referentiels, name="referentiels"),
]
