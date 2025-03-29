# db_utils.py

import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    """
    Create a database connection to the SQLite database specified by db_file.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print("Connection error:", e)
    return conn

def execute_query(conn, query, params=None):
    """
    Execute a query (INSERT, UPDATE, DELETE) and commit changes.
    """
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
        return cur
    except Error as e:
        print("Error executing query:", e)
        return None

def execute_read_query(conn, query, params=None):
    """
    Execute a SELECT query and return fetched results.
    """
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        result = cur.fetchall()
        return result
    except Error as e:
        print("Error executing read query:", e)
        return None

def initialize_database(db_file, schema_file='schema.sql'):
    """
    Initialize the database using the provided schema file.
    """
    conn = create_connection(db_file)
    if conn is not None:
        try:
            with open(schema_file, 'r') as f:
                sql_script = f.read()
            cur = conn.cursor()
            cur.executescript(sql_script)
            conn.commit()
            print("Database initialized successfully.")
        except Error as e:
            print("Error initializing database:", e)
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")
