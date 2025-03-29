```markdown
# Finance Job Scraping & Forecasting System

## Overview
This project is an automated system designed to scrape finance-related job postings, analyze and match job descriptions against a general-purpose finance resume, classify postings by sector, and forecast future job opportunities. It leverages multiple technologies—including API integrations, NLP techniques, SQL data storage, and (upcoming) interactive visualizations—to help users gain insights into the finance job market.

## Features
- **Automated Job Scraping:** Uses the JSearch API to pull finance job postings.
- **Data Storage:** Persists job data and analysis results in a SQLite database.
- **Resume Matching:** Computes similarity scores between job descriptions and a finance resume using both TF-IDF and SBERT approaches.
- **Analysis & Reporting:** Provides deep dive analysis with keyword insights and similarity metrics.
- **Planned Enhancements:** 
  - **Sector Classification:** Integration with YFinance API to categorize postings by finance sub-sector.
  - **Forecasting:** Development of ARIMA models to forecast job posting trends.
  - **Visualization:** Interactive dashboard built with Streamlit to explore current data and forecasts.

## Installation
1. **Clone the Repository:**
   git clone https://github.com/Team-Tu/JobScrape.git
   cd JobScrape
   
2. **Install Dependencies:**
   pip install -r requirements.txt
   
3. **Configuration:**
   - Update `config.py` with your API keys (for JSearch and YFinance) and adjust any file paths as necessary.

## Usage
- **Run the Pipeline:**
  Execute the main script to run the full pipeline—from scraping to analysis:
  python main.py
  
- **Database:**
  The job postings and analysis results are stored in the SQLite database (`data.db`).

## Project Structure

job_scraper/
├── config.py
├── data.db
├── main.py
├── requirements.txt
├── resume.txt
├── database/
├── docs/
├── logs/
├── output/
├── scripts/
└── utils/

- **config.py:** Contains configuration settings and API keys.
- **main.py:** Orchestrates the entire pipeline.
- **scripts/**: Houses modules for job scraping, TF-IDF and SBERT parsing, and analysis.
- **database/**: Includes database management and schema setup scripts.
- **docs/**: Contains project documentation.
- **logs/** & **output/**: Used for log files and generated visualizations (e.g., charts).

## Future Enhancements
- **Sector Classification:** Integrate the YFinance API to fetch and store company sector information.
- **Forecasting:** Implement ARIMA-based models using historical data to predict future job trends.
- **Visualization:** Build an interactive Streamlit dashboard to display job trends, similarity scores, and forecasts.