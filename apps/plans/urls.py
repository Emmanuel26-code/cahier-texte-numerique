from django.urls import path

from . import views

app_name = "plans"

urlpatterns = [
    path("documents/<int:document_id>/generer-plan/", views.generer_plan, name="generer_plan"),
]
