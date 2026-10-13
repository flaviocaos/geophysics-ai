"""Bootstrap do banco para o MVP: habilita PostGIS e cria as tabelas.

Uso: `python -m app.init_db`
Em produção (Fase 6), substituído por migrações versionadas com Alembic.
"""
from sqlalchemy import text

import app.models  # noqa: F401 — garante registro de todos os modelos
from app.database import Base, engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    Base.metadata.create_all(bind=engine)
    print("Banco inicializado: extensão PostGIS habilitada e tabelas criadas.")


if __name__ == "__main__":
    main()
