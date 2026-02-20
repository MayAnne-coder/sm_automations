import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from http.client import RemoteDisconnected
import json
import base64
from datetime import datetime, timedelta
import csv
import os

def validate_token(token):
    """Validate token format and basic structure"""
    if not token:
        return False
    # Basic check - tokens are usually longer than 20 characters
    if len(token) < 20:
        return False
    return True

def get_token_region(token):
    """Extract region from token prefix"""
    if token.startswith('dal:'):
        return 'dal'
    elif token.startswith('fra:'):
        return 'fra'
    return None

def create_basic_auth_header(token):
    """Create Basic Auth header from PAT"""
    # For PATs, we use the token as both username and password
    auth_string = base64.b64encode(f"{token}:".encode('utf-8')).decode('utf-8')
    return f"Basic {auth_string}"

def get_date_range():
    """Get date range for the last 7 days in ISO format"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    # Format dates in ISO 8601 format with microseconds
    return (
        start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )

def get_custom_date_range():
    """Get custom date range from user input"""
    while True:
        try:
            print("\nEnter date range (format: YYYY-MM-DD)")
            start = input("Start date: ").strip()
            end = input("End date: ").strip()
            
            # Convert to datetime objects for validation
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            
            # Set time to start and end of day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Validate date range
            if end_date < start_date:
                print("\nError: End date must be after start date")
                continue
                
            # Format dates in ISO 8601 format
            return (
                start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            )
            
        except ValueError:
            print("\nError: Invalid date format. Please use YYYY-MM-DD")
            continue

def get_agent_alias(users):
    """Helper function to extract agent alias based on specific rules"""
    # Find the agent user in the participants
    agent = next((
        user for user in users 
        if user.get('type') == 'agent'
    ), None)
    
    if not agent:
        return 'Unassigned'
        
    # Get agent name and email
    agent_name = agent.get('name', '').strip()
    agent_email = agent.get('email', '').strip().lower()
    
    # Map based on email and name
    if agent_email == 'afacebu.livechat4@gmail.com' and 'Angelie' in agent_name:
        return 'Angelie'
    elif agent_email == 'afacebu.livechat3@gmail.com' and 'Jessa' in agent_name:
        return 'Jessa'
    elif agent_email == 'afacebu.livechat3@gmail.com' and 'Celine' in agent_name:
        return 'Celine'
    elif agent_email == 'afacebu.livechat1@gmail.com' and 'Rhian' in agent_name:
        return 'Rhian'
    elif agent_email == 'afacebu.whil2@gmail.com' and 'Vilma' in agent_name:
        return 'Vilma'
    elif agent_email == 'afacebu.livechat3@gmail.com' and 'Friah' in agent_name:
        return 'Friah'
    elif agent_email == 'afacebu.livechat4@gmail.com' and 'Luna' in agent_name:
        return 'Luna'
    elif agent_email == 'afacebu.livechat1@gmail.com' and 'Debbie' in agent_name:
        return 'Debbie'
    
    return 'Unassigned'

def get_agent_full_name(agent_alias):
    """Helper function to map agent alias to full name"""
    agent_name_mapping = {
        'Angelie': 'Angel Grace Quiano',
        'Jessa': 'Mark Jacob Rentoza',
        'Celine': 'Celeste Caputolan',
        'Rhian': 'Adrian Piñero',
        'Vilma': 'Whilhelm Ledesma',
        'Friah': 'Efren Manjares',
        'Luna': 'Jason Jerome Robinson',
        'Debbie': 'Deah Marie Bonao',
        'Unassigned': 'Unassigned'
    }
    return agent_name_mapping.get(agent_alias, 'Unassigned')

def get_chat_status(thread):
    """Helper function to extract and map chat status from pre-chat form"""
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'prechat':
            for field in event.get('fields', []):
                # Check if this is the question field
                if field.get('label', '').lower().startswith('question'):
                    answer = field.get('answer', {})
                    
                    # Handle different answer formats
                    if isinstance(answer, dict):
                        # For nested answer structure
                        answer_text = answer.get('label', '')
                    elif isinstance(answer, str):
                        # For direct string answer
                        answer_text = answer
                    else:
                        # For other formats
                        answer_text = str(answer)
                    
                    # Clean and normalize the answer text
                    answer_text = answer_text.strip().lower()
                    
                    # Match the answer text
                    if 'registered member' in answer_text:
                        return 'Registered'
                    elif 'just exploring' in answer_text:
                        return 'Exploring'
                    elif 'exploring' in answer_text:
                        return 'Exploring'
    return 'No Answer'

def get_website_domain(website_origin):
    """Helper function to extract website domain based on specific rules"""
    if not website_origin:
        return "Ticket"
        
    website_mapping = {
        "1stchoicedating.com": "1stchoicedating.com",
        "1stlatinwomen.com": "1stlatinwomen.com",
        "a-foreign-affair.com": "a-foreign-affair.com",
        "acapulcowomen.com": "acapulcowomen.com",
        "anewbride.com": "anewbride.com",
        "anewwife.com": "anewwife.com",
        "angelsofpassion.com": "angelsofpassion.com",
        "armtrophy.com": "armtrophy.com",
        "asian-women.com": "asian-women.com",
        "asianlovemates.com": "asianlovemates.com",
        "bangkok-women.com": "bangkok-women.com",
        "barranquilladating.com": "barranquilladating.com",
        "barranquillasingles.com": "barranquillasingles.com",
        "barranquillawomen.com": "barranquillawomen.com",
        "cali-women.com": "cali-women.com",
        "cartagenadating.com": "cartagenadating.com",
        "cartagenawomen.com": "cartagenawomen.com",
        "cebuwomen.com": "cebuwomen.com",
        "china-brides.com": "china-brides.com",
        "chinese-brides.com": "chinese-brides.com",
        "cityofbrides.com": "cityofbrides.com",
        "colombianbride.com": "colombianbride.com",
        "colombiandating.com": "colombiandating.com",
        "colombianlady.com": "colombianlady.com",
        "colombianwoman.com": "colombianwoman.com",
        "costa-rica-women.com": "costa-rica-women.com",
        "davaowomen.com": "davaowomen.com",
        "filipino-bride.com": "filipino-bride.com",
        "filipino-women.com": "filipino-women.com",
        "foreign-affair.net": "foreign-affair.net",
        "foreignlovemates.com": "foreignlovemates.com",
        "international-dating.com": "international-dating.com",
        "internationaldatingclub.com": "internationaldatingclub.com",
        "islandladies.com": "islandladies.com",
        "kievpersonals.com": "kievpersonals.com",
        "kievwomen.com": "kievwomen.com",
        "latin-personals.com": "latin-personals.com",
        "latinlovemates.com": "latinlovemates.com",
        "manila-women.com": "manila-women.com",
        "medellindating.com": "medellindating.com",
        "medellinsingles.com": "medellinsingles.com",
        "medellinwomen.com": "medellinwomen.com",
        "mexicanlovemates.com": "mexicanlovemates.com",
        "mexico-women.com": "mexico-women.com",
        "moscowladies.com": "moscowladies.com",
        "mydreamasian.com": "mydreamasian.com",
        "mymailorderbride.com": "mymailorderbride.com",
        "odessawomen.com": "odessawomen.com",
        "peru-women.com": "peru-women.com",
        "philippine-women.com": "philippine-women.com",
        "poltavawomen.com": "poltavawomen.com",
        "russia-ladies.com": "russia-ladies.com",
        "russia-women.com": "russia-women.com",
        "shenzhenwomen.com": "shenzhenwomen.com",
        "thailand-women.com": "thailand-women.com",
        "ukrainedatingagency.com": "ukrainedatingagency.com",
        "ukraineladies.com": "ukraineladies.com",
        "ukrainesingles.com": "ukrainesingles.com",
        "internationallovescout.com": "internationallovescout.com",
        "wherewomenchaseyou.com": "wherewomenchaseyou.com",
        "foreignbride.com": "foreignbride.com",
        "dateint.com": "dateint.com",
        "mexicocitydating.com": "mexicocitydating.com",
        "perudating.com": "perudating.com",
        "hondurasdating.com": "hondurasdating.com",
        "honduraswomen.com": "honduraswomen.com"
    }
    
    # Check if any of the domains are in the website_origin
    for domain in website_mapping:
        if domain in website_origin.lower():
            return website_mapping[domain]
    
    return "Ticket"

def get_campaign_info(thread):
    """Helper function to extract campaign information"""
    properties = thread.get('properties', {})
    routing = properties.get('routing', {})
    
    # Check for campaign information in various possible locations
    campaign = routing.get('campaign', '')
    if campaign:
        return campaign
        
    # Check for utm_campaign in parameters if exists
    utm_campaign = routing.get('utm_campaign', '')
    if utm_campaign:
        return utm_campaign
        
    # Check if it's a returning visitor
    if routing.get('returning_visitor', False):
        return 'Returning visitors'
        
    return ''  # Return empty string if no campaign info found

def format_time_from_iso(iso_timestamp):
    """Helper function to convert ISO timestamp to 12-hour format in PH time"""
    try:
        dt = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        ph_time = dt + timedelta(hours=8)  # Convert to PH time
        return ph_time.strftime("%H:%M:%S")  # Returns time in 24-hour format (e.g., "12:00:00")
    except (ValueError, TypeError):
        return "00:00:00"

def get_started_time(thread):
    """Helper function to get the started time from the first message"""
    # First try to get from created_at
    created_at = thread.get('created_at', '')
    if created_at:
        return format_time_from_iso(created_at)
    
    # If no created_at, try to get from first event
    events = thread.get('events', [])
    if events:
        first_event = events[0]
        timestamp = first_event.get('created_at', '')
        if timestamp:
            return format_time_from_iso(timestamp)
    
    return "00:00:00"

def get_end_time(thread):
    """Helper function to get the end time from the last message"""
    # First try to get from ended_at if it exists
    ended_at = thread.get('ended_at', '')
    if ended_at:
        return format_time_from_iso(ended_at)
    
    # If no ended_at, try to get from last event
    events = thread.get('events', [])
    if events:
        last_event = events[-1]
        timestamp = last_event.get('created_at', '')
        if timestamp:
            return format_time_from_iso(timestamp)
    
    return "00:00:00"

def calculate_chatting_time(thread):
    """Helper function to calculate total chatting time"""
    try:
        # Get start time
        start_time = None
        if thread.get('created_at'):
            start_time = datetime.strptime(thread['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            events = thread.get('events', [])
            if events:
                first_event = events[0]
                if first_event.get('created_at'):
                    start_time = datetime.strptime(first_event['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Get end time
        end_time = None
        if thread.get('ended_at'):
            end_time = datetime.strptime(thread['ended_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            events = thread.get('events', [])
            if events:
                last_event = events[-1]
                if last_event.get('created_at'):
                    end_time = datetime.strptime(last_event['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Calculate difference if both times are available
        if start_time and end_time:
            time_diff = end_time - start_time
            # Format as hours:minutes:seconds
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            seconds = int(time_diff.total_seconds() % 60)
            return f"{hours}:{minutes:02d}:{seconds:02d}"
            
    except (ValueError, TypeError, AttributeError):
        pass
    
    return "00:00:00"

def format_queued_time(seconds):
    """Helper function to format queued time in H:MM:SS format"""
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"  # Ensure 2-digit format
    except (ValueError, TypeError):
        return "00:00:00"

def get_queued_time(thread):
    """Helper function to get queued time"""
    try:
        properties = thread.get('properties', {})
        queue_time = properties.get('queue_time', 0)  # Get queue time in seconds
        return format_queued_time(queue_time)
    except (ValueError, TypeError):
        return ""

def get_came_from(thread):
    """Helper function to get the referrer URL"""
    properties = thread.get('properties', {})
    routing = properties.get('routing', {})
    
    # Try to get referrer URL
    referrer = routing.get('referrer', '')
    if referrer:
        return referrer
        
    # If no referrer found, return N/A
    return 'N/A'

def get_case_resolved(thread):
    """Helper function to extract case resolution status from post-chat form"""
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'postchat':
            for field in event.get('fields', []):
                if field.get('label', '').lower() == 'was the case resolved during the chat?':
                    answer = field.get('answer', '').strip().lower()
                    if answer == 'yes':
                        return 'Yes'
                    elif answer == 'no':
                        return 'No'
    return 'N/A'

def get_website_rating(thread):
    """Helper function to extract website rating from post-chat form"""
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'postchat':
            for field in event.get('fields', []):
                if field.get('label', '').lower() == 'how would you rate our website?':
                    answer = field.get('answer', '').strip()
                    if answer == 'User-friendly':
                        return 'User-friendly'
                    elif answer == 'Complicated':
                        return 'Complicated'
    return 'N/A'

def get_os_info(thread):
    """Helper function to extract OS information"""
    # Try to get OS info from customer's last visit
    customer = next((
        user for user in thread.get('users', [])
        if user.get('type') == 'customer'
    ), {})
    
    last_visit = customer.get('last_visit', {})
    user_agent = last_visit.get('user_agent', {})
    
    # Get OS information
    os_info = user_agent.get('operating_system', '')
    return os_info if os_info else 'N/A'

def get_browser_info(thread):
    """Helper function to extract browser information"""
    # Try to get browser info from customer's last visit
    customer = next((
        user for user in thread.get('users', [])
        if user.get('type') == 'customer'
    ), {})
    
    last_visit = customer.get('last_visit', {})
    user_agent = last_visit.get('user_agent', {})
    
    # Get browser information
    browser_info = user_agent.get('browser', '')
    return browser_info if browser_info else 'N/A'

def get_visitor_comments(thread):
    """Helper function to extract visitor's comments"""
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'postchat':
            for field in event.get('fields', []):
                if field.get('label', '').lower() == "visitor's comment":
                    comment = field.get('answer', '').strip()
                    return comment if comment else 'N/A'
    return 'N/A'

