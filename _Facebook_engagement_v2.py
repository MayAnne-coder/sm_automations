import facebook
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import os
from facebook import GraphAPI


class FacebookEngagementCollector:
    def __init__(self, page_id: str, access_token: str):
        """Initialize the Facebook engagement collector.

        Args:
            page_id (str): Facebook page ID
            access_token (str): Facebook API access token
        """
        self.page_id = page_id
        self.graph = facebook.GraphAPI(access_token)

    def check_posts_made(self, start_date: str, end_date: str) -> int:
        """Check if posts were made during the date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            int: Number of posts made during the period
        """
        try:
            # Convert dates to timestamps for API query
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_ts = int((datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).timestamp())
            
            # Get posts in the date range
            posts = self.graph.get_connections(
                self.page_id,
                'posts',
                fields='created_time',
                since=start_ts,
                until=end_ts,
                limit=100
            )
            
            post_count = len(posts.get('data', []))
            return post_count
        except Exception as e:
            print(f"  Error checking posts: {str(e)}")
            return -1  # Return -1 to indicate error
    
    def get_page_engagement(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Collect page engagement metrics for the specified date range.

        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format

        Returns:
            Optional[pd.DataFrame]: DataFrame containing engagement metrics or None if error occurs
        """
        try:
            # Get page info
            page_info = self.graph.get_object(self.page_id, fields='name')
            page_name = page_info.get('name', '')
            
            # Get page insights
            insights = self.graph.get_connections(
                self.page_id,
                'insights',
                metric=['page_post_engagements'],
                period='day',
                since=start_date,
                until=end_date
            )
            
            # Debug: Print raw API response for troubleshooting
            print(f"\nDEBUG: Raw API response for {page_name}:")
            print(f"  - Has 'data' key: {'data' in insights}")
            if 'data' in insights:
                print(f"  - Number of data items: {len(insights['data'])}")
                if insights['data']:
                    print(f"  - First data item keys: {insights['data'][0].keys()}")
                    if 'values' in insights['data'][0]:
                        print(f"  - Number of values: {len(insights['data'][0]['values'])}")
                        if insights['data'][0]['values']:
                            print(f"  - Sample value: {insights['data'][0]['values'][0]}")
            
            # Process insights data
            insights_data = []
            if 'data' in insights and insights['data']:
                for data in insights['data']:
                    if 'values' in data and data['values']:
                        for value in data['values']:
                            # Handle potential missing or None values
                            engagement_value = value.get('value', 0)
                            if engagement_value is None:
                                engagement_value = 0
                            
                            insights_data.append({
                                'Page Name': page_name,
                                'Date': datetime.strptime(value['end_time'], '%Y-%m-%dT%H:%M:%S+0000').strftime('%Y-%m-%d'),
                                'Engagements': engagement_value
                            })
            
            # Convert to DataFrame and process
            df = pd.DataFrame(insights_data)
            if not df.empty:
                df = df.sort_values('Date', ascending=False)
                # Debug: Check if all values are 0
                total_engagements = df['Engagements'].sum()
                print(f"DEBUG: Total engagements for {page_name}: {total_engagements}")
                if total_engagements == 0:
                    print(f"WARNING: All engagement values are 0 for {page_name} in date range {start_date} to {end_date}")
                    # Check if posts were actually made during this period
                    post_count = self.check_posts_made(start_date, end_date)
                    if post_count > 0:
                        print(f"  -> {post_count} post(s) were made during this period, but received 0 engagements")
                    elif post_count == 0:
                        print(f"  -> No posts were made during this period (this explains the 0 engagements)")
                    else:
                        print(f"  -> Could not verify if posts were made (API error)")
                    print(f"  Other possible reasons:")
                    print(f"  1. Posts were made but received no engagements")
                    print(f"  2. The metric 'page_post_engagements' may not be available for this page")
                
                self._save_and_display_results(df, start_date, end_date)
                return df
            
            print(f"\nNo insights data found between {start_date} and {end_date}")
            return None
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            import traceback
            print("--- Error Traceback ---")
            print(traceback.format_exc())
            print("----------------------")
            return None

    def _save_and_display_results(self, df: pd.DataFrame, start_date: str, end_date: str) -> None:
        """Save results to CSV and display them.

        Args:
            df (pd.DataFrame): DataFrame containing the results
            start_date (str): Start date of the data collection
            end_date (str): End date of the data collection
        """
        print(f"\nPage Post Engagements ({start_date} to {end_date}):")
        print(df.to_string(index=False))
        
        filename = f'page_post_engagements_{start_date}_to_{end_date}.csv'
        df.to_csv(filename, index=False)
        print(f"\nData saved to {filename}")


# Add configuration constants
BQ_CREDENTIALS_PATH = "C:\\Users\\PM Shift\\OneDrive\\sc-v1\\encoded-source-413108-e44383b61f60.json"
BQ_PROJECT_ID = "encoded-source-413108"
BQ_DATASET_ID = "Internal_Stats_SMM_automation"
BQ_TABLE_ID = "fb_engagements_automation"

# Add the upload_to_bigquery function
def upload_to_bigquery(df, BQ_PROJECT_ID, BQ_DATASET_ID, BQ_TABLE_ID):
    try:
        # First save to CSV
        temp_csv_path = "temp_engagement_data.csv"
        df.to_csv(temp_csv_path, index=False)
        
        # Setup credentials
        credentials = service_account.Credentials.from_service_account_file(
            BQ_CREDENTIALS_PATH
        )
        
        # Initialize BigQuery client
        client = bigquery.Client(credentials=credentials, project=BQ_PROJECT_ID)
        
        # Define the table reference
        table_ref = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
        
        # Define schema
        schema = [
            bigquery.SchemaField("Page Name", "STRING"),
            bigquery.SchemaField("Date", "DATE"),
            bigquery.SchemaField("Engagement", "INTEGER"),
            
        ]
        
        # Load the CSV to BigQuery
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema=schema,
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1
        )
        
        with open(temp_csv_path, "rb") as source_file:
            job = client.load_table_from_file(
                source_file,
                table_ref,
                job_config=job_config
            )
        
        # Wait for the job to complete
        job.result()
        
        print(f"Successfully uploaded {len(df)} rows to {table_ref}")
        return True
    
    except Exception as e:
        print(f"Error uploading to BigQuery: {str(e)}")
        return False
    finally:
        # Clean up temporary CSV file
        if 'temp_csv_path' in locals():
            try:
                os.remove(temp_csv_path)
            except OSError:
                pass

def main():
    # Define date range
    start_date = "2026-02-01"  # Replace with your desired start date
    end_date = "2026-02-08"    # Replace with your desired end date

    # Define a list of page_id and access_token pairs
    pages = [
        {
    'page_id': '1506249542773779',      # 1stchoicedating.com
    'access_token': 
    'EAAU79kZCQM80BPletk2ENZAREjlfo94kJoJ105sZBshKu72meZARRcqIgH7o1cMj7M6qGKiUxGMJnfdZA0ZCXPvGo9v6Ty3XcWBSnWgoGIhyz9A54ZCZAeCtthnoyWBw5jPXcrqvrZABgBnxZCt03OvlYopaAwJiUnp32edR5Y6lLvP6j7qlGwvYpiT0ZBqgquA8RHGNrvZApUnX'
},
{
    'page_id': '111735251715320',       # 1stlatinwomen.com
    'access_token': 'EAAU79kZCQM80BPgok9TEN7N7kKflBXjzQuhmw8Vnou2ieJTZCFBIumMT9G20dXfhtJT3APxEeZBkWgLIf1gOhwQnDMZCqIJa2DmtAPvjW2RUOfZAavK3Y4EqI4AGZCR21YxkgogZBDlE8rLvapR4zazI8NL9o7Iqz1f9tbD0Js8SbZBVOcAx3GGhRK5oM8L4j85rBTUZD'
},
{
    'page_id': '113339236962845',       # a-foreign-affair.com
    'access_token': 'EAAU79kZCQM80BPsK5s3nc9DHYbbLyCTZAbeOkMB2RLET00zzNGPK1i66lmT3EGyElSGlT7DOd6t17Fzph6eSb3ukC7eGFQgVxqSsVYu7ZAuDST6G0NZCbfAncZBGDbaaNVZCl9BtZCzq9nwqBZBek6oil7xCXoZBPRObVVtWEpd4m9ELW5G5dLOWZBaweRGInRkt0ooV8ZD'
},
{
    'page_id': '102942631939790',       # acapulcowomen.com
    'access_token': 
'EAAU79kZCQM80BPhXu8CFKq286Qr2mGmvtiRxkqx36iwK3isHGGbZC2vhRqdRiZAv6JhNDko1cgH5rP4zZBrAh0P2Fe3mlDoa1RBQPQYcqWRZCCYWQTtHXZBBliVdKjfOB3rpZBxukYFzbnnjpoSYpifr09ceEZBtFeHszYwEZANLkjSjZApFFa1TwGh61hmN3wnJZAzpyoZD'
},
{
    'page_id': '112663474953906',       # asian-women.com
    'access_token': 'EAAU79kZCQM80BPuhIFWwZAnuMFMeDsdadw8C8LlpsdpUGRJiLclgDS8Uq5k1IXUxZC7HMTFK3iWA5WaG0VDiru8h2gwwX4I8IFHtLcO1Bx14NU23jMqzLFZAKDd55f5jmCk3Up9J6HcBhtNRG2Mfyp0JLBUKL8o9F55qERyK5GpJDNdGOZC4QZAt21S1fJdFwojsYIq6YZD'
},
{
    'page_id': '102337451246251',       # asianlovemates.com
    'access_token': 'EAAU79kZCQM80BPqmnZCfod0QrDI7y1lJVOEqMXSCqLJNZCCM028he8YBn8XjEbJoohocB6b7If9hdvXQOzR37Gj9e9red9nrYIyqLZAfbQ8zVnAQY4Bw0Ral8d5MNChOSzTnnFx7bP3n5PxekkpgtmtsfN2o6AYgndAH02GtOpH7maVgLpg8kYdvgXg9elBtnVOIZCBoZD'
},
{
    'page_id': '105143788766446',       # bangkok-women.com
    'access_token': 'EAAU79kZCQM80BPoyK6XPZBI1pTm9MGMpjYOqt33EccFB08ZCt53ZBocH8IPKCJqW4wSCPrsha8XQEKgmsKUkYBzcF99Gq9u1xu4ZAT5MdCtgijqZBdgEK7twsrzZBcyfqWEWQYFTZAeB9LqYGJAGcOUoU9JmBgxmWZCfONj4i4xELpo4GTj1W7VscnstTH76WoiWPmswZD'
},
{
    'page_id': '2349989701889561',      # barranquilladating.com
    'access_token': 'EAAU79kZCQM80BPkUowXHFIT3lX9uLtVoc534Cc3wL9ZBnmgJbsUoJWkZAziPk9OOrLm45CA7v9ooME6dIkZBk3LJVnSEKvAJBGfogZBEoMIZBqZCagyxRAZCh0rH2oRPPr1VVbIWBrMnidUYTroh5HALcrNGRHimHbYH2JSJWg7WJbyNtfym1hFS7TM6SUTOW61N8mup'
},
{
    'page_id': '101889859395755',       # barranquillasingles.com
    'access_token': 
'EAAU79kZCQM80BPsplzKfWkeq3BWdm2MnDRHVqK2zGvPeZBLv1hGgAGxQZAZCyGlKUsniRQlC7N3ZAtIffUzuIEXzZAI9LM0WQbsLzZA0r2MPxEayichtD7Q9IDtdTJXznZAjN6xWQMjVmaetNsba8P7keKCpgHvzUOAf0fNeMjMxlvNgKdKI8QbexRKTGAA23nHYUJ0ZD'
},
{
    'page_id': '110077387792791',       # barranquillawomen.com
    'access_token': 
'EAAU79kZCQM80BPvjEbz4JZBksnqdgxRiMe5R32Bgnbd6yxpMIusEFFDtA22mqZAO4qTWVdFz6IVgAOPXOxshH91kKRQnbW1YXwQZBmtf5X2AGEilkZA7dyTkZCEikoiMf83ELqYm6G0EDeYlcDbd8zCE8zCPmhHc5QnmQnRqm2zsrjh88QUDVSZAOoHyeYhlydG1c4ZD'
},
{
    'page_id': '100542016198977',       # cebuwomen.com
    'access_token': 'EAAU79kZCQM80BPrVV9CGhHhTHEqYjSO2cjuZCYZAKSFkYsLaWQEWeHSO1OBTubNw3VZByNbgLbIxpsqQ8ZCaFuZChRQ5Ju0UsZCsgXQDODzuCdgidaVnLprpLZADMYXhCTANl6HAl9rhVm5cZBCWaJ4BRsz40YFbhrLENgTJEGy2i5HYVui75qTJ4YZCUSZA6ezjed81lUZD'
},
{
    'page_id': '106538114153792',       # china-brides.com
    'access_token': 'EAAU79kZCQM80BPlO8OY3F7dVQRHpo7ZBnStzfG7mSmiCHbRhYwBIJfksMwAfnJDAEvouNJb8obZBCwsuGkkbDUIZCSUOMPW8sfRGcrc3vsj95zSl1NHwRqS9n1o6uyexrKf5jZBkluYDJJyJynuUSZBfVLIZAHQFxcojCEiZBMiO9gvBkh61l2RZCitTl2Q6UbS9qMkFsHJIZD'
},
{
    'page_id': '2373729159553276',      # colombianlady.com
    'access_token': 'EAAU79kZCQM80BPhvDdt3QYqiP6aYxoawPwWn7NPExDruONb2liS8alxvXFttWOSD0eD39UOAQBpmYbZAm06ABcW5XZAMdTkLpxrtVN3HGnZBUcZA4cZBQcXDiUBxm5NOtoxGlP7s72ZBF4PewlKQPCdFIVDmk8RS3clhLdM3tODuukhjzOJeE1pE7beM00fOS1zUcM6HuiH'
},
{
    'page_id': '109982603790834',       # colombianwoman.com
    'access_token': 
'EAAU79kZCQM80BPphIkUS5ri7GdUbXwY8jNyBCHNHZAIsS2E6AsTtUxPItGLhLCRnXA9nPTSXGowrGykoigVBJFu1ZC2jNkW37GKAhqJhLBct01qF6zwHNmN0BpslayN7d8MH6o0cZALl8WmZB7R2m6ljUhZAt3nn84GW1FhJeCrnV2WnpZA0VIhtZAigO9bSvpoTY8kZD'
},
{
    'page_id': '113923082579589',       # costa-rica-women.com
    'access_token': 'EAAU79kZCQM80BPiQTuI7hNedhbOv1MpLJQwUb0kF2eqFh0qhjKMQXuEjSGA69ZAOZCW2qiCm6njCH2Xw10poqgX2h2bi7OOh3Ne6DktI2Y6DcZBM9OLn6ZA0z9hQRFY6bclUqrLPmeU1KKYO0hZCHZCsIC85i5bd286ey8PyKx7t8CgkV7kZAZAan4ZCiIxzoBH2nbSlgTznsZD'
},
{
    'page_id': '109274038644039',       # filipino-bride.com
    'access_token': 
    'EAAU79kZCQM80BPoYsvnpHCEkIJT1s63v1WjVoj18fhVLTHzcEUTX47tn4j3R9UHVlaZAGvH9UqtrKNou8SU300BhCTV3T2uFcfzH4QNZA8uwcz8TUvywMYF7wo8Q5qh5ZAgQJfdJr0GRl2BK4M6R4PZCirFGr5UQVzhmW0QQp1y92aafVdcKx8IjJYZAAtFW5yUvQZD'
},
{
    'page_id': '103275485919781',       # filipino-women.com
    'access_token': 'EAAU79kZCQM80BPq0J6zssFWwOetV7x1qi3ApZAKpfqUM7sQ89gIWZBKdgg94ZBbJvACL4BZCiT6Y1BgigSfCZCHdwblUflSX3nLjJvIV8jneUVuaB4NJG6cLnt28pL8VeICiZBwoWKCBqBscRMkP2xBZAucEnaNpIYwClXAQmWbZAVjfPUSb1AJvmenYd6OZCVmCF9KL4ZD'
},
{
    'page_id': '111754168245315',       # foreignbride.com
    'access_token': 
'EAAU79kZCQM80BPgUNsZAzuUnClhIEFlQ0iqZA1dMPyui3YpmMj2jkWd4yYWjJZAcHE4eJXPC49HGHy4PQBtNztth7L1ZCHW7wSJDPtplnNbQZB6qvUhOslqvZC94ByrWGjOLnxhnuZC6LGBVVrqZAeAq72ZCRKvIXIIKhNtfdxr3TaZAemBiYNTx9clNqfbLjk2vCPSj4cZD'
},
{
    'page_id': '105926541553737',       # international-dating.com
    'access_token': 'EAAU79kZCQM80BPlpkW8AbxsD40qnZA5VjPOkHf6j4Rc7ZCME9ZCjaoXuQUuSXOjDZAtI2ZCvIZBETZBAsSEsmdFafKJnmAPrkFO2w0Lz5ZCTtAUWEHOZB0xrjJShpG1Bfni0ZB9cXRSO71odI2rkZABnSsMoMgNVraaUJYY0TWY9I4KhD3Gv9qDMMxh19kN1Lgpmv3ZCKSgSSnTUZD'
},
{
    'page_id': '587358945054158',       # islandladies.com
    'access_token': 'EAAU79kZCQM80BPgbS53GlpmUJxSvZChhWvia7pNwFd2EUh5wCILLJ3OfuAYve6n14r6aeBs7GL4d2JnU6m2h6UZAtvreXRhrZCZCYLgOdqUb7bZC36wZBT1tZA9zJqK1n4EZCHxYaFEzlDI90KK6UovggHWVuqOolyP4cmay3o6MkPGcumBUeKnZAZBaOZBGENXupvEbXyH6iCPF'
},
{
    'page_id': '2386086651618892',      # latin-personals.com
    'access_token': 'EAAU79kZCQM80BPjGTIYMGWHRapM3A5QLvvalvPvAdZCjmfeFIzW1te7Pg2PzBYfDfmRF025F7DFYwifI8jI67b55Psd7rTfZBV3t3BJYYHZBCxjkyeLI1XPWSXfEJVjZBWWDKBfuhrlfZCg0ZCRN2BZB9dAdpOZAi2tmBOgerJBjfDUlMhMejRCfURV3vtPOjU21j3WzfZAfu3'
},
{
    'page_id': '109986877198571',       # latinlovemates.com
    'access_token': 'EAAU79kZCQM80BPtxBcv882WqD2rxeWSj80OSW00Fj3gKNFb2FH7d8x62UMdMNtHh5bwWL1uMbj5RuZBb6KOWesmFy6rwr4qKqmxHNqDdHXeCvgk46ZB1zDij9FFiVeZAcUldT8MLIu0ZBeEoL2aWRdYrYdTRZATlwCM0TjeZAejJzlzPgzJFV1ot5epDM04bV2HZBksZD'
},
{
    'page_id': '102269671226464',       # manila-women.com
    'access_token': 'EAAU79kZCQM80BPjcN4Fyu41z4eEvlZBFIB02xmmW1bSMBv6pYjMZCXndN8PY4lXBZBz4Vc5L36xLEBmRuOYoZA6ZCsnnrsnG36sZBhwe5aHOc2FE1dWZA0GhrkZBPrPznRao18TFuk7wU7pEwTVGWQzCZBgdq5E6m1tHaIx2rQE6i9SWZBXIgSh5k4ZAQ6PFwPUOcMsWLRUZD'
},
{
    'page_id': '1048123725377818',      # medellindating.com
    'access_token': 'EAAU79kZCQM80BPu3mfHhXAGLkaFxZC1WEZBfMOH0yy4uelrT8Dymemso781cDjz5qsOeUXZCObB1uqSpeUkVzm7pf90tTvC5UE3GgjdXyevb3UqvdSeQsoC5Eo79vLE0RhXkWTx4sxNeRZBjYQeIDekgTWJQBjUXra1BXvZC4SYkXD3lmf08oehItGZCvpZA0oaiqJig'
},
{
    'page_id': '370778293538006',       # medellinsingles.com
    'access_token': 'EAAU79kZCQM80BPlCh337oXSzg3CMLgedXZAMXRGEqGstLVBu19bZAJJLo3YXNJ0jPfmi6bYuw4tUn1QcDilinVzuGopzEFqamlKkSev8D5nAW3TkQ1CNzS5c2tVsB96hPa0fIZCKvhrXloI9LDcLsnUn67qNhZCZCZAC2i69c7xVkwDtyoovIdxt0QDUHLIkGwm9KfYMHv7'
},
{
    'page_id': '110982528457798',       # medellinwomen.com
    'access_token': 'EAAU79kZCQM80BPuGiu7p0QtkNEr1NCefHLpnc6dzuhPLHNXlIHErzmwK6ZBnjblR1cYB7K3GZCz2jmyhNzIm5Hq65EOAyloKfHZCY41QuOLaibK2V9auoMZBluSqMRLy5SwVv7yI87prPmKQZCKnvmZCS7NvSZCdA3qrZB2l5VflPxwICoUYuOW6JJZBpdkEfnRqqP4fAZD'
},
{
    'page_id': '106705804256226',       # mexicanlovemates.com
    'access_token': 'EAAU79kZCQM80BPl8UMeo1zkwYjOdWCgUnycxWu6dfAZBzMeoJNodF3Mklfiv3GLU8XmxAZAof6yfBEeuzxCE3dWQQIlrLbyuO7F6lcEM5J3ZC9ZAgkq7gEWFiufud4BN2wGdLlOXW5cHuK2e72gOEI5oDzfu91xpSZBZAaUm2XMWDCOJtUZAdO8xJJMCHTtqAHXnbIEZD'
},
{
    'page_id': '111086494979811',       # mexicocitydating.com
    'access_token': 'EAAU79kZCQM80BPv0GtxFrTff5da8YHWTgxZBlIEoWaNnrdcoOKjoFP07ksFvKZCOUpAk4MayAnfS2TSZBYdRt5VRNdmXhj8MzGjDKv8xUkkknMdrflTtqhw7tqZAUWPTpBV8Ndu6KBbGpVMfNSdrMiA1440tggs4rj0zhDAmkeryS3gjcWghq4UkLhGZAOzdcMIBVEqDUZD'
},
{
    'page_id': '107131400746857',       # mydreamasian.com
    'access_token': 'EAAU79kZCQM80BPiNf8VhH86grZCAl06QmC11ZBoA7pZBpdqE7iQcbZAyhCInoRopzaDw3ajIOXoPJZBGkOQ0RtORm6hvIKBZAGKLvGDyUwDXOrkMeVJjzW21Xvoi7vGSmf23Wo1dCNaNk2lZBEYnF9FQKRsZAwgvDC9Fh8ZC2Adb6ZBThcobUor8kgTn9AF3dO5WSkb47LZC3JAZD'
},
{
    'page_id': '1972766582754024',      # odessawomen.com
    'access_token': 'EAAU79kZCQM80BPg0AZA05doWKC9Xar03XR8jmbttMqr4AMC9Gb4UhIXsKZBF6TAXhKpTsQGUuJ4E2LtbUlZA555wga6rc17c1TZButF4ZBBM2UhJs9YeHkBuKEe5RYOZC3pBZCJmyIxiCu7iLSu8hkZA2HnqXkydx9IACpuz2DwKTzguAh4c9uturlJ6LLl4zOIKdwoZA7'
},
{
    'page_id': '100705881707495',       # peru-women.com
    'access_token': 'EAAU79kZCQM80BPjZCrJjsdnZBSWtiCwfmnqX48kNt3506ZCCvFiKyMw2vb6ikRBGi6vZCA22N5Rp0VCmc0iCnTi5S4qITLiDv46nv6xYvXmhOpiZAANEEu69H2gB6DSPcnaqjE5usvJiZBRZAIZCIcQSl2AnuveXpD9XSYuh5iVbDYp4gS5tLSngrK64uNZBs5dQHgQZBAZD'
},
{
    'page_id': '441423289781124',       # philippine-women.com
    'access_token': 'EAAU79kZCQM80BPnISZCN4dvi3rPZAKu1KdLiZBbPxfhm1AwQrpNVsLynerU7SSLaACYt5IgZCcx66ReMUkZBLOnCLJdCSrFfmXXN9pxE4DrZAvahUi04Bd26SR7sxg02qzcwLIxf8pEyriVfXKfaO3UzMpYnRPnQT7P9BF6apEETQZAm37VeHT3KPellGYqymJKbyIlK'
},
{
    'page_id': '1934165216803908',      # poltavawomen.com
    'access_token': 'EAAU79kZCQM80BPvy8qE4QylZAoVn2ukUibAPNQykPRjZBHPDpnt7gg8FXwU06NbGjDoFyz4m6FyqllDAAoOvEwU28bcGgZCZAMNmFnpgOQwlQcK1AfdJ2WYcgmNK7dk67NAkqWijxpouMkNucj2ZCi6AYUtDcTZBIbiWE861s1W3rWz6BYv7AREpYqmpiWEDFEOWkfd6baR'
},
{
    'page_id': '108954838350310',       # shenzhenwomen.com
    'access_token': 'EAAU79kZCQM80BPoHlr3I7Sx0eBcsMWXgMcPNIWyDzfoeMZAkncMcLcIj7UTJkG1JEfEZBdZBQ6SxJK2BUMzpHBpStBqOwyrZBEc8LrAfFsKLSSxzwzPy7ybDGegwOaZB6jGZBLBpN9gI9CG7VHlxRbhdUA3Iv5xiRGN4Fce11FgJkpWHNseeptVTOC0Y6ZARhF32IjcZD'
},
{
    'page_id': '242384353128583',       # thailand-women.com
    'access_token': 
'EAAU79kZCQM80BPq9HZBlJBUnZC1Nx6ohzCmDZAA6DlhhBh4hRSh8z37SQKQ4b22sykp91xMIfcVSpczGIFVGHsDAbX65qVkvZAzjdujvGp9XaQcrJxZCbXUsbyJYOT5kj9Uxkse0h0pDgYZAhbTj1hPhFb4We6T3ETNSNZAbXmZCx1XWmI6GuISR7mS1BLc8v2ffD9EgZD'
},
{
    'page_id': '1393329487468986',      # ukraineladies.com
    'access_token': 'EAAU79kZCQM80BPhjBDsFIzhXwEZCE1Rr7aXZCPUSDVv5gEZAJdtKkfN3zisK47cg3GlJ0nVxzl4ZBaZCtW9aBzu6VQW5zapGVrxTuQEiyInMbGRsFGxsYC1ZBryy8GZBBsroAcexqZBn17sMfeRXj0tR3m08rZAcQKcQwqaQ3viRnHCkpZCaN0EdGJDh7ZBgcoQj8vOZBgZCNsqbRE'
},
{
    'page_id': '110840670411783',       # ukrainesingles.com
    'access_token': 
'EAAU79kZCQM80BPrJBsIHumsLox7zL5yC5uV4S5FnPm8IIZC0ZCw3vADC7mg3Y5xp6luzVe1khKS0tYOC4jLhQ3K35MjV0ys498ZAipYtHkS9lAqgH3CQP3XjMqZA761K70OkXS8rNCzpBypXRkBxo5DrNKyy4qdYpdlfmHWE5dC9BRkjTFZCHrVxQo3bztI3ulmMTXRK0ZD'
},
{
    'page_id': '105060968797194',       # cebuinsights.com
    'access_token': 'EAAU79kZCQM80BPoiaIz7UuudpTwq4AZAxijtPvgic1ZBgk1PmXffCw3zxnsQyYv0zbSZARdPR58lS3GsJplsFw108rCTLVcZAZCMljBJUqgLKCV3KpYzsgPxEv0k2IB82qYtXwDabZBgV7ezcOYyVJ10SvrutJv3ahqZBsorBYw5H53esxxYWcLRaFXE6E1NXOzJmW7FEAAZD'
},
{
    'page_id': '100405672192623',      # foreignladies.com
    'access_token': 'EAAU79kZCQM80BPiX6EDq7c0d8t9Ytsnizj99WTac6TSMEmJipqZBymv0J9Ut8cVzAXWXEc6ACZBjZBpFXJjBSv43tOYTd39kK3MoqUvnAvSrEPhQ5EABagTFBAMPEYX8TAkIjmwnw1C2YfqPiVrVxr79JolWfcTLzLKorfaCpawDUx4kKxdNEkpvk3ZCYJZAbPMEZBc1UMZD'
}


    ]


    successful_count = 0  # Counter for successful uploads
    failed_count = 0      # Counter for failed uploads

    for page in pages:
        page_id = page["page_id"]
        access_token = page["access_token"]
        
        # Basic check for missing ID or Token
        if not page_id or not access_token:
            print(f"\nSKIPPING: Missing Page ID or Access Token in configuration: {page}")
            failed_count += 1
            continue
        # Simple check for placeholder token
        if 'YOUR_' in access_token or len(access_token) < 50: # Add basic length check
             print(f"\nSKIPPING Page ID: {page_id} - Access token seems invalid or placeholder.")
             failed_count += 1
             continue

        print(f"\n{'='*40}")
        print(f"Processing Page ID: {page_id}")
        print(f"{'='*40}")

        # Create collector instance and get engagement data
        collector = FacebookEngagementCollector(page_id, access_token)
        engagement_df = collector.get_page_engagement(start_date=start_date, end_date=end_date)
        
        if engagement_df is not None and not engagement_df.empty:
            # Upload to BigQuery
            upload_success = upload_to_bigquery(engagement_df, BQ_PROJECT_ID, BQ_DATASET_ID, BQ_TABLE_ID)
            if upload_success:
                print(f"Data successfully uploaded to BigQuery for page {page_id}")
                successful_count += 1  # Increment successful count
            else:
                print(f"Failed to upload data to BigQuery for page {page_id}")
                failed_count += 1  # Increment failed count
            
            # Save to CSV with date range in filename (keeping this as backup)
            page_name = engagement_df['Page Name'].iloc[0]  # Get the page name
            filename = f'fb_engagement_{page_name}_{start_date}_to_{end_date}.csv'  # Include page name in filename
            engagement_df.to_csv(filename, index=False)
            print(f"\nBackup data saved to {filename}")
        else:
            print(f"Failed to retrieve engagement data for page {page_id}")
            failed_count += 1  # Increment failed count

    # Print summary of results
    print(f"\nSummary: {successful_count} pages processed successfully, {failed_count} pages failed.")

if __name__ == "__main__":
    main() 