import sqlite3
import asyncio
import pyfiglet
import requests
import json
import os
import shutil
import runpy
from pathlib import Path


FOLLOWING_FILE = Path("temp") / "following_list.json"
FOLLOWERS_FILE = Path("temp") / "followers_list.json"
DB_FILE = "fdap.db"
cookie_str = None
auth_str = None
csrf_str = None
id_str = None

async def main():
    global cookie_str, auth_str, csrf_str
    if os.path.isdir("./temp"):
        for filename in os.listdir("./temp"):
            file_path = os.path.join("./temp", filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print("Unknown error")
    os.makedirs('./temp', exist_ok=True)
    print(pyfiglet.figlet_format("FDAP"), end="", flush=True)
    print("Twitter Internal API Version")
    if not Path(DB_FILE).exists():
        await init_db()
    else:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT cookie, authorization, x_csrf_token FROM users ORDER BY rowid DESC LIMIT 1')
        row = cursor.fetchone()
        cookie_str, auth_str, csrf_str = row
        conn.close()
    await fetch_list(cookie_str, auth_str, csrf_str)
    await asyncio.to_thread(runpy.run_path, "clean.py", run_name="__main__")
    os.remove(FOLLOWING_FILE)
    os.remove(FOLLOWERS_FILE)
    await asyncio.to_thread(runpy.run_path, "split.py", run_name="__main__")

async def init_db():
    global cookie_str, auth_str, csrf_str
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            cookie TEXT,
            authorization TEXT,
            x_csrf_token TEXT
        )
        """
    )
    conn.commit()
    id_str = input('user_id: ').strip()
    cookie_str = input('cookie: ').strip()
    auth_str = input('authorization: ').strip()
    csrf_str = input('x-csrf-token: ').strip()
    conn.execute('INSERT INTO users (id, cookie, authorization, x_csrf_token) VALUES (?, ?, ?, ?)', (id_str, cookie_str, auth_str, csrf_str))
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

async def fetch_list(cookie_str, auth_str, csrf_str):
    global API_URL
    API_URL = (
    "https://x.com/i/api/1.1/friends/list.json"
    "?include_profile_interstitial_type=0"
    "&include_blocking=0"
    "&include_blocked_by=0"
    "&include_followed_by=1"
    "&include_want_retweets=0"
    "&include_mute_edge=0"
    "&include_can_dm=1"
    "&include_can_media_tag=1"
    "&include_ext_is_blue_verified=1"
    "&include_ext_verified_type=1"
    "&include_ext_profile_image_shape=0"
    "&skip_status=1"
    "&cursor=-1"
    f"&user_id={id_str}"
    "&count=200"
    "&with_total_count=true"
    )
    print("Fetching following list...")
    headers = {
        'accept': '*/*',
        'authorization': auth_str,
        'dnt': '1',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-csrf-token': csrf_str,
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }
    cookies = dict(pair.split("=", 1) for pair in cookie_str.split("; "))

    # --- Following list ---
    next_cursor_following = "-1"
    following_count = 0
    page = 0
    following_chunks = []
    while next_cursor_following and next_cursor_following != "0":
        print(f"Fetching following page {page} with cursor {next_cursor_following}...")
        url = API_URL.replace("cursor=-1", f"cursor={next_cursor_following}")
        
        # 为请求添加带超时的无限重试循环
        while True:
            try:
                resp = await asyncio.to_thread(
                    requests.get, url, headers=headers, cookies=cookies, timeout=3
                )
                resp.raise_for_status() # 检查HTTP错误
                break # 成功则跳出循环
            except requests.exceptions.RequestException:
                await asyncio.sleep(1) # 失败则稍等后重试
                continue # 继续下一次尝试

        data = resp.json()
        users = data.get("users", [])
        chunk_file = FOLLOWING_FILE.parent / f"following_list_{page}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        following_chunks.append(chunk_file)
        following_count += len(users)
        next_cursor_following = str(data.get("next_cursor", "0"))
        page += 1
    print(f"People you are following: {following_count}")

    # Merge following json
    all_following = []
    for chunk_file in following_chunks:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            all_following.extend(json.load(f))
        os.remove(chunk_file)
    with open(FOLLOWING_FILE.parent / "following_list.json", 'w', encoding='utf-8') as f:
        json.dump(all_following, f, ensure_ascii=False, indent=2)

    # --- Followers list ---
    print("Fetching followers list...")
    next_cursor_followers = "-1"
    followers_count = 0
    page = 0
    followers_chunks = []
    followers_url_template = API_URL.replace("friends/list.json", "followers/list.json")
    while next_cursor_followers and next_cursor_followers != "0":
        print(f"Fetching followers page {page} with cursor {next_cursor_followers}...")
        url = followers_url_template.replace("cursor=-1", f"cursor={next_cursor_followers}")

        # 为请求添加带超时的无限重试循环
        while True:
            try:
                resp = await asyncio.to_thread(
                    requests.get, url, headers=headers, cookies=cookies, timeout=3
                )
                resp.raise_for_status() # 检查HTTP错误
                break # 成功则跳出循环
            except requests.exceptions.RequestException:
                await asyncio.sleep(1) # 失败则稍等后重试
                continue # 继续下一次尝试

        data = resp.json()
        users = data.get("users", [])
        chunk_file = FOLLOWERS_FILE.parent / f"followers_list_{page}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        followers_chunks.append(chunk_file)
        followers_count += len(users)
        next_cursor_followers = str(data.get("next_cursor", "0"))
        page += 1
    print(f"Your followers: {followers_count}")

    # Merge followers json
    all_followers = []
    for chunk_file in followers_chunks: 
        with open(chunk_file, 'r', encoding='utf-8') as f:
            all_followers.extend(json.load(f))
        os.remove(chunk_file)
    with open(FOLLOWERS_FILE.parent / "followers_list.json", 'w', encoding='utf-8') as f:
        json.dump(all_followers, f, ensure_ascii=False, indent=2)



if __name__ == "__main__":
    asyncio.run(main())
