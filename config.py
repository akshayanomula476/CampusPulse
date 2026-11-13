
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env
load_dotenv()

# Get Supabase connection details
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or key is missing. Check your .env file.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Supabase configuration loaded successfully!")
