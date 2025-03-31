#!/usr/bin/env python3
import sqlite3
import logging
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import SENDGRID_API_KEY, EMAIL_SENDER, EMAIL_RECIPIENT, DATABASE_FILE

# Logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------
# Database Utility Functions
# ---------------------------
def ensure_emailed_date_column(DATABASE_FILE):
    """
    Ensure that the jobs table has an 'emailed_date' column.
    If the column already exists, this function will catch the error.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN emailed_date TEXT")
        conn.commit()
        logging.info("Added 'emailed_date' column to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logging.info("'emailed_date' column already exists.")
        else:
            logging.error("Error altering jobs table: %s", e)
    finally:
        conn.close()

def get_top_unemailed_jobs(DATABASE_FILE, limit=10):
    """
    Retrieve the top 'limit' unemailed jobs sorted by the SBERT similarity score.
    The query now selects additional fields for the email digest.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    query = """
        SELECT job_id, title, company, location, estimated_salary,
               company_website, job_apply_link_extracted, education_pattern,
               posted_date, days_ago, description, similarity_score_sbert
        FROM jobs
        WHERE emailed_date IS NULL
        ORDER BY similarity_score_sbert DESC
        LIMIT ?
    """
    cur.execute(query, (limit,))
    jobs = cur.fetchall()
    conn.close()
    return jobs

def mark_jobs_as_emailed(DATABASE_FILE, job_ids):
    """
    Update the 'emailed_date' for the given job IDs to mark them as emailed.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    for job_id in job_ids:
        cur.execute("UPDATE jobs SET emailed_date = ? WHERE job_id = ?", (now, job_id))
    conn.commit()
    conn.close()
    logging.info("Marked %d jobs as emailed.", len(job_ids))

# ---------------------------
# Email Functions using SendGrid
# ---------------------------
def compose_email_body(jobs):
    """
    Build an HTML email body that contains a table listing each job's details.
    New columns included: estimated salary, company website, job apply link,
    education, posted date, and days ago.
    """
    html = "<html><body>"
    html += "<h2>Top 10 New Jobs for Today</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    # Define table headers including new fields.
    headers = (
        "Job ID", "Title", "Company", "Location", "Estimated Salary", "Company Website",
        "Job Apply Link", "Education", "Posted Date", "Days Ago", "Similarity Score", "Description"
    )
    html += "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    for job in jobs:
        # Unpack fields based on the SELECT order.
        (job_id, title, company, location, salary, website, apply_link,
         education, posted_date, days_ago, description, similarity) = job
        # Limit the description snippet to 200 characters.
        snippet = (description[:200] + '...') if description and len(description) > 200 else description
        html += "<tr>"
        html += f"<td>{job_id}</td>"
        html += f"<td>{title}</td>"
        html += f"<td>{company}</td>"
        html += f"<td>{location}</td>"
        html += f"<td>{salary}</td>"
        html += f"<td><a href='{website}' target='_blank'>{website}</a></td>"
        html += f"<td><a href='{apply_link}' target='_blank'>{apply_link}</a></td>"
        html += f"<td>{education}</td>"
        html += f"<td>{posted_date}</td>"
        html += f"<td>{days_ago}</td>"
        html += f"<td>{similarity:.4f}</td>"
        html += f"<td>{snippet}</td>"
        html += "</tr>"
    html += "</table>"
    html += "</body></html>"
    return html

def send_email_sendgrid(subject, body, sender, recipient, api_key):
    """
    Send an email with the given subject and HTML body using SendGrid.
    """
    message = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=subject,
        html_content=body
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logging.info("Email sent successfully. Status Code: %s", response.status_code)
    except Exception as e:
        logging.error("Error sending email with SendGrid: %s", e)
        raise

# ---------------------------
# Main Process
# ---------------------------
def main():
    logging.info("Starting daily email digest process.")
    
    # Ensure the database has the necessary column to track emailed jobs.
    ensure_emailed_date_column(DATABASE_FILE)
    
    # Query the top 10 unemailed jobs based on SBERT similarity scores.
    jobs = get_top_unemailed_jobs(DATABASE_FILE, limit=10)
    if not jobs:
        logging.info("No new jobs to email today.")
        return
    
    # Compose the email content.
    email_body = compose_email_body(jobs)
    subject = "Daily Job Digest: Top 10 New Jobs"
    
    # Send the email via SendGrid.
    send_email_sendgrid(subject, email_body, EMAIL_SENDER, EMAIL_RECIPIENT, SENDGRID_API_KEY)
    
    # Mark the emailed jobs so they won't be emailed again.
    job_ids = [job[0] for job in jobs]
    mark_jobs_as_emailed(DATABASE_FILE, job_ids)
    
    logging.info("Daily email digest process completed.")

if __name__ == '__main__':
    main()
