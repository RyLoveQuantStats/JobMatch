# db_manager.py

import sqlite3
from utils.db_utils import create_connection, execute_query, execute_read_query

class DBManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = create_connection(db_file)
    
    def add_job(self, title, company, location, description, ticker, posted_date, similarity_score=None):
        """
        Insert a new job posting into the jobs table.
        """
        query = """
        INSERT INTO jobs (title, company, location, description, ticker, posted_date, similarity_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (title, company, location, description, ticker, posted_date, similarity_score)
        return execute_query(self.conn, query, params)
    
    def get_jobs(self, filters=None):
        """
        Retrieve job postings. Optionally accepts a filters dictionary, e.g.,
        {'ticker': 'AAPL', 'location': 'New York'}.
        """
        query = "SELECT * FROM jobs"
        if filters:
            conditions = []
            params = []
            for key, value in filters.items():
                conditions.append(f"{key} = ?")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
            return execute_read_query(self.conn, query, params)
        else:
            return execute_read_query(self.conn, query)
    
    def update_similarity(self, job_id, similarity_score):
        """
        Update the similarity score for a given job posting.
        """
        query = "UPDATE jobs SET similarity_score = ? WHERE job_id = ?"
        params = (similarity_score, job_id)
        return execute_query(self.conn, query, params)
    
    def add_or_update_company(self, name, ticker, sector, industry):
        """
        Add a new company or update an existing company’s details.
        """
        select_query = "SELECT company_id FROM companies WHERE ticker = ?"
        result = execute_read_query(self.conn, select_query, (ticker,))
        if result and len(result) > 0:
            # Update existing record
            query = "UPDATE companies SET name = ?, sector = ?, industry = ? WHERE ticker = ?"
            params = (name, sector, industry, ticker)
        else:
            # Insert new record
            query = "INSERT INTO companies (name, ticker, sector, industry) VALUES (?, ?, ?, ?)"
            params = (name, ticker, sector, industry)
        return execute_query(self.conn, query, params)
    
    def get_company(self, ticker):
        """
        Retrieve company details by ticker.
        """
        query = "SELECT * FROM companies WHERE ticker = ?"
        return execute_read_query(self.conn, query, (ticker,))
    
    def close(self):
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
