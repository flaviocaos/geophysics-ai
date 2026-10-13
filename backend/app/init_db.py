"""Bootstrap do banco para o MVP: habilita PostGIS, cria as tabelas, garante
a organização/usuário de desenvolvimento usados como dono padrão de todo
registro criado nesta fase do MVP (ver TODO em `routers/surveys.py`:
substituídos por organização/usuário autenticados via JWT na Fase 6) e
corrige a coluna `analysis_results.survey_id` para aceitar NULL (necessário
para os resultados de magnetic-rtp/anomaly-detection, que não são presos a
um levantamento — ver comentário em `models/analysis.py`).

`Base.metadata.create_all()` só cria tabelas que ainda não existem — não
altera colunas de uma tabela já criada em um deploy anterior. Por isso o
ALTER TABLE abaixo roda sempre, de forma idempotente (não dá erro se a
coluna já estiver nullable).

Uso: `python -m app.init_db`
Em produção (Fase 6), substituído por migrações versionadas com Alembic.
"""
from sqlalchemy import text

import app.models  # noqa: F401 — garante registro de todos os modelos
from app.database import Base, engine

# Precisam bater exatamente com _DEV_ORG_ID/_DEV_USER_ID em app/routers/surveys.py
_DEV_ORG_ID = "00000000-0000-0000-0000-000000000001"
_DEV_USER_ID = "00000000-0000-0000-0000-000000000002"


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE analysis_results ALTER COLUMN survey_id DROP NOT NULL"))

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO organizations (id, name, plan) "
                "VALUES (:id, :name, :plan) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": _DEV_ORG_ID, "name": "Organização de Desenvolvimento (MVP)", "plan": "trial"},
        )
        conn.execute(
            text(
                "INSERT INTO users (id, org_id, email, hashed_password, role) "
                "VALUES (:id, :org_id, :email, :hashed_password, :role) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {
                "id": _DEV_USER_ID,
                "org_id": _DEV_ORG_ID,
                "email": "dev@geophysics-ai.local",
                "hashed_password": "dev-placeholder-not-a-real-hash",
                "role": "analista",
            },
        )

    print(
        "Banco inicializado: extensao PostGIS habilitada, tabelas criadas, "
        "organizacao/usuario de desenvolvimento garantidos, "
        "analysis_results.survey_id tornado nullable."
    )


if __name__ == "__main__":
    main()
