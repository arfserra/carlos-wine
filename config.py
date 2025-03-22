import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# App password
APP_PASSWORD = os.getenv("APP_PASSWORD")

# Database configuration
DATABASE_PATH = "wine_collection.db"

# Application settings
APP_TITLE = "Carlos Wine Assistant"
APP_ICON = "🍷"