def get_device_type(browser, user_agent):
    """Helper function to determine device type based on browser and user agent"""
    if browser == "Chrome":
        return "Desktop"
    
    user_agent = user_agent.lower()
    
    if "android" in user_agent:
        return "Mobile"
    elif "ios" in user_agent:
        return "Mobile"
    elif "windows" in user_agent:
        return "Desktop"
    elif "mac os" in user_agent:
        return "Desktop"
    elif "linux" in user_agent:
        return "Desktop"
    elif "chromium os" in user_agent:
        return "Desktop"
    elif user_agent == "n/a":
        return "N/A"
    else:
        return "Unknown"

def get_device_info(thread):
    """Helper function to get device information"""
    # Try to get device info from customer's last visit
    customer = next((
        user for user in thread.get('users', [])
        if user.get('type') == 'customer'
    ), {})
    
    last_visit = customer.get('last_visit', {})
    user_agent = last_visit.get('user_agent', {})
    
    browser = user_agent.get('browser', 'N/A')
    os_info = user_agent.get('operating_system', 'N/A')
    
    return get_device_type(browser, os_info)

def get_chat_rating(thread):
    """Helper function to extract chat rating"""
    # Initialize rating as N/A
    rating = 'N/A'
    
    # Look for rating events
    for event in thread.get('events', []):
        if event.get('type') == 'rating':
            # Get rating value
            rating_value = event.get('value', 'N/A')
            if isinstance(rating_value, (int, float)):
                return str(rating_value)
            return rating_value if rating_value else 'N/A'
            
    return rating

