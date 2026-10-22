# ==============================================================================
# ค่าคงที่และการตั้งค่าระบบ (Configuration & Theme)
# ==============================================================================
import os
import base64
import streamlit as st
from datetime import datetime, timedelta, timezone

# --- ข้อมูลฐานข้อมูลและความปลอดภัย ---
DB_NAME = "restaurant.db"

# --- การตั้งค่าการส่งอีเมล (Email & SMTP Settings สำหรับ OTP) ---
def get_secret(key: str, default: str = "") -> str:
    """ดึงค่าคอนฟิกจาก st.secrets (Streamlit Cloud) หรือ os.environ (Local/Docker)"""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

SMTP_SERVER = get_secret("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", "587"))
SMTP_EMAIL = get_secret("SMTP_EMAIL", "")           # อีเมล Gmail ของทางร้าน เช่น fahsaitumnua@gmail.com
SMTP_PASSWORD = get_secret("SMTP_PASSWORD", "")     # Google App Password 16 หลัก
SMTP_SENDER_NAME = get_secret("SMTP_SENDER_NAME", "ฟ้าใสตำนัว (Fahsai Tumnua)")


# --- เวลาประเทศไทย (UTC+7) ---
TH_TZ = timezone(timedelta(hours=7))

def get_thai_now():
    """ฟังก์ชันคืนค่าวันและเวลาปัจจุบันของประเทศไทย (UTC+7)"""
    return datetime.now(TH_TZ)

# --- รูปภาพและโลโก้ร้าน ---
LOGO_PATH = "static/img/logo.png"

def get_base64_image(image_path):
    """แปลงไฟล์รูปภาพเป็น Base64 สำหรับแทรกใน HTML"""
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

def get_valid_image_path(img_path):
    """
    ตรวจสอบและค้นหาตำแหน่งไฟล์รูปภาพที่ใช้งานได้จริง
    รองรับทั้ง WebP, PNG, JPG และจัดการเรื่องชื่อไฟล์มี/ไม่มีช่องว่างโดยอัตโนมัติ
    """
    if not img_path:
        return None
    if isinstance(img_path, str) and (img_path.startswith("http://") or img_path.startswith("https://")):
        return img_path
    
    norm_path = str(img_path).replace("/", os.sep).replace("\\", os.sep)
    if os.path.exists(norm_path):
        return norm_path
    
    # ตรวจสอบนามสกุลทางเลือก (.webp, .png, .jpg, .jpeg)
    base, _ = os.path.splitext(norm_path)
    for alt_ext in [".webp", ".png", ".jpg", ".jpeg"]:
        if os.path.exists(base + alt_ext):
            return base + alt_ext
            
    # ตรวจสอบกรณีชื่อมีช่องว่าง เช่น menu 1 vs menu1
    candidates = []
    if "menu " in norm_path:
        candidates.append(norm_path.replace("menu ", "menu"))
    elif "menu" in norm_path:
        candidates.append(norm_path.replace("menu", "menu "))
        
    for c in candidates:
        if os.path.exists(c):
            return c
        c_base, _ = os.path.splitext(c)
        for alt_ext in [".webp", ".png", ".jpg", ".jpeg"]:
            if os.path.exists(c_base + alt_ext):
                return c_base + alt_ext
                
    # กรณีพิเศษ menu132 <-> menu124
    if "menu132" in norm_path:
        alt124 = norm_path.replace("menu132", "menu124")
        if os.path.exists(alt124):
            return alt124
        b124, _ = os.path.splitext(alt124)
        for alt_ext in [".webp", ".png", ".jpg", ".jpeg"]:
            if os.path.exists(b124 + alt_ext):
                return b124 + alt_ext
                
    return None

def get_current_base_url(default="https://tumnua1-fcjmlnyaebejaetpjkjbmd.streamlit.app"):
    """ตรวจจับ URL เว็บไซต์อัตโนมัติจาก Request Headers เพื่อใช้สร้าง QR Code"""
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            hdrs = st.context.headers
            host = hdrs.get("x-forwarded-host") or hdrs.get("host")
            proto = hdrs.get("x-forwarded-proto", "https")
            if host:
                clean_host = host.split(",")[0].strip()
                return f"{proto}://{clean_host}"
    except Exception:
        pass
    return default

