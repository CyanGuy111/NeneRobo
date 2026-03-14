import os
import requests
import time
import gspread
from google.oauth2.service_account import Credentials

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
clients = gspread.authorize(creds)

def get_img_url(song_id):
    if song_id in [371, 419, 453, 459, 479, 514, 528, 535, 563, 568, 598, 599, 602, 609, 640, 657, 673, 694, 701]:
        return f"https://storage.sekai.best/sekai-en-assets/music/jacket/jacket_s_{song_id:03}/jacket_s_{song_id:03}.webp"
    return f"https://storage.sekai.best/sekai-jp-assets/music/jacket/jacket_s_{song_id:03}/jacket_s_{song_id:03}.webp"

def download_jackets():
    print("Fetching song IDs from your Google Sheet...")
    
    obg = clients.open_by_key("1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo").sheet1
    raw_data = obg.get('A2:A')
    
    if not raw_data:
        print("Failed to fetch data from the spreadsheet.")
        return

    headers = raw_data[0]
    parsed = [dict(zip(headers, row)) for row in raw_data[1:]]
    
    unique_ids = set()
    for row in parsed:
        raw_id = row.get('ID')
        if raw_id and raw_id.isdigit():
            unique_ids.add(int(raw_id))
            
    print(f"Found {len(unique_ids)} unique song IDs in the spreadsheet. Starting downloads!")
    
    for song_id in sorted(list(unique_ids)):
        url = get_img_url(song_id)
        filename = f"assets/jackets/jacket_s_{song_id:03}.webp"
        
        if os.path.exists(filename):
            print(f"Already exists, skipping: {filename}")
            continue
            
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded: jacket_s_{song_id:03}.webp")
            else:
                print(f"Error {response.status_code} for ID {song_id}")
                
        except Exception as e:
            print(f"Failed to download ID {song_id}: {e}")
            
        time.sleep(0.1)

    print("Finished downloading all spreadsheet jackets!")