"""
Huong dan & kiem tra ket noi WordPress tu dong.
Chay: python setup_wordpress.py
"""
import os
import sys
import base64
import requests
from dotenv import load_dotenv, set_key

load_dotenv()
ENV_FILE = ".env"


def print_header(text):
    print(f"\n{'='*55}")
    print(f"  {text}")
    print('='*55)


def print_step(n, text):
    print(f"\n[Buoc {n}] {text}")
    print("-" * 40)


def test_wp_connection(url, username, password):
    """Kiem tra ket noi WordPress REST API."""
    api_url = url.rstrip("/") + "/wp-json/wp/v2/posts"
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    try:
        resp = requests.get(
            api_url,
            headers={"Authorization": f"Basic {auth}"},
            timeout=10
        )
        if resp.status_code == 200:
            return True, f"Ket noi thanh cong! Tim thay {len(resp.json())} bai viet."
        elif resp.status_code == 401:
            return False, "Sai username hoac Application Password."
        elif resp.status_code == 404:
            return False, "Khong tim thay WordPress REST API. Kiem tra lai URL site."
        else:
            return False, f"Loi HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Khong the ket noi toi {url}. Kiem tra lai URL."
    except Exception as e:
        return False, str(e)


def guide_get_wordpress():
    print_header("CACH CO WORDPRESS NHANH NHAT")
    print("""
OPTION 1: Dung Hostinger (re nhat - khuyen nghi)
-------------------------------------------------
  1. Vao: https://hostinger.com
  2. Chon goi "Premium" (~$2.99/thang)
  3. Mua ten mien .com (~$9/nam) hoac dung mien phi cua ho
  4. Click "Install WordPress" trong dashboard
  5. Done! Co WordPress trong 5 phut.

OPTION 2: InfinityFree (hoan toan mien phi, co gioi han)
----------------------------------------------------------
  1. Vao: https://infinityfree.com
  2. Dang ky tai khoan mien phi
  3. Tao hosting mien phi
  4. Cai WordPress qua Softaculous
  5. Luu y: mien phi nen hoi cham, khong co SSL

OPTION 3: Neu ban da co hosting/VPS
-------------------------------------
  1. Upload WordPress len server
  2. Cai dat binh thuong
""")


def guide_get_app_password():
    print("""
Sau khi co WordPress, tao Application Password:
-------------------------------------------------
  1. Dang nhap WordPress Admin
  2. Vao: Users -> Your Profile (Profile cua ban)
  3. Keo xuong phan "Application Passwords"
  4. Nhap ten bat ky (vd: "AI System")
  5. Click "Add New Application Password"
  6. SAO CHEP mat khau hien ra (chi hien 1 lan!)
     Vi du: "AbCd EfGh IjKl MnOp QrSt UvWx"
""")


def interactive_setup():
    print_header("WORDPRESS AUTO-CONNECT SETUP")
    print("Script nay se giup ban ket noi he thong AI voi WordPress.\n")

    # Kiem tra xem da co config chua
    current_url = os.getenv("WP_SITE_URL", "")
    current_user = os.getenv("WP_USERNAME", "")
    current_pass = os.getenv("WP_APP_PASSWORD", "")

    if current_url and current_user and current_pass:
        print(f"[!] Phat hien cau hinh hien tai:")
        print(f"    URL: {current_url}")
        print(f"    User: {current_user}")
        ok, msg = test_wp_connection(current_url, current_user, current_pass)
        if ok:
            print(f"[OK] {msg}")
            print("\nWordPress da duoc ket noi! He thong san sang dang bai tu dong.")
            return True
        else:
            print(f"[!!] {msg}")
            print("    Can cap nhat lai thong tin.")

    # Huong dan neu chua co WP
    print("\nBan co WordPress site chua?")
    print("  1. Co, toi da co site")
    print("  2. Chua, can huong dan")
    print("  3. Thoat")

    choice = input("\nChon (1/2/3): ").strip()

    if choice == "2":
        guide_get_wordpress()
        print("\nSau khi co site, chay lai script nay va chon option 1.")
        return False

    elif choice == "3":
        return False

    elif choice == "1":
        print_step(1, "Nhap URL WordPress site cua ban")
        print("Vi du: https://yourdomain.com hoac http://localhost")
        url = input("URL: ").strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url

        print_step(2, "Nhap Username WordPress")
        print("(Username ban dung de dang nhap WP Admin)")
        username = input("Username: ").strip()

        print_step(3, "Nhap Application Password")
        guide_get_app_password()
        app_pass = input("Application Password: ").strip()

        # Test ket noi
        print("\nDang kiem tra ket noi...")
        ok, msg = test_wp_connection(url, username, app_pass)

        if ok:
            # Luu vao .env
            set_key(ENV_FILE, "WP_SITE_URL", url)
            set_key(ENV_FILE, "WP_USERNAME", username)
            set_key(ENV_FILE, "WP_APP_PASSWORD", app_pass)
            print(f"\n[OK] {msg}")
            print("[OK] Da luu vao .env")
            print("\nHe thong san sang! Bai viet se TU DONG dang len WordPress.")
            print("\nChay ngay:")
            print("  python main.py publish 1    <- Dang 1 bai ngay bay gio")
            print("  python main.py schedule     <- Bat auto-pilot 3 bai/ngay")
            return True
        else:
            print(f"\n[!!] Ket noi that bai: {msg}")
            print("\nKiem tra lai:")
            print("  1. URL dung chua? (co http/https?)")
            print("  2. Username chinh xac?")
            print("  3. Application Password duoc sao chep day du?")
            print("  4. WordPress REST API duoc bat? (mac dinh la bat)")
            return False
    else:
        print("Lua chon khong hop le.")
        return False


def show_status():
    """Hien thi trang thai ket noi hien tai."""
    print_header("TRANG THAI KET NOI")

    url = os.getenv("WP_SITE_URL", "")
    user = os.getenv("WP_USERNAME", "")
    passwd = os.getenv("WP_APP_PASSWORD", "")

    if not url:
        print("[--] WordPress: Chua cau hinh")
        print("     Chay: python setup_wordpress.py")
    else:
        ok, msg = test_wp_connection(url, user, passwd)
        status = "[OK]" if ok else "[!!]"
        print(f"{status} WordPress: {url}")
        print(f"     {msg}")

    from utils.ai_client import AIClient
    try:
        ai = AIClient()
        print(f"[OK] AI Provider: {ai.provider.upper()}")
    except Exception as e:
        print(f"[!!] AI Provider: {e}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    else:
        interactive_setup()
