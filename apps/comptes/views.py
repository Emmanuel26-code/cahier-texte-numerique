from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import InscriptionForm


def inscription(request):
    if request.user.is_authenticated:
        return redirect("accueil")

    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save() 
            login(request, utilisateur)  
            return redirect("accueil")
    else:
        form = InscriptionForm()

    return render(request, "comptes/inscription.html", {"form": form})