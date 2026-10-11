from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rôle", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Rôle", {"fields": ("email", "role")}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
