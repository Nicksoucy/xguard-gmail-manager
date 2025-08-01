from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Sauvegarde du token
with open('token.json', 'w') as token:
    token.write(creds.to_json())

print("✅ token.json généré avec succès.")
