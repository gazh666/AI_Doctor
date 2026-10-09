# Create a file named check.py and run: python check.py
from google import genai
from app.core.config import settings
client = genai.Client(api_key=settings.GOOGLE_API_KEY)
# This will print the exact string you need to use
print([m.name for m in client.models.list() if 'embed' in m.name])