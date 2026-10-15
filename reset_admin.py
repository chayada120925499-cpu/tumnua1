# ==============================================================================
# สคริปต์รีเซ็ตรหัสผ่านผู้ดูแลระบบ (Admin Password Reset Utility)
# ==============================================================================
import sqlite3
import sys

# รองรับการแสดงผลภาษาไทยและ Emoji บน Windows Terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from utils.auth import hash_password

DB_NAME = "restaurant.db"

def reset_admin_password(username="admin", new_password="adminfahsaitumnua@12"):
    """รีเซ็ตรหัสผ่านของแอดมินในฐานข้อมูล SQLite"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ตรวจสอบว่ามีผู้ใช้นี้อยู่หรือไม่
    c.execute("SELECT id, username, full_name FROM admin_users WHERE LOWER(username) = LOWER(?)", (username,))
    user = c.fetchone()
    
    if not user:
        print(f"[-] ไม่พบบัญชีผู้ใช้: '{username}' ในระบบ")
        conn.close()
        return False
        
    pw_hash, salt = hash_password(new_password)
    c.execute("UPDATE admin_users SET password_hash = ?, salt = ? WHERE id = ?", (pw_hash, salt, user[0]))
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print("[+] รีเซ็ตรหัสผ่านสำเร็จเรียบร้อยแล้ว!")
    print(f"[*] บัญชีผู้ใช้ : {user[1]} ({user[2]})")
    print(f"[*] รหัสผ่านใหม่ : {new_password}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        target_user = sys.argv[1]
        target_pw = sys.argv[2]
    elif len(sys.argv) == 2:
        target_user = "admin"
        target_pw = sys.argv[1]
    else:
        print("[i] กำลังรีเซ็ตรหัสผ่านบัญชี 'admin' กลับสู่ค่าเริ่มต้น...")
        target_user = "admin"
        target_pw = "adminfahsaitumnua@12"
        
    reset_admin_password(target_user, target_pw)
