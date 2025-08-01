# smoke_test.py
from dotenv import load_dotenv
import os
import openai

# Charge ton .env
load_dotenv()

# Récupère ta clé
openai.api_key = os.getenv("OPENAI_API_KEY")

# Appel basique pour lister quelques modèles
models = openai.Model.list()
print("OK, modèles disponibles :", [m.id for m in models.data][:5])