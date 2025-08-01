"""
Configuration centralisée pour XGuard Gmail Manager
"""
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
ENV_PATH = BASE_DIR / ".env"

# Configuration par défaut
DEFAULT_CONFIG = {
    "check_interval": 300,  # 5 minutes
    "test_mode": True,
    "ignored_senders": [
        "noreply@",
        "no-reply@",
        "notification@"
    ],
    "keywords": [
        "formation",
        "gardiennage",
        "prix",
        "intéressé"
    ]
}

# Messages
SYSTEM_PROMPT = """Tu es un assistant professionnel pour l'Académie XGuard. 
Réponds de manière professionnelle, claire et utile aux demandes concernant 
les formations en gardiennage et sécurité."""

def load_env():
    """Charge les variables d'environnement"""
    if ENV_PATH.exists():
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH)
