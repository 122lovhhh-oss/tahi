import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from colorama import Fore, Style, init as colorama_init

# ============================================================
#  CẤU HÌNH CỐ ĐỊNH — CHỈNH Ở ĐÂY NẾU MUỐN
# ============================================================
COOKIE_FILE   = "cookie.txt"   # tên file cookie
DELAY         = 0.3            # delay mỗi request (giây)
TOTAL_TARGET  = 999999         # số share tối đa
MAX_WORKER    = 20             # số thread
MAX_RETRY     = 3              # retry khi lỗi
TIMEOUT       = 15             # timeout request

TOKEN_PREFIXES = ["EAAJ", "EAAG", "EAAU", "EAAK", "EAAB", "EAAC"]

# ============================================================
#  MÀU SẮC
# ============================================================
colorama_init(autoreset=True)
R, G, Y, C, M, W = Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.MAGENTA, Fore.WHITE
RS = Style.RESET_ALL

def log(tag, msg, color=W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.LIGHTBLACK_EX}[{ts}]{RS} {color}[{tag}]{RS} {msg}")

def clear():
    os.system("cls" if sys.platform.startswith("win") else "clear")

# ============================================================
#  BANNER
# ============================================================
def banner():
    clear()
    print(f"""{M}
╔══════════════════════════════════════════════════════════════╗
║  {C}████████╗    ████████╗ ██████╗  ██████╗ ██╗     {M}              ║
║  {C}╚══██╔══╝    ╚══██╔══╝██╔═══██╗██╔═══██╗██║     {M}              ║
║  {C}   ██║          ██║   ██║   ██║██║   ██║██║     {M}              ║
║  {C}   ██║          ██║   ██║   ██║██║   ██║██║     {M}              ║
║  {C}   ██║          ██║   ╚██████╔╝╚██████╔╝███████╗{M}              ║
║  {C}   ╚═╝          ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝{M}              ║
╠══════════════════════════════════════════════════════════════╣
║  {G}Tool Share Cookie FB - Max Speed{RS}{M}                              ║
║  {Y}Admin: {W}Tokydev  {M}|  {Y}Ver: {W}2.1  {M}|  {Y}Youtube: {W}N/A{RS}{M}              ║
╚══════════════════════════════════════════════════════════════╝{RS}
""")

# ============================================================
#  LOAD COOKIE
# ============================================================
def load_cookies(path):
    if not os.path.isfile(path):
        log("ERROR", f"Không tìm thấy file {path}", R)
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = [l.strip() for l in f if l.strip()]
    seen, cookies = set(), []
    for c in raw:
        if c not in seen:
            seen.add(c); cookies.append(c)
    log("INFO", f"Đã load {len(cookies)} cookie", C)
    return cookies

# ============================================================
#  LẤY TOKEN
# ============================================================
def get_token(session, cookie, retry=MAX_RETRY):
    headers = {
        "authority": "business.facebook.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.6",
        "cookie": cookie,
        "referer": "https://www.facebook.com/",
        "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "upgrade-insecure-requests": "1",
    }
    for attempt in range(1, retry + 1):
        try:
            r = session.get("https://business.facebook.com/content_management",
                            headers=headers, timeout=TIMEOUT)
            html = r.text
            for prefix in TOKEN_PREFIXES:
                if prefix in html:
                    token = html.split(prefix, 1)[1].split('"', 1)[0]
                    return cookie, f"{prefix}{token}"
            return None
        except requests.RequestException:
            if attempt == retry:
                return None
            time.sleep(1)
    return None

def scan_tokens(cookies):
    print()
    log("SCAN", f"Đang kiểm tra {len(cookies)} cookie...", Y)
    live, dead = [], []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKER) as ex:
        futures = {ex.submit(get_token, requests.Session(), c): c for c in cookies}
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            if res:
                live.append(res)
            else:
                dead.append(futures[fut])
            print(f"{Fore.LIGHTBLACK_EX}  → Tiến độ: {done}/{len(cookies)} "
                  f"| Live: {len(live)} | Dead: {len(dead)}{RS}    ", end="\r")
    print()
    return live, dead

