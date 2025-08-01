import os
import base64
import datetime
import requests
import openai
import gspread

from dotenv import load_dotenv
from email.utils import parseaddr
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------- 0. Config ---------- #
load_dotenv()
CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHEET_ID = "19R0THrBOMCWafXHf_X9DQJNnvvmbhLGMwX5TU84abq8"
USER_ID = "me"

KEYWORDS = ["formation", "gardiennage", "prix", "intéressé par la formation"]
IGNORED_SENDERS = {"d.oliveira@academiexguard.ca", "academie@academiexguard.ca"}

openai.api_key = OPENAI_API_KEY

# ---------- 1. Gmail Auth ---------- #
def refresh_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def gmail_service():
    creds = Credentials(token=refresh_access_token(),
                        refresh_token=REFRESH_TOKEN,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET)
    return build("gmail", "v1", credentials=creds)

# ---------- 2. Helpers ---------- #
def extract_text(payload):
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part["body"].get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""

def generate_reply(body):
    prompt = f"""Tu es le service à la clientèle pour une école de formation en sécurité privée au Québec.

Voici le message d’un client :
---
{body}
---

Écris une réponse professionnelle, claire et rassurante, en français. Si la personne est intéressée à acheter, aide-la à comprendre quoi faire ensuite (ex. s'inscrire, payer, etc.)."""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()

def move_to_label(service, msg_id, label_name="Élite"):
    # Crée le label s’il n’existe pas encore
    labels = service.users().labels().list(userId=USER_ID).execute().get("labels", [])
    label_id = next((l["id"] for l in labels if l["name"].lower() == label_name.lower()), None)
    if not label_id:
        label = service.users().labels().create(userId=USER_ID, body={"name": label_name}).execute()
        label_id = label["id"]
    # Applique le label
    service.users().messages().modify(
        userId=USER_ID,
        id=msg_id,
        body={"addLabelIds": [label_id]}
    ).execute()

# ---------- 3. GSheet Auth ---------- #
def gsheet_append_row(row):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    worksheet = sheet.worksheet("Feuille 1")
    worksheet.append_row(row)

# ---------- 4. Main ---------- #
def main():
    service = gmail_service()
    results = service.users().messages().list(userId=USER_ID, q="is:unread", maxResults=5).execute()
    messages = results.get("messages", [])

    if not messages:
        print("📭 Aucun message non lu trouvé.")
        return

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        msg = service.users().messages().get(userId=USER_ID, id=msg_id, format="full").execute()
        payload = msg["payload"]
        headers = payload.get("headers", [])

        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(aucun sujet)")
        sender_name, sender_email = parseaddr(sender)

        if sender_email.lower() in IGNORED_SENDERS:
            print(f"⏭️ Ignoré : expéditeur exclu ({sender_email})")
            if sender_email.lower() == "d.oliveira@academiexguard.ca":
                move_to_label(service, msg_id, label_name="Élite")
            continue

        if subject.lower().startswith("confirmation d'inscription"):
            print(f"⏭️ Ignoré : sujet exclu pour {sender_email}")
            continue

        body = extract_text(payload)
        if not any(kw in body.lower() for kw in KEYWORDS):
            print(f"⏭️ Ignoré : aucun mot-clé dans le message de {sender_email}")
            continue

        reply = generate_reply(body)
        detected = [kw for kw in KEYWORDS if kw in body.lower()]
        category = detected[0] if detected else ""
        now = datetime.datetime.now().strftime("%Y-%m-%d")

        gsheet_append_row([
            now,
            msg_id,
            sender_name,
            sender_email,
            subject,
            body,
            ", ".join(detected),
            category,
            reply,
            "À valider",
            "", "", "Oui"
        ])
        print(f"✅ Suggestion ajoutée pour {sender_email}")

if __name__ == "__main__":
    main()
