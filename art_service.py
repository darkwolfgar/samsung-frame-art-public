import asyncio
import httpx
import random
import os
import logging
from samsungtvws.async_art import SamsungTVAsyncArt

# --- CONFIGURATION ---
TV_IP = os.getenv("TV_IP", "192.168.1.100")
DEPT_ID = int(os.getenv("DEPT_ID", "11"))  # 11 = European Paintings
INTERVAL = int(os.getenv("INTERVAL", "86400"))  # 24 hours
TOKEN_PATH = "/app/data/tv-token.txt"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def fetch_met_painting():
    async with httpx.AsyncClient(timeout=60.0) as client:
        logging.info(f"Searching The Met for classic paintings (Dept: {DEPT_ID})...")
        
        try:
            search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?departmentId={DEPT_ID}&q=painting&isPublicDomain=true"
            search_res = await client.get(search_url)
            search_res.raise_for_status()
            object_ids = search_res.json().get('objectIDs', [])

            if not object_ids:
                logging.warning("No paintings found in this department.")
                return None

            random.shuffle(object_ids)
            for obj_id in object_ids[:10]:
                obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
                obj_res = await client.get(obj_url)
                if obj_res.status_code != 200:
                    continue
                
                data = obj_res.json()
                image_url = data.get('primaryImage')
                
                if image_url:
                    title = data.get('title', 'Unknown')
                    artist = data.get('artistDisplayName', 'Unknown Artist')
                    logging.info(f"Selected Artwork: {title} by {artist}")
                    
                    logging.info(f"Downloading image from {image_url}...")
                    img_res = await client.get(image_url)
                    img_res.raise_for_status()
                    return img_res.content

        except Exception as e:
            logging.error(f"Error fetching from The Met: {e}")
            
    return None

async def monitor_power(tv):
    # Monitor power state and force Art Mode
    logging.info("CEC/Power monitor started.")
    while True:
        try:
            info = await tv.rest_device_info()
            device_info = info.get('device', {})
            power_state = device_info.get('PowerState', 'UNKNOWN')
            in_art_mode = await tv.is_artmode()

            if power_state == 'STANDBY' and not in_art_mode:
                logging.info(f"TV is in {power_state} and Art Mode is OFF. Forcing Art Mode...")
                await tv.set_artmode(True)
            
        except Exception:
            pass
            
        await asyncio.sleep(15)

async def main():
    logging.info(f"Samsung Frame Art Service Started (TV: {TV_IP})")
    tv = SamsungTVAsyncArt(host=TV_IP, port=8002, token_file=TOKEN_PATH)
    
    asyncio.create_task(monitor_power(tv))
    
    try:
        await tv.start_listening()
        
        while True:
            logging.info("Checking for daily art update...")
            
            if await tv.on():
                image_data = await fetch_met_painting()
                if image_data:
                    logging.info("Uploading new daily masterpiece...")
                    content_id = await tv.upload(image_data, file_type='JPEG', matte='modern_white')
                    await tv.select_image(content_id)
                    logging.info(f"Daily update successful: {content_id}")
            else:
                logging.info("TV is unreachable, skipping daily update for now.")

            logging.info(f"Next scheduled update check in {INTERVAL} seconds.")
            await asyncio.sleep(INTERVAL)
            
    except Exception as e:
        logging.error(f"Main loop error: {e}")
    finally:
        await tv.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
