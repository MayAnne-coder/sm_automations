import base64
import csv
import json
import os
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

API_BASE = "https://api.helpdesk.com/v1"
OUTPUT_DIR = r"C:\Users\PM Shift\OneDrive\sc-v1\helpdesk_raw"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_session(account_id: str, token: str) -> requests.Session:
    """
    Create a resilient HTTP session with Basic auth for HelpDesk API.
    """
    auth_string = base64.b64encode(f"{account_id}:{token}".encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_string}",
        "User-Agent": "sc-v1/1.0 (+https://helpdesk.com)",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"},
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(headers)
    return session


def fetch_all_tickets(
    session: requests.Session,
    silo: str | None = None,
) -> list[dict]:
    """
    Fetch tickets from HelpDesk API.

    NOTE:
    - This uses a generic pattern that should work with many list endpoints:
      * GET /v1/tickets?limit=...
      * If the response is a list, we take it as-is.
      * If the response is an object, we look for keys like 'tickets' or 'items',
        and for pagination cursors like 'nextCursor' or meta.nextCursor.

    If your account has many tickets, you may want to:
    - Add proper server-side filters (created date, status, silo, etc.)
    - Follow the exact cursor pagination described in the HelpDesk docs.
    """
    url = f"{API_BASE}/tickets"
    all_tickets: list[dict] = []

    page = 1
    total_pages = None

    while True:
        params = {"page": page}
        if silo:
            params["silo"] = silo

        print(
            f"Requesting tickets page {page} "
            f"(silo: {silo or 'tickets'}, current total: {len(all_tickets)})..."
        )
        resp = session.get(url, params=params, timeout=(10, 60))

        if resp.status_code != 200:
            print(f"\nError fetching tickets:")
            print(f"Status: {resp.status_code}")
            print(f"Body:   {resp.text}")
            # Save full error response to a file for inspection
            try:
                ensure_output_dir()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_path = os.path.join(OUTPUT_DIR, f"helpdesk_error_{ts}.txt")
                with open(error_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {resp.url}\n")
                    f.write(f"Status: {resp.status_code}\n")
                    f.write("Headers:\n")
                    for k, v in resp.headers.items():
                        f.write(f"{k}: {v}\n")
                    f.write("\nBody:\n")
                    f.write(resp.text)
                print(f"Full error details saved to: {error_path}")
            except Exception as e:
                print(f"Failed to save error details: {e}")
            break

        data = resp.json()

        # On the first page, capture total_pages from headers (x-total-pages)
        if total_pages is None:
            header_val = resp.headers.get("x-total-pages")
            try:
                total_pages = int(header_val) if header_val is not None else 1
            except ValueError:
                total_pages = 1

        # Handle response shape (tickets list)
        if isinstance(data, list):
            batch = data
        else:
            batch = data.get("tickets") or data.get("items") or []

        if not batch:
            break

        all_tickets.extend(batch)

        # Stop when we've fetched all pages
        if page >= (total_pages or 1):
            break

        page += 1

    print(f"\nTotal tickets fetched: {len(all_tickets)}")
    return all_tickets


def parse_iso(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def filter_by_last_n_days(tickets: list[dict], days: int) -> list[dict]:
    """
    Filter tickets by createdAt in the last N days (client-side).
    """
    if days <= 0:
        return tickets

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = []

    for t in tickets:
        created_at = t.get("createdAt") or t.get("created_at")
        dt = parse_iso(created_at) if created_at else None
        if dt and dt >= cutoff:
            filtered.append(t)

    print(f"Tickets after last-{days}-days filter: {len(filtered)}")
    return filtered


def filter_by_date_range(
    tickets: list[dict], start_dt: datetime, end_dt: datetime
) -> list[dict]:
    """
    Filter tickets whose createdAt falls within [start_dt, end_dt].
    """
    filtered: list[dict] = []

    for t in tickets:
        created_at = t.get("createdAt") or t.get("created_at")
        dt = parse_iso(created_at) if created_at else None
        if dt and start_dt <= dt <= end_dt:
            filtered.append(t)

    print(
        f"Tickets after custom date range "
        f"({start_dt.isoformat()} to {end_dt.isoformat()}): {len(filtered)}"
    )
    return filtered


def build_conversation(ticket: dict) -> str:
    """
    Build a simple text transcript from ticket events.
    """
    lines: list[str] = []
    for event in ticket.get("events", []):
        if event.get("type") != "message":
            continue

        author = event.get("author", {}) or {}
        author_type = (author.get("type") or "").capitalize()
        author_name = author.get("name") or author.get("email") or ""

        message = event.get("message", {}) or {}
        text = message.get("text") or ""

        if not text and not author_name:
            continue

        prefix = author_type or "Author"
        if author_name:
            line = f"{prefix} ({author_name}): {text}"
        else:
            line = f"{prefix}: {text}"

        lines.append(line)

    return "\n".join(lines)


def ticket_to_row(ticket: dict) -> dict:
    """
    Map a HelpDesk ticket JSON object to a flat CSV row.

    This is intentionally defensive: it uses .get and supports a few common shapes.
    After your first run, open the raw JSON and adjust field names if needed.
    """
    # Top-level fields / meta
    ticket_id = ticket.get("ID") or ticket.get("id")
    license_id = ticket.get("licenseID")
    short_id = ticket.get("shortID", "")
    ticket_silo = ticket.get("silo", "")

    created_at = ticket.get("createdAt") or ticket.get("created_at") or ""
    created_by = ticket.get("createdBy", "")
    created_by_type = ticket.get("createdByType", "")

    updated_at = ticket.get("updatedAt") or ticket.get("updated_at") or ""
    updated_by = ticket.get("updatedBy", "")

    last_message_at = ticket.get("lastMessageAt", "")

    parent_ticket = ticket.get("parentTicket")
    child_tickets = ticket.get("childTickets") or []
    if isinstance(child_tickets, list):
        child_ticket_ids = ", ".join(str(ct) for ct in child_tickets)
    else:
        child_ticket_ids = str(child_tickets)

    status = ticket.get("status", "")
    priority = ticket.get("priority", "")
    subject = ticket.get("subject", "")

    # Teams / assignment
    team_ids = ticket.get("teamIDs") or []
    if isinstance(team_ids, list):
        team_ids_str = ", ".join(str(tid) for tid in team_ids)
    else:
        team_ids_str = str(team_ids)

    assignment = ticket.get("assignment") or {}
    assigned_team = assignment.get("team") or {}
    assigned_agent = assignment.get("agent") or {}

    assigned_team_id = assigned_team.get("ID", "")
    assigned_team_name = assigned_team.get("name", "")

    assigned_agent_id = assigned_agent.get("ID", "")
    assigned_agent_name = assigned_agent.get("name", "")

    # Requester / customer info
    requester = ticket.get("requester") or ticket.get("requesterUser") or {}
    requester_email = (
        requester.get("email")
        or requester.get("Email")
        or ticket.get("requesterEmail")
        or ""
    )
    requester_name = (
        requester.get("name")
        or requester.get("Name")
        or ticket.get("requesterName")
        or ""
    )

    # CC / followers
    cc_list = ticket.get("cc") or []
    if isinstance(cc_list, list):
        cc_emails = ", ".join(str(c) for c in cc_list)
    else:
        cc_emails = str(cc_list)

    followers = ticket.get("followers") or []
    followers_count = len(followers) if isinstance(followers, list) else 0

    # Tags (note: HelpDesk uses tagIDs for IDs; we also support any 'tags' list)
    tags = ticket.get("tags") or ticket.get("tagIDs") or []
    if isinstance(tags, list):
        tags_str = ", ".join(str(t) for t in tags)
    else:
        tags_str = str(tags)

    # Spam
    spam = ticket.get("spam") or {}
    spam_status = spam.get("status")
    spam_reason = spam.get("reason", "")

    # Rating
    rating_obj = ticket.get("rating") or {}
    rating_score = rating_obj.get("score")
    rating_comment = rating_obj.get("comment", "")
    if rating_score is None:
        rating_status = ""
    elif rating_score > 0:
        rating_status = "good"
    elif rating_score < 0:
        rating_status = "bad"
    else:
        rating_status = "neutral"

    rating_request_sent = bool(ticket.get("ratingRequestSent", False))

    # Source / integration / language / delivery
    source = ticket.get("source") or {}
    source_type = source.get("type", "")
    source_integration_type = source.get("integrationType", "")
    source_reference_url = source.get("referenceURL", "")
    source_reference_reason = source.get("referenceReason", "")
    source_reference_reason_at = source.get("referenceReasonAt", "")
    source_detailed = source.get("detailedSource", "")
    integration_customer_id = source.get("customerID", "")

    detected_language = ticket.get("detectedLanguage", "")
    delivery_status_overall = ticket.get("deliveryStatus", "")

    # Conversation transcript and simple message stats
    conversation = build_conversation(ticket)
    total_messages = 0
    client_messages = 0
    agent_messages = 0
    for event in ticket.get("events", []):
        if event.get("type") == "message":
            total_messages += 1
            author_type = (event.get("author", {}) or {}).get("type")
            if author_type == "client":
                client_messages += 1
            elif author_type == "agent":
                agent_messages += 1

    return {
        # Core IDs and meta
        "ticket_id": ticket_id,
        "license_id": license_id,
        "short_id": short_id,
        "created_at": created_at,
        "created_by": created_by,
        "created_by_type": created_by_type,
        "updated_at": updated_at,
        "updated_by": updated_by,
        "last_message_at": last_message_at,
        "parent_ticket": parent_ticket,
        "child_ticket_ids": child_ticket_ids,
        "silo": ticket_silo,
        # Status / priority / subject
        "status": status,
        "priority": priority,
        "subject": subject,
        # Teams / assignment
        "team_ids": team_ids_str,
        "assigned_team_id": assigned_team_id,
        "assigned_team_name": assigned_team_name,
        "assigned_agent_id": assigned_agent_id,
        "assigned_agent_name": assigned_agent_name,
        # Requester / CC / followers
        "requester_email": requester_email,
        "requester_name": requester_name,
        "cc_emails": cc_emails,
        "followers_count": followers_count,
        # Tags / spam
        "tags": tags_str,
        "spam_status": spam_status,
        "spam_reason": spam_reason,
        # Rating
        "rating_score": rating_score,
        "rating_status": rating_status,
        "rating_comment": rating_comment,
        "rating_request_sent": rating_request_sent,
        # Source / integration
        "source_type": source_type,
        "source_integration_type": source_integration_type,
        "source_reference_url": source_reference_url,
        "source_reference_reason": source_reference_reason,
        "source_reference_reason_at": source_reference_reason_at,
        "source_detailed": source_detailed,
        "integration_customer_id": integration_customer_id,
        # Language / delivery
        "language": detected_language,
        "delivery_status_overall": delivery_status_overall,
        # Conversation & simple stats
        "total_messages": total_messages,
        "client_messages": client_messages,
        "agent_messages": agent_messages,
        "conversation": conversation,
    }


def save_csv(tickets: list[dict], timestamp: str) -> str:
    csv_path = os.path.join(OUTPUT_DIR, f"helpdesk_tickets_{timestamp}.csv")
    fieldnames = [
        # Core IDs and meta
        "ticket_id",
        "license_id",
        "short_id",
        "created_at",
        "created_by",
        "created_by_type",
        "updated_at",
        "updated_by",
        "last_message_at",
        "parent_ticket",
        "child_ticket_ids",
        "silo",
        # Status / priority / subject
        "status",
        "priority",
        "subject",
        # Teams / assignment
        "team_ids",
        "assigned_team_id",
        "assigned_team_name",
        "assigned_agent_id",
        "assigned_agent_name",
        # Requester / CC / followers
        "requester_email",
        "requester_name",
        "cc_emails",
        "followers_count",
        # Tags / spam
        "tags",
        "spam_status",
        "spam_reason",
        # Rating
        "rating_score",
        "rating_status",
        "rating_comment",
        "rating_request_sent",
        # Source / integration
        "source_type",
        "source_integration_type",
        "source_reference_url",
        "source_reference_reason",
        "source_reference_reason_at",
        "source_detailed",
        "integration_customer_id",
        # Language / delivery
        "language",
        "delivery_status_overall",
        # Conversation & simple stats
        "total_messages",
        "client_messages",
        "agent_messages",
        "conversation",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tickets:
            row = ticket_to_row(t)
            writer.writerow(row)

    print(f"CSV saved to: {csv_path}")
    return csv_path


def main():
    print("HelpDesk Tickets → CSV")
    print("-" * 30)

    ensure_output_dir()

    # Try to read credentials from environment variables first (recommended)
    env_account_id = os.environ.get("HELPDESK_ACCOUNT_ID", "").strip()
    env_token = os.environ.get("HELPDESK_PAT", "").strip()

    if env_account_id and env_token:
        print("Using HelpDesk credentials from environment variables (HELPDESK_ACCOUNT_ID / HELPDESK_PAT).")
        account_id = env_account_id
        token = env_token
    else:
        account_id = input("Enter your HelpDesk account_id (from Developers Console): ").strip()
        token = input("Enter your HelpDesk Personal Access Token: ").strip()

    if not account_id or not token:
        print("Error: Both account_id and token are required.")
        return

    # Folder (silo) option
    print("\nChoose folder (silo) to export:")
    print("1. Active tickets (silo: tickets)")
    print("2. Archive (silo: archive)")
    print("3. Spam (silo: spam)")
    print("4. Trash (silo: trash)")
    print("5. All silos (tickets, archive, spam, trash)")
    silo_choice = input("Enter 1, 2, 3, 4 or 5: ").strip()

    if silo_choice == "1":
        silos = ["tickets"]
    elif silo_choice == "2":
        silos = ["archive"]
    elif silo_choice == "3":
        silos = ["spam"]
    elif silo_choice == "4":
        silos = ["trash"]
    elif silo_choice == "5":
        silos = ["tickets", "archive", "spam", "trash"]
    else:
        print("Unrecognized choice, defaulting to active tickets (silo: tickets).")
        silos = ["tickets"]

    # Date range option (client-side filter)
    print("\nChoose date range:")
    print("1. Last 7 days (by createdAt)")
    print("2. Custom date range (by createdAt)")
    print("3. All tickets returned by the API")
    choice = input("Enter 1, 2 or 3: ").strip()

    use_last_7_days = choice == "1"
    use_custom_range = choice == "2"

    session = create_session(account_id, token)

    # Fetch tickets from selected silos
    tickets: list[dict] = []
    for silo in silos:
        print(f"\nFetching tickets from silo: {silo}")
        silo_tickets = fetch_all_tickets(session, silo=silo if silo != "tickets" else None)
        # Ensure silo is set on each ticket for clarity
        for t in silo_tickets:
            if not t.get("silo"):
                t["silo"] = silo
        tickets.extend(silo_tickets)

    if use_last_7_days:
        tickets = filter_by_last_n_days(tickets, 7)
    elif use_custom_range:
        while True:
            print("\nEnter custom date range in UTC (format: YYYY-MM-DD)")
            start_str = input("Start date: ").strip()
            end_str = input("End date: ").strip()

            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_str, "%Y-%m-%d")

                # Set to full days in UTC
                start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

                if end_dt < start_dt:
                    print("End date must be on or after start date. Please try again.")
                    continue

                tickets = filter_by_date_range(tickets, start_dt, end_dt)
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.")
                continue

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_csv(tickets, timestamp)

    print("\nDone.")


if __name__ == "__main__":
    main()