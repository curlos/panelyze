# Download one MangaDex chapter's pages. Args: chapter_id out_dir
import json, os, sys, time, urllib.request
cid, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
H = {"User-Agent": "panelyze-test"}
server = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.mangadex.org/at-home/server/{cid}", headers=H), timeout=30))
for number, name in enumerate(server["chapter"]["data"]):
    data = urllib.request.urlopen(urllib.request.Request(f"{server['baseUrl']}/data/{server['chapter']['hash']}/{name}", headers=H), timeout=60).read()
    open(os.path.join(out, f"{number:02}{os.path.splitext(name)[1]}"), "wb").write(data)
    time.sleep(0.3)
print(out, len(os.listdir(out)), "pages")
