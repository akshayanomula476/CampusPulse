
import httpx
from config import SUPABASE_URL, SUPABASE_KEY

print("Testing Supabase connection...")

try:
    response = httpx.get(
        f"{SUPABASE_URL.rstrip('/')}/auth/v1/settings",
        headers={
            "apikey": SUPABASE_KEY
        },
        timeout=15
    )

    if response.status_code == 200:
        print("SUCCESS!")
        print("Supabase connection is working.")
    else:
        print("Connection test returned an error.")
        print("Status code:", response.status_code)
        print("Response:", response.text[:500])

except Exception as error:
    print("CONNECTION FAILED!")
    print("Error:", error)
