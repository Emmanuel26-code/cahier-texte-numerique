"""Backend MySQL/MariaDB tolérant pour le développement avec XAMPP.

XAMPP fournit MariaDB 10.4, alors que Django 5.2 annonce exiger MariaDB 10.5+.
Pour le développement, on accepte MariaDB >= 10.4 ; toute autre version trop
ancienne reste refusée par Django.
Pour la production : utiliser MariaDB 10.5+ ou MySQL 8+ (voir README).
"""
from django.db.backends.mysql import base


class DatabaseWrapper(base.DatabaseWrapper):
    def check_database_version_supported(self):
        if self.mysql_is_mariadb and self.mysql_version >= (10, 4):
            return
        super().check_database_version_supported()
