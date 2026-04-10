import json
import os
import uuid
from typing import Any

import duckdb
import pandas as pd
from cryptography.fernet import Fernet
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.data_source import DataSource, DataSourceType

# Encryption key derived from SECRET_KEY (first 32 url-safe base64 bytes)
import base64
_raw = settings.secret_key.encode()[:32].ljust(32, b"0")
_FERNET_KEY = base64.urlsafe_b64encode(_raw)
_fernet = Fernet(_FERNET_KEY)


def encrypt_config(config: dict) -> dict:
    plaintext = json.dumps(config).encode()
    return {"encrypted": _fernet.encrypt(plaintext).decode()}


def decrypt_config(stored: dict) -> dict:
    if "encrypted" in stored:
        return json.loads(_fernet.decrypt(stored["encrypted"].encode()))
    return stored  # legacy unencrypted (dev only)


class DataSourceManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        # In-memory schema cache: {(source_id, schema_hash): schema_dict}
        self._schema_cache: dict[tuple, dict] = {}

    async def list_sources(self) -> list[DataSource]:
        result = await self.db.execute(select(DataSource).order_by(DataSource.created_at))
        return list(result.scalars().all())

    async def get_source(self, source_id: uuid.UUID) -> DataSource | None:
        result = await self.db.execute(select(DataSource).where(DataSource.id == source_id))
        return result.scalar_one_or_none()

    async def connect_database(
        self,
        name: str,
        db_type: DataSourceType,
        connection_params: dict,
        created_by: uuid.UUID,
    ) -> DataSource:
        """Test connection, then persist the data source."""
        conn_str = self._build_connection_string(db_type, connection_params)
        # Test synchronously using synchronous SQLAlchemy engine
        from sqlalchemy import create_engine
        engine = create_engine(conn_str, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()

        source = DataSource(
            name=name,
            type=db_type,
            connection_config=encrypt_config(connection_params),
            created_by=created_by,
        )
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def connect_file(
        self,
        name: str,
        file_type: DataSourceType,
        file_path: str,
        created_by: uuid.UUID,
    ) -> DataSource:
        source = DataSource(
            name=name,
            type=file_type,
            connection_config=encrypt_config({"file_path": file_path}),
            created_by=created_by,
        )
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def delete_source(self, source_id: uuid.UUID) -> None:
        source = await self.get_source(source_id)
        if source:
            await self.db.delete(source)
            await self.db.commit()

    async def extract_schema(self, source_id: uuid.UUID) -> dict:
        """Extract table names, column names, data types, and 5 sample rows."""
        source = await self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")

        config = decrypt_config(source.connection_config)

        if source.type in (DataSourceType.csv, DataSourceType.json, DataSourceType.parquet):
            return self._extract_file_schema(source.type, config["file_path"])
        else:
            return self._extract_db_schema(source.type, config)

    def _extract_file_schema(self, file_type: DataSourceType, file_path: str) -> dict:
        con = duckdb.connect()
        if file_type == DataSourceType.csv:
            con.execute(f"CREATE VIEW data AS SELECT * FROM read_csv_auto('{file_path}')")
        elif file_type == DataSourceType.json:
            con.execute(f"CREATE VIEW data AS SELECT * FROM read_json_auto('{file_path}')")
        elif file_type == DataSourceType.parquet:
            con.execute(f"CREATE VIEW data AS SELECT * FROM read_parquet('{file_path}')")

        columns = con.execute("DESCRIBE data").fetchdf()
        samples = con.execute("SELECT * FROM data LIMIT 5").fetchdf()
        con.close()

        return {
            "data": {
                "columns": columns.to_dict(orient="records"),
                "sample_rows": samples.to_dict(orient="records"),
            }
        }

    def _extract_db_schema(self, db_type: DataSourceType, config: dict) -> dict:
        from sqlalchemy import create_engine, inspect
        conn_str = self._build_connection_string(db_type, config)
        engine = create_engine(conn_str)
        inspector = inspect(engine)
        schema: dict[str, Any] = {}

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_info = [{"name": c["name"], "type": str(c["type"])} for c in columns]
            with engine.connect() as conn:
                rows = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 5")).mappings().all()
                sample_rows = [dict(r) for r in rows]
            schema[table_name] = {"columns": col_info, "sample_rows": sample_rows}

        engine.dispose()
        return schema

    def get_filtered_schema(self, full_schema: dict, permitted_tables: list[str] | None) -> dict:
        """Return schema filtered to only permitted tables. None = all tables."""
        if permitted_tables is None:
            return full_schema
        return {k: v for k, v in full_schema.items() if k in permitted_tables}

    @staticmethod
    def _build_connection_string(db_type: DataSourceType, config: dict) -> str:
        if db_type == DataSourceType.postgres:
            return (
                f"postgresql://{config['user']}:{config['password']}"
                f"@{config['host']}:{config.get('port', 5432)}/{config['database']}"
            )
        elif db_type == DataSourceType.mysql:
            return (
                f"mysql+pymysql://{config['user']}:{config['password']}"
                f"@{config['host']}:{config.get('port', 3306)}/{config['database']}"
            )
        elif db_type == DataSourceType.sqlite:
            return f"sqlite:///{config['database']}"
        raise ValueError(f"Unsupported DB type: {db_type}")
