"""
Database Connection Manager placeholder
"""

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="editorial_prefilter",
        user="postgres",
        password="postgres123", 
        port="5432"
    )


def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)