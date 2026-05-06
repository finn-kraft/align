import os
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ----------------------------
# PATH SETUP (module-local)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
ENV_DIR = os.path.join(BASE_DIR, ".env")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ENV_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(DATA_DIR, "live_data.csv")
TOKEN_FILE = os.path.join(ENV_DIR, "token.json")
CREDS_FILE = os.path.join(ENV_DIR, "credentials.json")

# ----------------------------
# CONFIG
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SPREADSHEET_ID = "1I0IQZWs7x8wu7yNa9UC95R-nGxtz2MyNzJSxtysVKw0"
RANGE_NAME = "Jetta!A2:G"


# ----------------------------
# MAIN
# ----------------------------
def main():
    creds = None

    # --- Load existing token ---
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # --- Refresh or authenticate ---
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDS_FILE):
                    print("❌ Missing credentials.json in gas/.env/")
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        except Exception as e:
            print("❌ Auth error:", e)
            return

    # --- Fetch data ---
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        values = result.get("values", [])

        if not values:
            print("⚠️ No data found")
            return

        headers = values[0]
        data = values[1:]

        df = pd.DataFrame(data, columns=headers)

        # --- Save safely ---
        tmp_file = OUTPUT_FILE + ".tmp"
        df.to_csv(tmp_file, index=False, encoding="utf-8-sig")
        os.replace(tmp_file, OUTPUT_FILE)

        print(f"✅ Data saved → {OUTPUT_FILE}")

    except HttpError as err:
        print(f"❌ Google API error: {err}")
    except Exception as e:
        print("❌ Unexpected error:", e)


if __name__ == "__main__":
    main()