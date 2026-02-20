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
Add your pages and access tokens in the >pages> list inside >main()>:


