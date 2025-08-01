import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Autorisation avec ton fichier credentials.json
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# ID de la feuille Google Sheets
sheet_id = "19R0THrBOMCWafXHf_X9DQJNnvvmbhLGMwX5TU84abq8"
sheet = client.open_by_key(sheet_id)

# Sélectionne l'onglet (worksheet) avec fallback intelligent
try:
    worksheet = sheet.worksheet("Feuille 1")
except gspread.exceptions.WorksheetNotFound:
    print("⚠️ Onglet 'Feuille 1' non trouvé.")
    print("📋 Onglets disponibles :", [ws.title for ws in sheet.worksheets()])
    worksheet = sheet.get_worksheet(0)
    print(f"✅ Ouverture du premier onglet : {worksheet.title}")

# Écrit une ligne test
worksheet.append_row(["✅ Connexion réussie !", "Test depuis script"])

print("✅ Connexion réussie et ligne ajoutée.")