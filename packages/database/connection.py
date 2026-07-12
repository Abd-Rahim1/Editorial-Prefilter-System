import os
import yaml
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

def get_connection():
    db_user = "postgres"
    db_password = "postgres123"
    db_host = "localhost"
    db_port = "5432"
    db_name = "editorial_prefilter"
    
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        config_path = project_root / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            db_cfg = config.get("database", {})
            db_user = db_cfg.get("user", db_user)
            db_password = db_cfg.get("password", db_password)
            db_host = db_cfg.get("host", db_host)
            db_port = db_cfg.get("port", db_port)
            db_name = db_cfg.get("dbname", db_name)
    except Exception:
        pass

    return psycopg2.connect(
        host=os.getenv("DATABASE_HOST", db_host),
        database=os.getenv("DATABASE_NAME", db_name),
        user=os.getenv("DATABASE_USER", db_user),
        password=os.getenv("DATABASE_PASSWORD", db_password),
        port=os.getenv("DATABASE_PORT", db_port)
    )

def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)