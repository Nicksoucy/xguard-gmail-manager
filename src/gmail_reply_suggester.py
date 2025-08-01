gmail_reply_suggester.py

import os
import base64
import requests
import openai
import datetime
from dotenv import load_dotenv
from email.utils import parseaddr
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- CHARGER VARIABLES ---------- #
load_dotenv()
CLIENT_ID      = os.getenv("CLIENT_ID")
CLIENT_SECRET  = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN  = os.getenv("REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("SHEET_ID")
USER_ID = "me"

openai.api_key = OPENAI_API_KEY

KEYWORDS = ["formation", "gardiennage", "prix", "intéressé par la formation"]

# ---------- GMAIL ---------- #
def refresh_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def get_gmail_service():
    creds = Credentials(
        token=refresh_token(),
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return build("gmail", "v1", credentials=creds)

def extract_text(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload["body"] and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""

# ---------- SHEET ---------- #
def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1

# ---------- CHATGPT ---------- #
def generate_reply(text):
    prompt = f"""Tu es un conseiller pour une école de formation en sécurité. Génère une réponse polie et rassurante à ce message, qui semble vouloir des infos sur la formation :\n\n{text}"""
    result = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    return result.choices[0].message.content.strip()

# ---------- MAIN ---------- #
def main():
    service = get_gmail_service()
    sheet = get_sheet()

    results = service.users().messages().list(userId=USER_ID, q="is:unread", maxResults=10).execute()
    messages = results.get("messages", [])

    if not messages:
        print("✅ Aucun courriel non lu détecté.")
        return

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        msg = service.users().messages().get(userId=USER_ID, id=msg_id, format="full").execute()
        payload = msg["payload"]
        headers = {h["name"]: h["value"] for h in payload["headers"]}
        sender_name, sender_email = parseaddr(headers.get("From", ""))
        subject = headers.get("Subject", "(Aucun sujet)")
        body = extract_text(payload)

        if not body:
            continue

        if any(k in body.lower() for k in KEYWORDS):
            suggested_reply = generate_reply(body)
            detected = ", ".join(k for k in KEYWORDS if k in body.lower())
            now = datetime.datetime.now().strftime("%Y-%m-%d")

            sheet.append_row([
                now, msg_id, sender_name, sender_email,
                subject, body, detected,
                "formation", suggested_reply,
                "À valider", "", "", "Oui"
            ])
            print(f"📝 Suggestion ajoutée pour : {sender_email}")

if __name__ == "__main__":
    main()