def render_app_footer():
    """แสดง Footer เครดิตผู้พัฒนาระบบ"""
    st.write("---")
    footer_html = """
    <div style="text-align: center; margin-top: 25px; margin-bottom: 25px; padding: 15px 10px; color: #4b5563; line-height: 1.8;">
        <div style="font-weight: 700; color: #c2410c; font-size: 1.05rem;">ระบบสั่งอาหารโต๊ะผ่าน QR Code</div>
        <div style="color: #374151; font-weight: 500;">พัฒนา โดย นางสาวชญาดา สิงหวัฒน์</div>
        <div style="color: #6b7280; font-size: 0.95rem;">อีเมล์ : chayada.sing@kkumail.com &nbsp;&nbsp;&nbsp;&nbsp; โทรศัพท์ : 093-773-4851</div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def apply_custom_css():
    """แทรกสไตล์ CSS และ JavaScript จัดการหน้าจอ/URL เข้าสู่ระบบ"""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

/* บังคับใช้ฟอนต์ Prompt โดยไม่ทับไอคอน Material Symbols ของ Streamlit */
html, body, p, input, select, textarea {
    font-family: 'Prompt', sans-serif !important;
}

.stMarkdown, .stButton > button {
    font-family: 'Prompt', sans-serif !important;
}

/* คืนค่าฟอนต์ไอคอน Material Symbols เพื่อไม่ให้กลายเป็นตัวหนังสือคำว่า expand_less ทับบนปุ่ม */
[data-testid="stIconMaterial"], 
[class*="material-symbols"], 
[class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    font-style: normal !important;
}

/* ซ่อนไอคอนลูกศร expand_less/expand_more ในปุ่ม popover ไม่ให้บังข้อความ */
div[data-testid="stPopover"] > button [data-testid="stIconMaterial"] {
    display: none !important;
}

div[data-testid="stPopover"] > button {
    font-family: 'Prompt', sans-serif !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 44px !important;
    font-weight: 600 !important;
}


/* ปรับระยะขอบหน้าจอให้พอดีกับมือถือ */
@media (max-width: 640px) {
    .main .block-container {
        padding: 0.75rem 0.5rem 3rem 0.5rem !important;
    }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
}

@media (min-width: 641px) and (max-width: 1024px) {
    .main .block-container {
        padding: 1.5rem 1.25rem 3rem 1.25rem !important;
    }
}

/* ปุ่มกดขนาดใหญ่ สัมผัสง่ายสำหรับนิ้วมือบนสมาร์ตโฟน (Touch-friendly 44px+) */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    min-height: 44px !important;
    font-size: 14px !important;
    border: 1.5px solid #fed7aa !important;
    background: #ffffff !important;
    color: #9a3412 !important;
    box-shadow: 0 2px 6px rgba(234, 88, 12, 0.08) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stButton > button:hover {
    background: #ffedd5 !important;
    border-color: #f97316 !important;
    color: #c2410c !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(234, 88, 12, 0.18) !important;
}

.stButton > button:active {
    transform: scale(0.97) !important;
}

/* ปุ่ม Primary โดดเด่นด้วยสีส้มเปลวไฟไล่เฉด สดใส น่ากด (Vibrant Gradient Primary) */
button[kind="primary"] {
    background: linear-gradient(135deg, #f97316 0%, #ea580c 50%, #dc2626 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(234, 88, 12, 0.4) !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(135deg, #fb923c 0%, #f97316 50%, #ea580c 100%) !important;
    box-shadow: 0 6px 18px rgba(234, 88, 12, 0.5) !important;
}

/* การ์ดรายการอาหารและบล็อกคอนเทนเนอร์ มีขอบมนและเงาสีนุ่มนวล (Glassmorphism card) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1.5px solid #ffedd5 !important;
    box-shadow: 0 4px 16px rgba(234, 88, 12, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    background: #ffffff !important;
    padding: 12px !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #fdba74 !important;
    box-shadow: 0 6px 20px rgba(234, 88, 12, 0.12) !important;
}

/* สไตล์การ์ดอาหาร: Responsive Grid ทุกแถวและทุกคอลัมน์ขนาดเท่ากันเป๊ะ (แถวสุดท้ายไม่ขยายเกินแถวด้านบน) */
/* สไตล์การ์ดอาหาร: Responsive Flexbox Grid ทุกแถวและทุกคอลัมน์ขนาดเท่ากันเป๊ะ แถวสุดท้ายไม่ขยายเกินแถวด้านบน */
div[data-testid="stLayoutWrapper"]:has(.st-key-menu_grid_flex),
div.st-key-menu_grid_flex,
[data-testid="stHorizontalBlock"].st-key-menu_grid_flex,
div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    justify-content: flex-start !important;
    align-items: stretch !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}

/* เฉพาะตัวการ์ดแต่ละใบเท่านั้นที่ล็อคความกว้าง ไม่ให้ขยายเกินแถวด้านบน */
[data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(.fcard-marker),
[data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(div[class*="st-key-fcard_"]),
[data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div[class*="st-key-fcard_"],
div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] > div {
    flex-grow: 0 !important;
    flex-shrink: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
    min-width: 0 !important;
}

/* หน้าจอใหญ่ Desktop (> 1024px): 6 คอลัมน์ (5 gaps * 12px = 60px) */
@media (min-width: 1025px) {
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex,
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] {
        gap: 12px !important;
        row-gap: 16px !important;
    }
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(.fcard-marker),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(div[class*="st-key-fcard_"]),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div[class*="st-key-fcard_"],
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 calc((100% - 60px) / 6) !important;
        width: calc((100% - 60px) / 6) !important;
        max-width: calc((100% - 60px) / 6) !important;
    }
}

/* หน้าจอ Tablet แนวนอน / โน้ตบุ๊กเล็ก (769px - 1024px): 4 คอลัมน์ (3 gaps * 12px = 36px) */
@media (min-width: 769px) and (max-width: 1024px) {
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex,
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] {
        gap: 12px !important;
        row-gap: 14px !important;
    }
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(.fcard-marker),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(div[class*="st-key-fcard_"]),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div[class*="st-key-fcard_"],
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 calc((100% - 36px) / 4) !important;
        width: calc((100% - 36px) / 4) !important;
        max-width: calc((100% - 36px) / 4) !important;
    }
}

/* หน้าจอ Tablet แนวตั้ง / มือถือจอใหญ่ (481px - 768px): 3 คอลัมน์ (2 gaps * 10px = 20px) */
@media (min-width: 481px) and (max-width: 768px) {
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex,
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] {
        gap: 10px !important;
        row-gap: 12px !important;
    }
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(.fcard-marker),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(div[class*="st-key-fcard_"]),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div[class*="st-key-fcard_"],
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 calc((100% - 20px) / 3) !important;
        width: calc((100% - 20px) / 3) !important;
        max-width: calc((100% - 20px) / 3) !important;
    }
}

/* หน้าจอมือถือทั่วไป (<= 480px): 2 คอลัมน์ (1 gap * 8px = 8px) */
@media (max-width: 480px) {
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex,
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] {
        gap: 8px !important;
        row-gap: 10px !important;
    }
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(.fcard-marker),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div:has(div[class*="st-key-fcard_"]),
    [data-testid="stHorizontalBlock"].st-key-menu_grid_flex > div[class*="st-key-fcard_"],
    div.st-key-menu_grid_flex[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 calc((100% - 8px) / 2) !important;
        width: calc((100% - 8px) / 2) !important;
        max-width: calc((100% - 8px) / 2) !important;
    }
}

/* กรอบการ์ดอาหาร: จำกัดขอบเขตเฉพาะใน .st-key-menu_grid_flex หรือ st-key-fcard_ เท่านั้น ไม่ให้กระทบ Header หรือส่วนอื่นของเว็บ */
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker),
.st-key-menu_grid_flex div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker),
div[class*="st-key-fcard_"] div[data-testid="stVerticalBlock"],
div[class*="st-key-fcard_"] [data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-fcard_"][data-testid="stVerticalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 100% !important;
    padding: 8px !important;
    border-radius: 12px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    background: #ffffff !important;
    border: 1.5px solid #ffedd5 !important;
    box-shadow: 0 4px 14px rgba(234, 88, 12, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    align-items: center !important;
    text-align: center !important;
}

/* ซ่อน marker ที่ใช้ระบุตัวการ์ด */
.fcard-marker,
div:has(> .fcard-marker) {
    display: none !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 0 !important;
}

/* เนื้อหาทุกชิ้นภายในการ์ดอาหาร ต้องขยายเต็ม 100% ของตัวการ์ด และจัดกึ่งกลาง */
div[class*="st-key-fcard_"] [data-testid="stElementContainer"],
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) [data-testid="stElementContainer"],
.st-key-menu_grid_flex div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stElementContainer"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
    text-align: center !important;
}

/* บังคับ wrapper รูปภาพทุกชั้น ให้รักษาอัตราส่วนสี่เหลี่ยมจัตุรัส 1:1 และห้ามหดตัว (flex-shrink: 0) */
div[class*="st-key-fcard_"] [data-testid="stElementContainer"]:has([data-testid="stImage"]),
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) [data-testid="stElementContainer"]:has([data-testid="stImage"]),
div[class*="st-key-fcard_"] [data-testid="stElementContainer"]:has(.no-img-box),
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) [data-testid="stElementContainer"]:has(.no-img-box) {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    aspect-ratio: 1 / 1 !important;
    display: block !important;
    flex-shrink: 0 !important;
    margin-left: auto !important;
    margin-right: auto !important;
    margin-top: 0 !important;
    margin-bottom: 6px !important;
    padding: 0 !important;
}

div[class*="st-key-fcard_"] [data-testid="stFullScreenFrame"],
.st-key-menu_grid_flex [data-testid="stFullScreenFrame"],
div[class*="st-key-fcard_"] [data-testid="stFullScreenFrame"] > div,
.st-key-menu_grid_flex [data-testid="stFullScreenFrame"] > div,
div[class*="st-key-fcard_"] [data-testid="stImage"],
.st-key-menu_grid_flex [data-testid="stImage"],
div[class*="st-key-fcard_"] [data-testid="stImageContainer"],
.st-key-menu_grid_flex [data-testid="stImageContainer"] {
    width: 100% !important;
    height: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    min-height: 0 !important;
    aspect-ratio: 1 / 1 !important;
    display: block !important;
    flex-shrink: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

/* บังคับรูปภาพ <img> แสดงผลสี่เหลี่ยมจัตุรัส 1:1 เป๊ะทุกขนาดหน้าจอ */
div[class*="st-key-fcard_"] img,
.st-key-menu_grid_flex img {
    width: 100% !important;
    height: 100% !important;
    min-width: 100% !important;
    min-height: 100% !important;
    max-width: 100% !important;
    max-height: 100% !important;
    aspect-ratio: 1 / 1 !important;
    object-fit: cover !important;
    object-position: center !important;
    border-radius: 8px !important;
    margin: 0 !important;
    padding: 0 !important;
    display: block !important;
    box-sizing: border-box !important;
    flex-shrink: 0 !important;
}

/* กล่องข้อความกรณีไม่มีรูปภาพ ให้เป็นสี่เหลี่ยมจัตุรัส 1:1 จัดกึ่งกลาง */
div[class*="st-key-fcard_"] .no-img-box,
.st-key-menu_grid_flex .no-img-box {
    width: 100% !important;
    aspect-ratio: 1 / 1 !important;
    height: 100% !important;
    min-height: 0 !important;
    max-height: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 2.2rem !important;
    background: linear-gradient(135deg, #fff7ed, #ffedd5) !important;
    border: 1px solid #fed7aa !important;
    border-radius: 8px !important;
    margin: 0 auto !important;
    box-sizing: border-box !important;
    text-align: center !important;
    flex-shrink: 0 !important;
}

/* จัดข้อความชื่ออาหารและราคาให้อยู่กึ่งกลางการ์ด */
div[class*="st-key-fcard_"] .stMarkdown,
div[class*="st-key-fcard_"] .stMarkdown p,
div[class*="st-key-fcard_"] .stMarkdown div,
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) .stMarkdown {
    text-align: center !important;
    justify-content: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
    width: 100% !important;
}

/* บังคับปุ่มสั่งอาหารเต็มความกว้าง 100% และจัดวางกึ่งกลาง */
div[class*="st-key-fcard_"] div[data-testid="stButton"],
div[class*="st-key-fcard_"] .stButton,
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) .stButton {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin: 0 auto !important;
    display: flex !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}

div[class*="st-key-fcard_"] .stButton > button,
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    min-height: 36px !important;
    height: 36px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    padding: 2px 4px !important;
    border-radius: 8px !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    text-align: center !important;
    box-sizing: border-box !important;
    margin: 0 auto !important;
}

/* Stepper แถบปรับจำนวน เต็มความกว้างการ์ด */
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"],
.st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) [data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    gap: 3px !important;
    align-items: center !important;
    margin: 0 auto !important;
}
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    min-width: 0 !important;
    flex: 1 1 0px !important;
}
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] .stButton,
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] .stButton > button {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    min-height: 32px !important;
    height: 32px !important;
    padding: 0px !important;
}

@media (max-width: 480px) {
    div[class*="st-key-fcard_"] div[data-testid="stVerticalBlock"],
    .st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) {
        padding: 6px !important;
    }
    div[class*="st-key-fcard_"] img,
    .st-key-menu_grid_flex img,
    div[class*="st-key-fcard_"] .no-img-box,
    .st-key-menu_grid_flex .no-img-box {
        aspect-ratio: 1 / 1 !important;
        width: 100% !important;
        height: 100% !important;
        border-radius: 6px !important;
    }
    div[class*="st-key-fcard_"] .stButton > button,
    .st-key-menu_grid_flex div[data-testid="stVerticalBlock"]:has(.fcard-marker) .stButton > button {
        min-height: 32px !important;
        height: 32px !important;
        font-size: 12px !important;
    }
}

/* ตกแต่งกล่องสรุปตัวเลข Metric ให้มีสีสันสะดุดตา */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #fff7ed 100%) !important;
    border: 1.5px solid #fed7aa !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    box-shadow: 0 2px 8px rgba(234, 88, 12, 0.08) !important;
}
div[data-testid="stMetricLabel"] {
    color: #7c2d12 !important;
    font-weight: 600 !important;
}
div[data-testid="stMetricValue"] {
    color: #ea580c !important;
    font-weight: 700 !important;
}

/* รูปภาพอาหารตัดมุมโค้งสวยงาม พร้อมเงา (ยกเว้นรูป QR Code ชำระเงินที่ต้องแสดงเต็มภาพไม่ถูกตัดขอบ) */
img:not(.qr-payment-img) {
    border-radius: 14px !important;
    object-fit: cover !important;
}
img.qr-payment-img {
    border-radius: 8px !important;
    object-fit: contain !important;
    width: 100% !important;
    max-width: min(78vw, 245px) !important;
    height: auto !important;
    aspect-ratio: auto !important;
    display: block !important;
    margin: 0 auto !important;
}

/* ปุ่มเลือกหมวดหมู่อาหาร ให้เป็นปุ่มทรงเหลี่ยมชัดเจน สีสันสดใส */
div[data-testid="stPills"], div[data-testid="stRadio"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    margin: 6px 0 16px 0 !important;
}
div[data-testid="stPills"] > div, div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    justify-content: center !important;
    width: 100% !important;
}

/* สไตล์สำหรับ st.pills */
div[data-testid="stPills"] button {
    border-radius: 4px !important; /* ปรับเป็นทรงเหลี่ยมชัดเจน */
    border: 2px solid #ea580c !important;
    background-color: #ffffff !important;
    color: #431407 !important;
    padding: 8px 18px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.15s ease-in-out !important;
}
div[data-testid="stPills"] button:hover {
    background-color: #ffedd5 !important;
    border-color: #c2410c !important;
}
div[data-testid="stPills"] button[aria-selected="true"],
div[data-testid="stPills"] button[data-checked="true"] {
    background-color: #ea580c !important;
    color: #ffffff !important;
    border-color: #9a3412 !important;
    box-shadow: 0 4px 10px rgba(234, 88, 12, 0.35) !important;
}

/* สไตล์ fallback สำหรับ stRadio โดยไม่ปิดกั้นการคลิก */
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    border-radius: 4px !important;
    border: 2px solid #ea580c !important;
    background-color: #ffffff !important;
    padding: 8px 18px !important;
    cursor: pointer !important;
    margin: 0 !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.15s ease-in-out !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background-color: #ffedd5 !important;
    border-color: #c2410c !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] svg {
    display: none !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input {
    opacity: 0 !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    pointer-events: none !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] p,
div[data-testid="stRadio"] label[data-baseweb="radio"] span,
div[data-testid="stRadio"] label[data-baseweb="radio"] div {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #431407 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked),
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] {
    background-color: #ea580c !important;
    border: 2px solid #9a3412 !important;
    box-shadow: 0 4px 10px rgba(234, 88, 12, 0.35) !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div,
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] p,
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] span {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* แถบเมนูแท็บสไตล์ที่คั่นหนังสือ (Bookmark Tabs) ขอบบนมน 2 มุม */
.stTabs [data-baseweb="tab-list"],
div[data-testid="stTabs"] [data-baseweb="tab-list"],
div[data-baseweb="tab-list"],
div[role="tablist"] {
    gap: 6px !important;
    background-color: transparent !important;
    border-bottom: 2.5px solid #ea580c !important;
    padding-bottom: 0px !important;
    align-items: flex-end !important;
}

/* ซ่อนเส้นขีดสีแดงเดิมของ Streamlit และเส้นใต้ทุกแบบ */
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"],
div[data-baseweb="tab-highlight"],
div[data-baseweb="tab-border"],
div[data-testid="stTabs"] hr {
    display: none !important;
    height: 0px !important;
    visibility: hidden !important;
    border: none !important;
}

/* สไตล์ของแท็บทั้งหมด (Unselected) - สี่เหลี่ยมมุมบนมน 2 มุม */
.stTabs [data-baseweb="tab"],
.stTabs button[role="tab"],
div[data-testid="stTabs"] button[role="tab"],
button[data-baseweb="tab"],
div[data-baseweb="tab-list"] > button {
    border-top-left-radius: 12px !important;   /* มนมุมบนซ้าย */
    border-top-right-radius: 12px !important;  /* มนมุมบนขวา */
    border-bottom-left-radius: 0px !important;
    border-bottom-right-radius: 0px !important;
    background-color: #fff7ed !important;       /* พื้นหลังสีครีมส้มอ่อน */
    color: #7c2d12 !important;                  /* ตัวอักษรสีน้ำตาลเข้ม */
    border: 1.5px solid #fed7aa !important;
    border-bottom: none !important;
    padding: 11px 26px !important;              /* เพิ่มระยะขอบซ้าย-ขวาให้โปร่งสบาย ไม่อึดอัด */
    margin-right: 6px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: 0 -1px 3px rgba(0, 0, 0, 0.04) !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs button[role="tab"] p,
div[data-testid="stTabs"] button[role="tab"] p {
    color: #7c2d12 !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    margin: 0 !important;
}

/* สไตล์เมื่อนำเมาส์ไปชี้ (Hover) */
.stTabs [data-baseweb="tab"]:hover,
.stTabs button[role="tab"]:hover,
div[data-testid="stTabs"] button[role="tab"]:hover,
button[data-baseweb="tab"]:hover {
    background-color: #ffedd5 !important;
    color: #ea580c !important;
    border-color: #fdba74 !important;
}

.stTabs [data-baseweb="tab"]:hover p,
.stTabs [data-baseweb="tab"]:hover span,
.stTabs button[role="tab"]:hover p,
div[data-testid="stTabs"] button[role="tab"]:hover p {
    color: #ea580c !important;
}

/* สไตล์แท็บที่ถูกเลือก/คลิกใช้งาน (Active / Selected Tab) - แถบสีพื้นหลังเด่นชัด ทรงมุมบนมน 2 มุม */
.stTabs [data-baseweb="tab"][aria-selected="true"],
.stTabs button[role="tab"][aria-selected="true"],
.stTabs [aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-baseweb="tab-list"] > button[aria-selected="true"] {
    background: linear-gradient(180deg, #ea580c 0%, #c2410c 100%) !important;
    background-color: #ea580c !important;
    color: #ffffff !important;
    border: 1.5px solid #c2410c !important;
    border-bottom: none !important;
    border-top-left-radius: 12px !important;
    border-top-right-radius: 12px !important;
    border-bottom-left-radius: 0px !important;
    border-bottom-right-radius: 0px !important;
    padding: 11px 26px !important;
    box-shadow: 0 -4px 12px rgba(234, 88, 12, 0.35) !important;
    font-weight: 700 !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] p,
.stTabs [data-baseweb="tab"][aria-selected="true"] span,
.stTabs [data-baseweb="tab"][aria-selected="true"] div,
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div,
.stTabs button[role="tab"][aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* ========================================================================== */
/* สไตล์สีเฉพาะสำหรับ 5 แท็บระบบหลังร้าน (Admin Dashboard 5 Distinct Tabs) */
/* ========================================================================== */

/* ให้แถบแท็บเลื่อนแนวนอนได้อย่างลื่นไหลบนแท็บเล็ตและมือถือ */
.st-key-admin_main_tabs [data-baseweb="tab-list"],
.stTabs [data-baseweb="tab-list"],
div[data-testid="stTabs"] [data-baseweb="tab-list"],
div[role="tablist"] {
    overflow-x: auto !important;
    scrollbar-width: thin !important;
    padding-bottom: 0px !important;
}

/* 1. แท็บที่ 1 - จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (สีแดง - Red) */
.stTabs [data-baseweb="tab"]:nth-of-type(1),
.stTabs button[role="tab"]:nth-of-type(1),
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1),
div[data-baseweb="tab-list"] button:nth-of-type(1),
div[role="tablist"] button:nth-of-type(1) {
    background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%) !important;
    background-color: #fee2e2 !important;
    border: 2px solid #ef4444 !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(1) p,
.stTabs [data-baseweb="tab"]:nth-of-type(1) span,
.stTabs button[role="tab"]:nth-of-type(1) p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) p,
div[data-baseweb="tab-list"] button:nth-of-type(1) p,
div[role="tablist"] button:nth-of-type(1) p {
    color: #991b1b !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(1):hover,
.stTabs button[role="tab"]:nth-of-type(1):hover,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1):hover,
div[data-baseweb="tab-list"] button:nth-of-type(1):hover {
    background: linear-gradient(180deg, #fecaca 0%, #fca5a5 100%) !important;
    border-color: #dc2626 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"],
.stTabs button[role="tab"]:nth-of-type(1)[aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)[aria-selected="true"],
div[data-baseweb="tab-list"] button:nth-of-type(1)[aria-selected="true"],
div[role="tablist"] button:nth-of-type(1)[aria-selected="true"] {
    background: linear-gradient(180deg, #ef4444 0%, #b91c1c 100%) !important;
    background-color: #dc2626 !important;
    border: 2px solid #991b1b !important;
    border-bottom: none !important;
    box-shadow: 0 -4px 12px rgba(220, 38, 38, 0.4) !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"] p,
.stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"] span,
.stTabs button[role="tab"]:nth-of-type(1)[aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)[aria-selected="true"] p,
div[data-baseweb="tab-list"] button:nth-of-type(1)[aria-selected="true"] p {
    color: #ffffff !important;
}

/* 2. แท็บที่ 2 - จอครัว & เคาน์เตอร์คิดเงิน (สีเขียว - Green) */
.stTabs [data-baseweb="tab"]:nth-of-type(2),
.stTabs button[role="tab"]:nth-of-type(2),
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2),
div[data-baseweb="tab-list"] button:nth-of-type(2),
div[role="tablist"] button:nth-of-type(2) {
    background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important;
    background-color: #dcfce7 !important;
    border: 2px solid #10b981 !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(2) p,
.stTabs [data-baseweb="tab"]:nth-of-type(2) span,
.stTabs button[role="tab"]:nth-of-type(2) p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) p,
div[data-baseweb="tab-list"] button:nth-of-type(2) p,
div[role="tablist"] button:nth-of-type(2) p {
    color: #065f46 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(2):hover,
.stTabs button[role="tab"]:nth-of-type(2):hover,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2):hover,
div[data-baseweb="tab-list"] button:nth-of-type(2):hover {
    background: linear-gradient(180deg, #bbf7d0 0%, #86efac 100%) !important;
    border-color: #059669 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"],
.stTabs button[role="tab"]:nth-of-type(2)[aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"],
div[data-baseweb="tab-list"] button:nth-of-type(2)[aria-selected="true"],
div[role="tablist"] button:nth-of-type(2)[aria-selected="true"] {
    background: linear-gradient(180deg, #10b981 0%, #047857 100%) !important;
    background-color: #059669 !important;
    border: 2px solid #065f46 !important;
    border-bottom: none !important;
    box-shadow: 0 -4px 12px rgba(16, 185, 129, 0.4) !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"] p,
.stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"] span,
.stTabs button[role="tab"]:nth-of-type(2)[aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"] p,
div[data-baseweb="tab-list"] button:nth-of-type(2)[aria-selected="true"] p {
    color: #ffffff !important;
}

/* 3. แท็บที่ 3 - รายงานยอดขาย (สีม่วง - Purple) */
.stTabs [data-baseweb="tab"]:nth-of-type(3),
.stTabs button[role="tab"]:nth-of-type(3),
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3),
div[data-baseweb="tab-list"] button:nth-of-type(3),
div[role="tablist"] button:nth-of-type(3) {
    background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important;
    background-color: #f3e8ff !important;
    border: 2px solid #8b5cf6 !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(3) p,
.stTabs [data-baseweb="tab"]:nth-of-type(3) span,
.stTabs button[role="tab"]:nth-of-type(3) p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) p,
div[data-baseweb="tab-list"] button:nth-of-type(3) p,
div[role="tablist"] button:nth-of-type(3) p {
    color: #5b21b6 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(3):hover,
.stTabs button[role="tab"]:nth-of-type(3):hover,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3):hover,
div[data-baseweb="tab-list"] button:nth-of-type(3):hover {
    background: linear-gradient(180deg, #e9d5ff 0%, #d8b4fe 100%) !important;
    border-color: #7c3aed !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"],
.stTabs button[role="tab"]:nth-of-type(3)[aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"],
div[data-baseweb="tab-list"] button:nth-of-type(3)[aria-selected="true"],
div[role="tablist"] button:nth-of-type(3)[aria-selected="true"] {
    background: linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%) !important;
    background-color: #7c3aed !important;
    border: 2px solid #5b21b6 !important;
    border-bottom: none !important;
    box-shadow: 0 -4px 12px rgba(124, 58, 237, 0.4) !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"] p,
.stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"] span,
.stTabs button[role="tab"]:nth-of-type(3)[aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"] p,
div[data-baseweb="tab-list"] button:nth-of-type(3)[aria-selected="true"] p {
    color: #ffffff !important;
}

/* 4. แท็บที่ 4 - ประวัติลูกค้า (สีส้ม - Orange) */
.stTabs [data-baseweb="tab"]:nth-of-type(4),
.stTabs button[role="tab"]:nth-of-type(4),
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4),
div[data-baseweb="tab-list"] button:nth-of-type(4),
div[role="tablist"] button:nth-of-type(4) {
    background: linear-gradient(180deg, #ffedd5 0%, #fed7aa 100%) !important;
    background-color: #ffedd5 !important;
    border: 2px solid #f97316 !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(4) p,
.stTabs [data-baseweb="tab"]:nth-of-type(4) span,
.stTabs button[role="tab"]:nth-of-type(4) p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4) p,
div[data-baseweb="tab-list"] button:nth-of-type(4) p,
div[role="tablist"] button:nth-of-type(4) p {
    color: #9a3412 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(4):hover,
.stTabs button[role="tab"]:nth-of-type(4):hover,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4):hover,
div[data-baseweb="tab-list"] button:nth-of-type(4):hover {
    background: linear-gradient(180deg, #fed7aa 0%, #fdba74 100%) !important;
    border-color: #ea580c !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"],
.stTabs button[role="tab"]:nth-of-type(4)[aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)[aria-selected="true"],
div[data-baseweb="tab-list"] button:nth-of-type(4)[aria-selected="true"],
div[role="tablist"] button:nth-of-type(4)[aria-selected="true"] {
    background: linear-gradient(180deg, #f97316 0%, #c2410c 100%) !important;
    background-color: #ea580c !important;
    border: 2px solid #9a3412 !important;
    border-bottom: none !important;
    box-shadow: 0 -4px 12px rgba(234, 88, 12, 0.4) !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"] p,
.stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"] span,
.stTabs button[role="tab"]:nth-of-type(4)[aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)[aria-selected="true"] p,
div[data-baseweb="tab-list"] button:nth-of-type(4)[aria-selected="true"] p {
    color: #ffffff !important;
}

/* 5. แท็บที่ 5 - จัดการเมนูอาหาร (สีฟ้า - Sky Blue) */
.stTabs [data-baseweb="tab"]:nth-of-type(5),
.stTabs button[role="tab"]:nth-of-type(5),
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5),
div[data-baseweb="tab-list"] button:nth-of-type(5),
div[role="tablist"] button:nth-of-type(5) {
    background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important;
    background-color: #e0f2fe !important;
    border: 2px solid #0ea5e9 !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(5) p,
.stTabs [data-baseweb="tab"]:nth-of-type(5) span,
.stTabs button[role="tab"]:nth-of-type(5) p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) p,
div[data-baseweb="tab-list"] button:nth-of-type(5) p,
div[role="tablist"] button:nth-of-type(5) p {
    color: #075985 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(5):hover,
.stTabs button[role="tab"]:nth-of-type(5):hover,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5):hover,
div[data-baseweb="tab-list"] button:nth-of-type(5):hover {
    background: linear-gradient(180deg, #bae6fd 0%, #7dd3fc 100%) !important;
    border-color: #0284c7 !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"],
.stTabs button[role="tab"]:nth-of-type(5)[aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)[aria-selected="true"],
div[data-baseweb="tab-list"] button:nth-of-type(5)[aria-selected="true"],
div[role="tablist"] button:nth-of-type(5)[aria-selected="true"] {
    background: linear-gradient(180deg, #0ea5e9 0%, #0369a1 100%) !important;
    background-color: #0284c7 !important;
    border: 2px solid #075985 !important;
    border-bottom: none !important;
    box-shadow: 0 -4px 12px rgba(2, 132, 199, 0.4) !important;
}
.stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"] p,
.stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"] span,
.stTabs button[role="tab"]:nth-of-type(5)[aria-selected="true"] p,
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)[aria-selected="true"] p,
div[data-baseweb="tab-list"] button:nth-of-type(5)[aria-selected="true"] p {
    color: #ffffff !important;
}

/* ซ่อน Header, Toolbar, Fork icon, GitHub, Share, MainMenu และ Watermark ทั้งหมดของ Streamlit Cloud */
header,
header[data-testid="stHeader"],
[data-testid="stHeader"],
div[data-testid="stHeader"] {
    display: none !important;
    visibility: hidden !important;
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
#MainMenu,
footer,
footer[data-testid="stFooter"],
div[class*="viewerBadge"],
div[class*="ProfileButton"],
div[class*="stToolbarActions"],
a[href*="github.com"],
button[title*="Fork"],
button[title*="fork"],
button[aria-label*="Fork"],
button[aria-label*="fork"] {
    display: none !important;
    visibility: hidden !important;
    height: 0px !important;
    width: 0px !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* ดึงเนื้อหาเว็บขึ้นมาชิดขอบบนสุดเพื่อไม่ให้มีช่องว่างสีขาวเหลือจาก header */
.main .block-container,
[data-testid="stAppViewContainer"] > .main {
    padding-top: 0.8rem !important;
}
</style>
<script>
(function() {
    function hideStreamlitHeaders() {
        try {
            var selectors = [
                'header[data-testid="stHeader"]',
                '[data-testid="stHeader"]',
                'header',
                '[data-testid="stToolbar"]',
                '[data-testid="stToolbarActions"]',
                '[data-testid="stDecoration"]',
                '[data-testid="stStatusWidget"]',
                '[data-testid="stAppDeployButton"]',
                '#MainMenu',
                'footer',
                'div[class*="viewerBadge"]',
                'div[class*="ProfileButton"]'
            ];
            selectors.forEach(function(s) {
                var items = document.querySelectorAll(s);
                items.forEach(function(el) {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('height', '0px', 'important');
                    el.style.setProperty('opacity', '0', 'important');
                    el.style.setProperty('pointer-events', 'none', 'important');
                });
            });
        } catch(e) {}
    }

    // ซ่อนทันทีและตั้ง interval ตรวจสอบเป็นระยะ
    hideStreamlitHeaders();
    document.addEventListener("DOMContentLoaded", hideStreamlitHeaders);
    window.addEventListener("load", hideStreamlitHeaders);
    setInterval(hideStreamlitHeaders, 500);

    try {
        var currentHref = window.location.href;
        var currentPath = window.location.pathname;
        var currentSearch = window.location.search;

        // ตรวจสอบว่าต้องดันออกจาก iframe พรีวิว (/~/+/) หรือไม่
        if (window.top !== window.self && (window.location.pathname.includes('/~/+/') || currentHref.includes('mode=admin?mode=admin'))) {
            var isAdmin = currentHref.includes('mode=admin');
            var matchTable = currentHref.match(/table=([0-9]+)/);
            var destSearch = '';
            if (isAdmin) destSearch = '?mode=admin';
            else if (matchTable) destSearch = '?table=' + matchTable[1];
            try {
                window.top.location.href = window.top.location.origin + '/' + destSearch;
            } catch(e) {}
        }
    } catch(e) {}
})();
</script>
    """, unsafe_allow_html=True)


