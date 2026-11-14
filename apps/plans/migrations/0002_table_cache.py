"""Crée la table du cache Django (settings.CACHES) utilisée par le quota de générations IA.

Un cache en base est partagé entre tous les processus et toutes les fonctions
serverless : le quota horaire est donc respecté même avec plusieurs instances.
"""
from django.core.management import call_command
from django.db import migrations


def creer_table_cache(apps, schema_editor):
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(creer_table_cache, migrations.RunPython.noop),
    ]
