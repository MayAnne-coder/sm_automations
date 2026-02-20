**Facebook Page Insights to BigQuery Automation**

This Python script automates fetching daily Facebook Page insights (reach and total page likes) and uploads the data into Google BigQuery for analytics and reporting purposes.

**Features:**
- Fetches daily Facebook Page followers (likes) and unique reach metrics.
- Supports multiple Facebook Pages in a single run.
- Uploads the processed data into Google BigQuery.
- Saves a local CSV backup of fetched data.
- Detailed logging and traceback for debugging.
- Handles date ranges dynamically.

**Requirements:**
- Python 3.8+
- Facebook SDK for Python
- pandas
- google-cloud-bigquery
- google-auth

Install dependencies using pip:
```
pip install facebook-sdk pandas google-cloud-bigquery google-auth
```


**Installation:**
1. Clone the repository:
```
git clone https://github.com/yourusername/fb-insights-to-bq.git
cd fb-insights-to-bq
```


2. Make sure your **Google Cloud service account JSON** file is accessible. This file is required to authenticate with BigQuery.

**Configuration:**
Edit the script to update these variables:
```
BQ_CREDENTIALS_PATH = r"C:\path\to\your\service_account.json"
BQ_PROJECT_ID = "your-gcp-project-id"
BQ_DATASET_ID = "your_bigquery_dataset"
BQ_TABLE_ID = "your_bigquery_table"
```


**Facebook Pages:**
Add your pages and access tokens in the pages list inside main():
```
pages = [
    {
        'page_id': 'YOUR_PAGE_ID',
        'access_token': 'YOUR_PAGE_ACCESS_TOKEN'
    },
    ...
]
```

**Important:**
- Access tokens must have read_insights permission.
- Avoid storing tokens in code for production; consider using environment variables or a secure vault.
- Access tokens may expire. Make sure they are valid.


**Usage:**
Run the script using Python:
```
python fb_insights_to_bq.py
```

**Date Range:**
By default, the script fetches the last **8 days** of insights (from yesterday minus 7 days up to yesterday). You can modify the date range in main():
```
end_date = datetime.now() - timedelta(days=1)
start_date = end_date - timedelta(days=7)
```

**Output:**
1. **BigQuery Table:**
     Columns: Page Name, Date, Reach, Total Page Likes.
2. **CSV Backup:**
  A CSV file is saved locally for each page:
  ```
  fb_insights_<PageName>_<start_date>_to_<end_date>.csv
  ```

**Error Handling:**
- Errors with the Facebook API are caught and printed with tracebacks.
- Upload errors to BigQuery are logged in detail.
- Pages that fail to fetch or upload data are tracked in error_pages.

**Notes & Best Practices:**
- Ensure your Google Cloud service account has permission to write to BigQuery.
- Use a dedicated access token for insights fetching.
- Validate all pages and tokens before running.
- Temporary CSV files are cleaned up automatically.
- Debug logs include a metrics summary and a full data preview.