def process_chat_to_row(chat):
    """Convert a single chat's data into a CSV row"""
    row = {}
    
    # Initialize default values
    row['Rating'] = 'Unrated'
    row['Visitor\'s Comments'] = 'No Visitor Comment'
    row['Chat Status'] = 'No Answer'
    row['Case Resolved'] = 'N/A'
    row['Website Rating'] = 'N/A'

    # Get thread data
    thread = chat.get('thread', {})
    properties = thread.get('properties', {})
    events = thread.get('events', [])
    
    # Initialize times
    started_time = None
    end_time = None
    
    # Find first and last message timestamps
    message_events = [e for e in events if e.get('type') == 'message']
    if message_events:
        started_time = message_events[0].get('created_at')
        end_time = message_events[-1].get('created_at')
    
    # Format times in PH time
    row['Started Time'] = format_time_from_iso(started_time) if started_time else '00:00:00'
    row['EndTime'] = format_time_from_iso(end_time) if end_time else '00:00:00'
    
    # Calculate Chatting Time
    if started_time and end_time:
        start_dt = datetime.strptime(started_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        chatting_time = end_dt - start_dt
        row['Chatting Time'] = str(chatting_time).split('.')[0]  # Format as HH:MM:SS
    else:
        row['Chatting Time'] = '00:00:00'

    # Format Queued Time
    row['Queued Time'] = format_queued_time(thread.get('queues_duration', 0))

    # Extract Rating and Comment from properties
    if 'rating' in properties:
        rating_data = properties['rating']
        score = rating_data.get('score', None)
        if score is not None:
            row['Rating'] = 'Rated Good' if score == 1 else 'Rated Bad'
        if 'comment' in rating_data:
            row['Visitor\'s Comments'] = rating_data['comment']

    # Extract Chat Status and Website Rating from post-chat form
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'postchat':
            for field in event.get('fields', []):
                label = field.get('label', '').lower()
                answer = field.get('answer', '')
                if isinstance(answer, dict):
                    answer = answer.get('label', '')
                
                if 'case resolved' in label:
                    row['Case Resolved'] = answer
                elif 'rate our website' in label:
                    row['Website Rating'] = answer
                elif "visitor's comment" in label:
                    row['Visitor\'s Comments'] = answer

    # Extract Rating and Comment from system messages
    for event in thread.get('events', []):
        if event.get('type') == 'system_message':
            system_type = event.get('system_message_type', '')
            if system_type == 'rating.chat_rated':
                row['Rating'] = 'Rated Good' if event.get('text', '').lower().find('good') != -1 else 'Rated Bad'
            elif system_type == 'rating.chat_commented':
                row['Visitor\'s Comments'] = event.get('text_vars', {}).get('comment', 'No Visitor Comment')

    # Basic chat info
    row['Chat ID'] = thread.get('id', 'N/A')
    contact_date = thread.get('created_at', 'N/A')
    if contact_date != 'N/A':
        try:
            # Convert to datetime, add 8 hours, and format
            dt = datetime.strptime(contact_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            ph_time = dt + timedelta(hours=8)
            row['Contact Date'] = ph_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            row['Contact Date'] = 'N/A'
    else:
        row['Contact Date'] = 'N/A'
    
    # Customer info
    customer = next((user for user in chat.get('users', []) if user.get('type') == 'customer'), {})
    row['Lead Name'] = customer.get('name', 'N/A')
    row['Lead Email'] = customer.get('email', 'N/A')
    
    # Location info
    location = customer.get('last_visit', {}).get('geolocation', {})
    row['Lead Address'] = f"{location.get('city', '')}, {location.get('region', '')}, {location.get('country', '')}"
    row['Lead Country'] = location.get('country', 'N/A')
    
    # Website info
    routing = thread.get('properties', {}).get('routing', {})
    row['Website Origin'] = routing.get('start_url', 'N/A')
    row['Came from'] = routing.get('referrer', 'N/A')
    row['Website'] = routing.get('start_url', '').split('/')[2] if routing.get('start_url') else 'N/A'
    
    # Agent info
    agent = next((user for user in chat.get('users', []) if user.get('type') == 'agent'), {})
    row['Agent Alias'] = agent.get('name', 'Unassigned')
    row['Agent Name'] = get_agent_full_name(agent.get('name', 'Unassigned'))
    
    # Technology info
    last_visit = customer.get('last_visit', {})
    user_agent = last_visit.get('user_agent', '')
    
    # OS/Device detection
    
    if 'iPhone' in user_agent or 'iOS' in user_agent:
        row['OS'] = 'iOS'
        row['Device'] = 'Mobile'
    elif 'Android' in user_agent:
        row['OS'] = 'Android'
        row['Device'] = 'Mobile'
    else:
        row['OS'] = 'Desktop'
        row['Device'] = 'Desktop'
    
    # Browser detection
    if 'Chrome' in user_agent:
        row['Browser'] = 'Chrome'
    elif 'Safari' in user_agent:
        row['Browser'] = 'Safari'
    elif 'Firefox' in user_agent:
        row['Browser'] = 'Firefox'
    else:
        row['Browser'] = 'Other'
    
    # Add conversation history with name tagging
    conversation = []
    for event in thread.get('events', []):
        if event.get('type') == 'message':
            author = next((user for user in chat.get('users', []) if user.get('id') == event.get('author_id')), {})
            author_type = author.get('type', 'unknown')
            author_name = author.get('name', 'Unknown')
            
            # Get message text directly from the event
            message_text = event.get('text', '')
            
            # Format based on author type
            if author_type == 'agent':
                conversation.append(f"Agent ({author_name}): {message_text}")
            elif author_type == 'customer':
                conversation.append(f"Client ({author_name}): {message_text}")
            else:
                conversation.append(f"System ({author_name}): {message_text}")
    
    row['Conversation'] = "\n".join(conversation) if conversation else 'No conversation'
    
    # Look for pre-chat form
    for event in thread.get('events', []):
        if event.get('type') == 'filled_form' and event.get('form_type') == 'prechat':
            for field in event.get('fields', []):
                if field.get('label', '') == 'Question:':
                    answer = field.get('answer', {})
                    if isinstance(answer, dict):
                        row['Chat Status'] = answer.get('label', 'No Answer')
                    else:
                        row['Chat Status'] = answer if answer else 'No Answer'
                    break

    return row

def download_chat_transcript(account_id, token, chat_id=None, output_file=None, custom_range=False):
    """Download and process chat transcripts directly to CSV"""
    # Define output directory
    output_dir = r"C:\Users\PM Shift\OneDrive\sc-v1\livechat_raw"
    os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
    
    # Get date range based on user preference
    if custom_range:
        from_date, to_date = get_custom_date_range()
    else:
        from_date, to_date = get_date_range()
    
    print(f"\nFetching chats from {from_date} to {to_date}")
    
    # Save raw chat data to the specified directory
    raw_chats_file = os.path.join(output_dir, 'raw_chats_data.json')
    
    # Generate output CSV filename with timestamp in the specified directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_file:
        output_file = os.path.join(output_dir, f'chat_transcript_{timestamp}.csv')

    all_chats = []
    page_id = None
    total_chats = 0

    try:
        # API endpoint and headers setup
        url = "https://api.livechatinc.com/v3.5/agent/action/list_archives"
        auth_string = base64.b64encode(f"{account_id}:{token}".encode('utf-8')).decode('utf-8')
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json',
            'User-Agent': 'sc-v1/1.0 (+https://livechatinc.com)'
        }
        
        if token.startswith(('dal:', 'fra:')):
            region = token.split(':')[0]
            headers['X-Region'] = region
            print(f"Using region: {region}")

        # Configure a resilient session with retries/backoff
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            connect=5,
            read=5,
            status=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504, 520, 521, 522, 524),
            allowed_methods={"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"},
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        # Fetch all chats and save raw data
        while True:
            if page_id:
                payload = {"page_id": page_id}
            else:
                payload = {
                    "filters": {
                        "from": from_date,
                        "to": to_date
                    },
                    "limit": 100
                }

            print(f"\nFetching chats (current total: {total_chats})...")
            try:
                response = session.post(url, headers=headers, json=payload, timeout=(10, 60))
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, RemoteDisconnected) as net_err:
                print(f"\nNetwork error during request: {net_err}. Retrying via configured backoff...")
                # Trigger a retry by performing a second attempt which the session/adapter will manage
                response = session.post(url, headers=headers, json=payload, timeout=(10, 60))
            
            if response.status_code != 200:
                print(f"\nError Details:")
                print(f"Status Code: {response.status_code}")
                print(f"Response Body: {response.text}")
                return False
                
            data = response.json()
            chats = data.get('chats', [])
            
            if not chats:
                break
                
            all_chats.extend(chats)
            total_chats = len(all_chats)
            
            if 'next_page_id' not in data:
                break
                
            page_id = data['next_page_id']

        # Save raw data
        with open(raw_chats_file, 'w', encoding='utf-8') as f:
            json.dump(all_chats, f, indent=2)

        print(f"\nTotal chats found: {total_chats}")
        print(f"Raw chat data saved to: {raw_chats_file}")

        if total_chats == 0:
            print("\nNo chats found in the specified date range.")
            return True

        # Process chats directly to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f'chat_transcript_{timestamp}.csv')

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'Contact Date', 'Agent Alias', 'Agent Name', 'Chat ID', 
                'Lead Name', 'Lead Email', 'Lead Address', 'Lead Country', 
                'Rating', 'Chat Status', 'Website Origin', 'Website', 
                'Campaign', 'Started Time', 'EndTime', 'Chatting Time', 
                'Queued Time', 'Came from', 'Case Resolved', 'Website Rating',
                'OS', 'Browser', 'Visitor\'s Comments', 'Device',
                'Conversation'
            ])
            writer.writeheader()
            
            for chat in all_chats:
                row = process_chat_to_row(chat)
                writer.writerow(row)

        return True

    except Exception as e:
        print(f"\nError: {e}")
        return False