# ============================================================
#  SHARE 1 LẦN
# ============================================================
def share_once(session, cookie_token, post_id, retry=MAX_RETRY):
    cookie, token = cookie_token
    url = (f"https://graph.facebook.com/me/feed"
           f"?link=https://m.facebook.com/{post_id}"
           f"&published=0&access_token={token}")
    headers = {"accept": "*/*", "cookie": cookie,
               "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36")}
    for attempt in range(1, retry + 1):
        try:
            r = session.post(url, headers=headers, timeout=TIMEOUT)
            if r.status_code == 200 and '"id"' in r.text:
                return True, r.text
            return False, r.text[:120]
        except requests.RequestException as e:
            if attempt == retry:
                return False, str(e)
            time.sleep(1)
    return False, "unknown"

# ============================================================
#  COUNTER
# ============================================================
class Counter:
    def __init__(self, target):
        self.lock = threading.Lock()
        self.success = 0
        self.fail = 0
        self.target = target
    def add(self, ok):
        with self.lock:
            if ok: self.success += 1
            else:  self.fail += 1
    def reached(self):
        with self.lock:
            return self.success >= self.target

# ============================================================
#  MAIN — CHỈ HỎI ID
# ============================================================
def main_share():
    banner()

    # ❗ CHỈ HỎI DUY NHẤT 1 THỨ: ID CẦN SHARE
    post_id = input(f"{Y}➤ Nhập ID cần share: {RS}").strip()
    if not post_id:
        log("ERROR", "Chưa nhập ID!", R); time.sleep(2); return

    cookies = load_cookies(COOKIE_FILE)
    if not cookies:
        log("ERROR", f"File {COOKIE_FILE} trống hoặc không tồn tại!", R)
        input(f"\n{W}Nhấn Enter để quay lại...{RS}")
        return

    live, dead = scan_tokens(cookies)

    with open("live.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(f"{c}|{t}" for c, t in live))
    with open("dead.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(dead))

    if not live:
        log("ERROR", "Toàn bộ cookie DIE!", R)
        input(f"\n{W}Nhấn Enter để quay lại...{RS}")
        return

    print(f"\n{G}✔ LIVE: {len(live)}{RS}  |  {R}✘ DEAD: {len(dead)}{RS}")
    print(f"{M}═══════════ BẮT ĐẦU SHARE ID: {Y}{post_id}{RS} ═══════════")

    counter = Counter(TOTAL_TARGET)
    start = time.time()

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKER) as ex:
            while not counter.reached():
                batch = []
                for ck_token in live:
                    if counter.reached():
                        break
                    fut = ex.submit(share_once, requests.Session(), ck_token, post_id)
                    batch.append(fut)
                    time.sleep(DELAY)
                for fut in batch:
                    ok, info = fut.result()
                    counter.add(ok)
                    if ok:
                        log("OK", f"✔ Share #{counter.success} | ID: {post_id} | Fail: {counter.fail}", G)
                    else:
                        log("FAIL", f"✘ {info}", R)

    except KeyboardInterrupt:
        log("STOP", "Người dùng dừng tool!", Y)

    elapsed = time.time() - start
    print(f"\n{M}═══════════════════ KẾT QUẢ ═══════════════════{RS}")
    print(f"  {G}✔ Thành công: {counter.success}{RS}")
    print(f"  {R}✘ Thất bại  : {counter.fail}{RS}")
    print(f"  {C}⏱ Thời gian : {elapsed:.2f}s{RS}")
    print(f"  {C}⚡ Tốc độ   : {counter.success / max(elapsed, 1):.2f} share/s{RS}")

    input(f"\n{W}Nhấn Enter để share ID khác...{RS}")

# ============================================================
#  ENTRY POINT — CHẠY THẲNG VÀO SHARE
# ============================================================
if __name__ == "__main__":
    try:
        while True:
            main_share()
    except KeyboardInterrupt:
        print(f"\n{Y}Đã thoát. Tool {G}T Tool{Y} - Chúc bạn thành công!{RS}")
        sys.exit()
