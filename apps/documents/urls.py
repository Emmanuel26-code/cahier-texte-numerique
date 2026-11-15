from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("importer/", views.importer, name="importer"),
    path("<int:document_id>/telecharger/", views.telecharger, name="telecharger"),
    path("<int:document_id>/vu/", views.marquer_vu_document, name="marquer_vu"),
]