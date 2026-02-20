# Facebook Page Insights to BigQuery Automation

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)

This Python script automates fetching daily Facebook Page insights (reach and total page likes) and uploads the data into Google BigQuery for analytics and reporting purposes.

---

## Quickstart
1. Install dependencies:
```bash
pip install facebook-sdk pandas google-cloud-bigquery google-auth
```

2. Configure your Google Cloud service account and BigQuery table.
3. Add your Facebook Pages and access tokens in the script.
4. Run the script:
```
python fb_insights_to_bq.py
```
## Features
- Fetches daily **Facebook Page likes** and **unique reach** metrics.
- Supports multiple Facebook Pages in a single run.
- Uploads processed data into **Google BigQuery**.
- Saves a local **CSV backup** of fetched data.
- Detailed logging and traceback for debugging.
- Handles **dynamic date ranges**.

## Requirements
- Python 3.8+
- Facebook SDK for Python
- pandas
- google-cloud-bigquery
- google-auth

## Installation
```
git clone https://github.com/yourusername/fb-insights-to-bq.git
cd fb-insights-to-bq
```
Make sure your **Google Cloud service account JSON** file is accessible. This file is required to authenticate with BigQuery.

## Configuration
Edit the script to update these variables:
```
BQ_CREDENTIALS_PATH = r"C:\path\to\your\service_account.json"
BQ_PROJECT_ID = "your-gcp-project-id"
BQ_DATASET_ID = "your_bigquery_dataset"
BQ_TABLE_ID = "your_bigquery_table"
```

## Facebook Pages
Add your pages and access tokens in main():
```
pages = [
    {
        'page_id': 'YOUR_PAGE_ID',
        'access_token': 'YOUR_PAGE_ACCESS_TOKEN'
    },
    ...
]
```
> Important:
> "Access tokens must have read_insights permission."
> "Avoid storing tokens in code for production; consider environment variables."
> ```
> import os
> ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")
> ```
> "Access tokens may expire. Make sure they are valid."

## Date Range
By default, the script fetches the last **8 days** of insights (from yesterday minus 7 days up to yesterday).
```
from datetime import datetime, timedelta

end_date = datetime.now() - timedelta(days=1)
start_date = end_date - timedelta(days=7)
```
## Output
### BigQuery Table
| Page Name   | Date       | Reach  | Total Page Likes |
| ----------- | ---------- | ------ | ---------------- |
| ExamplePage | 2026-02-12 | 12,345 | 6,789            |

## CSV Backup
A CSV file is saved locally for each page:
```
fb_insights_<PageName>_<start_date>_to_<end_date>.csv
```

Example:
```
fb_insights_ExamplePage_2026-02-12_to_2026-02-19.csv
```

## Error Handling
- Facebook API errors are caught and printed with a traceback.
- Upload errors to BigQuery are logged in detail.
- Pages that fail to fetch or upload data are tracked in error_pages.

## Notes & Best Practices
- Ensure your Google Cloud service account has permission to write to BigQuery.
- Use a dedicated access token for insights fetching.
- Validate all pages and tokens before running.
- Temporary CSV files are cleaned up automatically.
- Debug logs include a metrics summary and a full data preview.
