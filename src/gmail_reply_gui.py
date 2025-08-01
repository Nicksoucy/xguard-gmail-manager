import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from dotenv import load_dotenv
import os
import base64
import requests
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
USER_ID = "me"

KEYWORDS = ["formation", "gardiennage", "prix", "intéressé par la formation"]
EXCLUDED_SENDERS = ["academie@academiexguard.ca", "d.oliveira@academiexguard.ca"]
EXCLUDED_SUBJECT_PHRASES = ["Confirmation d'inscription"]

def refresh_access_token():
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    r = requests.post(token_url, data=payload)
    return r.json().get("access_token")

def build_gmail_service():
    creds = Credentials(token=refresh_access_token())
    return build("gmail", "v1", credentials=creds)

def get_latest_messages():
    service = build_gmail_service()
    results = service.users().messages().list(userId=USER_ID, maxResults=15).execute()
    messages = results.get("messages", [])
    filtered = []
    for m in messages:
        msg = service.users().messages().get(userId=USER_ID, id=m["id"]).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        snippet = msg.get("snippet", "")
        if any(sender.lower().startswith(ex.lower()) for ex in EXCLUDED_SENDERS):
            continue
        if any(phrase.lower() in subject.lower() for phrase in EXCLUDED_SUBJECT_PHRASES):
            continue
        if any(k.lower() in snippet.lower() for k in KEYWORDS):
            filtered.append({
                "id": m["id"],
                "subject": subject,
                "from": sender,
                "snippet": snippet,
            })
        if len(filtered) >= 5:
            break
    return filtered

def generate_reply(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Voici un message reçu : {prompt}\n\nPropose une réponse polie, utile et orientée vers la vente pour XGuard Formation."
            }],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Erreur GPT : {e}"

class GmailApp:
    def __init__(self, root):
        self.root = root
        root.title("Gmail Reply App")

        self.tree = ttk.Treeview(root, columns=("De", "Sujet"), show="headings")
        self.tree.heading("De", text="De")
        self.tree.heading("Sujet", text="Sujet")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.reply_box = scrolledtext.ScrolledText(root, height=10)
        self.reply_box.pack(fill=tk.X, padx=10, pady=5)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="✅ Confirmer", command=self.confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="📝 Modifier", command=self.modify).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="🔄 Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.messages = []
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.messages = get_latest_messages()
        for i, m in enumerate(self.messages):
            self.tree.insert("", "end", iid=str(i), values=(m["from"], m["subject"]))
        self.reply_box.delete("1.0", tk.END)

    def on_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        msg = self.messages[int(selected)]
        suggestion = generate_reply(msg["snippet"])
        self.reply_box.delete("1.0", tk.END)
        self.reply_box.insert(tk.END, suggestion)

    def confirm(self):
        messagebox.showinfo("Envoyé", "Réponse confirmée. (À automatiser plus tard)")
        self.reply_box.delete("1.0", tk.END)

    def modify(self):
        messagebox.showinfo("Modifier", "Tu peux modifier la réponse manuellement dans la boîte ci-dessus.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GmailApp(root)
    root.mainloop()