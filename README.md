**Facebook Page Insights to BigQuery Automation**

This Python script automates fetching daily Facebook Page insights (reach and total page likes) and uploads the data into Google BigQuery for analytics and reporting purposes.

**Features:**
- Fetches daily Facebook Page followers (likes) and unique reach metrics.
- Supports multiple Facebook Pages in a single run.
- Uploads the processed data into Google BigQuery.
- Saves a local CSV backup of fetched data.
- Detailed logging and traceback for debugging.
- Handles date ranges dynamically.

**Requirements:
**- Python 3.8+
- Facebook SDK for Python
- pandas
- google-cloud-bigquery
- google-auth