def process_raw_chats(raw_chats_file, output_file):
    """Second phase: Transform JSON data into text format then CSV"""
    # Define output directory
    output_dir = r"C:\Users\PM Shift\OneDrive\sc-v1\livechat_raw"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(raw_chats_file, 'r', encoding='utf-8') as f:
        chats = json.load(f)
    
    # Generate output filename with timestamp if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f'chat_transcript_{timestamp}.csv')

    # First convert to text format (like the working .txt version)
    formatted_chats = []
    for chat in chats:
        formatted_chat = format_chat_to_text(chat)
        formatted_chats.append(formatted_chat)
    
    # Now process the formatted text into CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            'Contact Date', 'Agent Alias', 'Agent Name', 'Chat ID', 
            'Lead Name', 'Lead Email', 'Lead Address', 'Lead Country', 
            'Rating', 'Chat Status', 'Website Origin', 'Website', 
            'Campaign', 'Started Time', 'EndTime', 'Chatting Time', 
            'Queued Time', 'Came from', 'Case Resolved', 'Website Rating',
            'OS', 'Browser', 'Visitor\'s Comments', 'Device',
            'Conversation'
        ])
        writer.writeheader()
        
        for formatted_chat in formatted_chats:
            row = extract_chat_data(formatted_chat)
            writer.writerow(row)

