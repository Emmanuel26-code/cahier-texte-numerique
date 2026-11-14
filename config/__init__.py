"""Pilote MySQL : on utilise mysqlclient s'il est installé, sinon PyMySQL (100 % Python).

PyMySQL s'installe partout sans compilateur C (Vercel, GitHub Actions, Windows),
alors que mysqlclient a besoin des bibliothèques MySQL du système.
"""
try:
    import MySQLdb  # noqa: F401  (mysqlclient)
except ImportError:
    try:
        import pymysql
    except ImportError:  # ni l'un ni l'autre : base PostgreSQL ou SQLite
        pass
    else:
        pymysql.version_info = (2, 2, 7, "final", 0)  # version minimale attendue par Django 5.2
        pymysql.install_as_MySQLdb()
