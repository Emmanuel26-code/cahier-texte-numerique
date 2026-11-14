from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm

from .models import Utilisateur


class CreationUtilisateurAdminForm(AdminUserCreationForm):
    """Création dans l'admin : l'e-mail sert d'identifiant, le nom d'utilisateur est généré."""

    class Meta(AdminUserCreationForm.Meta):
        model = Utilisateur
        fields = ("email", "first_name", "last_name", "role")


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    add_form = CreationUtilisateurAdminForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "role")}),
        ("Droits", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "usable_password", "password1", "password2"),
        }),
    )
    list_display = ("email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("last_name", "first_name", "email")