def format_chat_to_text(chat):
    """Convert a chat JSON object to text format (like the working .txt version)"""
    text = []
    text.append("="*50)
    text.append(f"Chat ID: {chat['id']}")
    text.append("-"*30)
    text.append("\nDetails\n----------")
    
    # Add General info
    customer = next((u for u in chat['users'] if u['type'] == 'customer'), {})
    text.append("\nGeneral info")
    text.append(customer.get('name', 'N/A'))
    text.append(customer.get('email', 'N/A'))
    
    # Add location
    location = customer.get('last_visit', {}).get('geolocation', {})
    address = f"{location.get('city', '')}, {location.get('region', '')}, {location.get('country', '')}"
    text.append(address)
    
    # Add other sections...
    # ... continue formatting all other data like the .txt version
    
    return "\n".join(text)

def extract_chat_data(formatted_chat):
    """Extract data from formatted text into CSV row"""
    # Use the same parsing logic that worked in the .txt version
    row = {}
    # ... extract all fields from the formatted text
    return row

# Modified main section
if __name__ == "__main__":
    print("LiveChat Transcript Downloader")
    print("-" * 30)
    
    print("\nIMPORTANT: You'll need both your Account ID and Personal Access Token")
    print("1. Account ID can be found in the LiveChat Console URL or Developer Console")
    print("2. Personal Access Token from Developer Console")
    
    ACCOUNT_ID = input("\nPlease enter your Account ID: ").strip()
    TOKEN = input("Please enter your Personal Access Token: ").strip()
    
    if not ACCOUNT_ID or not TOKEN:
        print("\nError: Both Account ID and Token are required")
        exit(1)
    
    # Ask user for date range preference
    while True:
        choice = input("\nWould you like to:\n1. Download last 7 days\n2. Specify custom date range\nEnter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    print("\nAttempting to download transcripts...")
    download_chat_transcript(ACCOUNT_ID, TOKEN, custom_range=(choice == '2'))
    
    # Convert UTC to Philippine Time (+8 hours)
    def convert_to_ph_time(utc_time_str):
        utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        ph_time = utc_time + timedelta(hours=8)
        return ph_time.strftime("%H:%M:%S")

    # Example usage for the archived time
    archived_time = "2025-02-08T04:09:11.004001Z"
    ph_archived_time = convert_to_ph_time(archived_time)

    # For QueuedTime, convert to the same format
    queued_time = "00:00:00"  # Replace with your actual QueuedTime value
    formatted_queued_time = queued_time  # Already in the correct format
    
    