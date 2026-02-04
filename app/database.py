"""Configuração do banco de dados SQLite."""
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./finance_manager.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Cria as tabelas no banco de dados e aplica migrações leves."""
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    """Executa migrações para manter compatibilidade com versões anteriores."""

    def _column_exists(conn, table: str, column: str) -> bool:
        result = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
        return any(row[1] == column for row in result)

    def _add_column(conn, table: str, column_sql: str) -> None:
        try:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column_sql}'))
            conn.commit()
        except Exception:
            conn.rollback()

    with engine.connect() as conn:
        if not _column_exists(conn, "card", "title"):
            _add_column(conn, "card", "title TEXT DEFAULT ''")
        if not _column_exists(conn, "card", "user_id"):
            _add_column(conn, "card", "user_id INTEGER")
        if not _column_exists(conn, "balance", "user_id"):
            _add_column(conn, "balance", "user_id INTEGER")


def get_session():
    """Generator de sessão para injeção de dependência."""
    with Session(engine) as session:
        yield session
