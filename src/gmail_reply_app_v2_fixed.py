import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import base64
import os
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import requests
import re

# Charger les variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

USER_ID = "me"
KEYWORDS = ["formation", "gardiennage", "prix", "intéressé par la formation"]
IGNORED_SENDERS = ["academie@academiexguard.ca", "d.oliveira@academiexguard.ca"]

def authenticate():
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/gmail.modify"])
    service = build("gmail", "v1", credentials=creds)
    return service

def list_messages(service, user_id):
    response = service.users().messages().list(userId=user_id, maxResults=10).execute()
    messages = []
    if "messages" in response:
        for msg in response["messages"]:
            msg_data = service.users().messages().get(userId=user_id, id=msg["id"], format="full").execute()
            payload = msg_data["payload"]
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                            break
            elif "body" in payload and "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            messages.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "body": body,
            })
    return messages

def message_contains_keywords(msg):
    return any(kw.lower() in msg["body"].lower() for kw in KEYWORDS)

def generate_reply(body):
    prompt = f"Un client a écrit : {body}\n\nRédige une réponse professionnelle et rassurante pour XGuard Formation."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un assistant du service client."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Erreur lors de la génération : {str(e)}"

class GmailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gmail Reply App")
        self.service = authenticate()
        self.ignored_threads = set()

        self.tree = ttk.Treeview(root, columns=("from", "subject"), show="headings")
        self.tree.heading("from", text="De")
        self.tree.heading("subject", text="Sujet")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.display_selected)

        self.textbox = scrolledtext.ScrolledText(root, height=12)
        self.textbox.pack(fill="both", padx=4, pady=4)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=4)

        tk.Button(btn_frame, text="✅ Confirmer", command=self.confirm).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📝 Modifier", command=self.edit).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔁 Rafraîchir", command=self.refresh_messages).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🚫 Ignorer", command=self.ignore).pack(side="left", padx=5)
        tk.Button(btn_frame, text="❌ Toujours ignorer", command=self.ignore_forever).pack(side="left", padx=5)

        self.messages = []
        self.refresh_messages()

    def refresh_messages(self):
        self.messages = [msg for msg in list_messages(self.service, USER_ID)
                         if message_contains_keywords(msg)
                         and msg["from"] not in IGNORED_SENDERS
                         and msg["id"] not in self.ignored_threads]
        self.tree.delete(*self.tree.get_children())
        for i, msg in enumerate(self.messages):
            self.tree.insert("", "end", iid=i, values=(msg["from"], msg["subject"]))

    def display_selected(self, event):
        selected = self.tree.focus()
        if selected:
            msg = self.messages[int(selected)]
            suggestion = generate_reply(msg["body"])
            self.textbox.delete("1.0", tk.END)
            self.textbox.insert(tk.END, suggestion)

    def confirm(self):
        messagebox.showinfo("Envoyé", "Réponse confirmée. (À brancher si tu veux envoyer)")

    def edit(self):
        messagebox.showinfo("Modifier", "Tu peux modifier manuellement le texte.")

    def ignore(self):
        selected = self.tree.focus()
        if selected:
            msg = self.messages[int(selected)]
            self.ignored_threads.add(msg["id"])
            self.refresh_messages()

    def ignore_forever(self):
        selected = self.tree.focus()
        if selected:
            msg = self.messages[int(selected)]
            sender = msg["from"]
            parsed_email = re.findall(r"<(.*?)>", sender)
            if parsed_email:
                sender = parsed_email[0]
            IGNORED_SENDERS.append(sender)
            self.refresh_messages()

if __name__ == "__main__":
    root = tk.Tk()
    app = GmailApp(root)
    root.mainloop()