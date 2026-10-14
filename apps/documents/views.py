from django.contrib import messages
from django.shortcuts import redirect, render

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .forms import DocumentForm
from .models import Document

Role = Utilisateur.Role


@role_requis(Role.PROFESSEUR)
def importer(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "Document importé avec succès.")
            return redirect("documents:liste")
    else:
        form = DocumentForm()
    return render(request, "documents/importer.html", {"form": form})


@role_requis(Role.PROFESSEUR, Role.ADMINISTRATEUR)
def liste(request):
    documents = Document.objects.all()
    return render(request, "documents/liste.html", {"documents": documents})