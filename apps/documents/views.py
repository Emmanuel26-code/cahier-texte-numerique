
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import DocumentForm
from .models import Document


@login_required
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


@login_required
def liste(request):
    documents = Document.objects.all()
    return render(request, "documents/liste.html", {"documents": documents})