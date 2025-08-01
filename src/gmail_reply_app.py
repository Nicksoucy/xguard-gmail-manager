import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests, base64
import openai

def load_env():
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

# Gmail helper functions
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
USER_ID = "me"
KEYWORDS = ["formation", "gardiennage", "prix", "intéressé par la formation"]

def refresh_access_token():
    token_url = "https://oauth2.googleapis.com/token"
    r = requests.post(token_url, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    r.raise_for_status()
    return r.json()["access_token"]

def gmail_service():
    creds = Credentials(token=refresh_access_token(),
                        refresh_token=REFRESH_TOKEN,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET)
    return build("gmail", "v1", credentials=creds)

# Fetch unread messages matching keywords
def fetch_messages(max_results=5):
    svc = gmail_service()
    res = svc.users().messages().list(userId=USER_ID, q="is:unread", maxResults=max_results).execute()
    items = res.get("messages", [])
    emails = []
    for m in items:
        msg = svc.users().messages().get(userId=USER_ID, id=m['id'], format='full').execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        # skip our administrative replies
        if headers.get('From', '').startswith(('academie@', 'd.oliveira@')):
            continue
        parts = msg['payload'].get('parts', [])
        body = ''
        for p in parts:
            if p.get('mimeType')=='text/plain':
                body = base64.urlsafe_b64decode(p['body']['data']).decode()
                break
        if not any(kw in body.lower() for kw in KEYWORDS):
            continue
        emails.append({
            'id': m['id'],
            'from': headers.get('From',''),
            'subject': headers.get('Subject','(Sans sujet)'),
            'body': body,
        })
    return emails

# Generate ChatGPT reply
def generate_reply(body_text):
    prompt = f"Compose a polite, professional reply in French to:\n\n{body_text}"
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}],
        max_tokens=300
    )
    return resp.choices[0].message.content.strip()

# GUI Application
class ReplyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XGuard Reply Suggester")
        self.geometry("800x600")
        self.emails = []
        self.create_widgets()
        self.load_emails()

    def create_widgets(self):
        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        # Left: list of emails
        frame_list = ttk.Frame(pane, width=200)
        self.listbox = tk.Listbox(frame_list)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        pane.add(frame_list)

        # Right: details and reply
        frame_detail = ttk.Frame(pane)
        self.lbl_meta = ttk.Label(frame_detail, text="Sélectionnez un courriel")
        self.lbl_meta.pack(anchor=tk.W, pady=5)
        self.txt_body = scrolledtext.ScrolledText(frame_detail, height=8)
        self.txt_body.pack(fill=tk.BOTH, expand=False)
        ttk.Label(frame_detail, text="Réponse proposée:").pack(anchor=tk.W, pady=5)
        self.txt_reply = scrolledtext.ScrolledText(frame_detail, height=8)
        self.txt_reply.pack(fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(frame_detail)
        ttk.Button(btn_frame, text="Envoyer", command=self.send_reply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Ignorer", command=self.ignore_email).pack(side=tk.LEFT, padx=5)
        btn_frame.pack(pady=5)
        pane.add(frame_detail)

    def load_emails(self):
        def task():
            self.emails = fetch_messages()
            self.listbox.delete(0, tk.END)
            for e in self.emails:
                self.listbox.insert(tk.END, e['subject'])
        threading.Thread(target=task).start()

    def on_select(self, evt):
        idx = self.listbox.curselection()
        if not idx: return
        e = self.emails[idx[0]]
        self.lbl_meta.config(text=f"De: {e['from']} | Sujet: {e['subject']}")
        self.txt_body.delete('1.0', tk.END)
        self.txt_body.insert(tk.END, e['body'])
        # generate
        def task_gen():
            rep = generate_reply(e['body'])
            self.txt_reply.delete('1.0', tk.END)
            self.txt_reply.insert(tk.END, rep)
        threading.Thread(target=task_gen).start()

    def send_reply(self):
        messagebox.showinfo("Envoyer", "Fonction d'envoi à implémenter")

    def ignore_email(self):
        idx = self.listbox.curselection()
        if idx:
            self.listbox.delete(idx)
            del self.emails[idx[0]]

if __name__ == '__main__':
    load_env()
    app = ReplyApp()
    app.mainloop()
