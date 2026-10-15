# ==============================================================================
# ระบบความปลอดภัยและการเข้ารหัสรหัสผ่าน (Authentication Utilities)
# ==============================================================================
import hashlib
import hmac
import secrets

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """เข้ารหัสผ่านด้วย SHA-256 ผสม Salt ป้องกันการขโมยรหัสผ่าน"""
    if not salt:
        salt = secrets.token_hex(8)
    pw_hash = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return pw_hash, salt

def verify_password(input_password: str, stored_hash: str, salt: str) -> bool:
    """ตรวจสอบรหัสผ่านที่ป้อนเข้ามา เทียบกับค่า Hash ที่บันทึกไว้ในฐานข้อมูล (Timing-attack safe)"""
    calc_hash = hashlib.sha256((salt + input_password).encode('utf-8')).hexdigest()
    return hmac.compare_digest(calc_hash, stored_hash)
