# ==============================================================================
#  ฟ้าใสตำนัว (Fahsai Tum Nua) - ระบบสั่งอาหารโต๊ะ & จอครัวอัจฉริยะ (Smart POS)
# ==============================================================================
# โครงสร้างการทำงานของโปรแกรม:
# 1.  ฐานข้อมูล SQLite (restaurant.db): บันทึกเมนูอาหาร, โต๊ะ, ออเดอร์ และใบเสร็จ
# 2.  จัดการโต๊ะอาหาร & QR-Code: เพิ่ม/ลบโต๊ะ สร้าง QR-Code อัตโนมัติ และเคลียร์โต๊ะ
# 3.  จอครัว & เคาน์เตอร์คิดเงิน (KDS): แสดงออเดอร์สด อัปเดตทุก 3 วินาที พร้อมเสียงเตือน
# 4.  เมนูขายดี: จัดอันดับเมนูยอดนิยม ยอดขายรวม และสรุปตามหมวดหมู่อาหาร
# 5.  ฝั่งลูกค้า: สแกน QR Code เข้ามาสั่งอาหาร จัดการตะกร้า และติดตามสถานะแบบเรียลไทม์
# ==============================================================================

# --- ไลบรารีที่จำเป็นสำหรับระบบ ---
import streamlit as st                      # เฟรมเวิร์กหลักสำหรับสร้างเว็บแอปพลิเคชัน
import streamlit.components.v1 as components # ใช้สำหรับแทรก HTML/JS เช่น หน้าต่างพิมพ์ใบเสร็จ
import sqlite3                             # ระบบจัดการฐานข้อมูลในตัวเครื่อง (ไม่ต้องลงเซิร์ฟเวอร์แยก)
import os                                  # จัดการไฟล์และพาธของระบบปฏิบัติการ
import base64                              # เข้ารหัสไฟล์รูปภาพและเสียงเป็นข้อความ Base64
import wave                                # สร้างและจัดการไฟล์เสียงแบบคลื่นเสียง WAV
import struct                              # แปลงข้อมูลตัวเลขเป็นไบนารีสำหรับไฟล์เสียง
import math                                # ฟังก์ชันคณิตศาสตร์ (ใช้คำนวณคลื่นเสียงกระดิ่ง)
import io                                  # จัดการข้อมูลในหน่วยความจำ RAM (In-Memory Buffer)
from datetime import datetime, timedelta, timezone # จัดการวันและเวลา
from urllib.parse import quote             # เข้ารหัส URL สำหรับสร้างภาพ QR Code
import hashlib                              # แฮชรหัสผ่านอย่างปลอดภัย (SHA-256 + Salt)
import hmac                                 # เปรียบเทียบรหัสผ่านแบบ Timing-attack safe

# --- ตั้งค่าเวลาประเทศไทย (UTC+7 / Asia/Bangkok) ---
# เนื่องจากเซิร์ฟเวอร์ Cloud (เช่น Streamlit Cloud) มักตั้งเวลาเป็น UTC (ช้ากว่าไทย 7 ชม.)
# เราจึงล็อกเขตเวลาให้เป็น UTC+7 โดยตรง เพื่อให้เวลาในระบบตรงกับเวลาจริงในประเทศไทยเสมอ
TH_TZ = timezone(timedelta(hours=7))

def get_thai_now():
    """ฟังก์ชันคืนค่าวันและเวลาปัจจุบันของประเทศไทย (UTC+7)"""
    return datetime.now(TH_TZ)

# --- ตั้งค่าหน้าเว็บ Streamlit เบื้องต้น ---
st.set_page_config(
    page_title="ฟ้าใสตำนัว",               # ชื่อที่จะแสดงบนแท็บของเบราว์เซอร์
    page_icon="static/img/favicon.ico" if os.path.exists("static/img/favicon.ico") else "", # ไอคอน Favicon ของแท็บเว็บ
    layout="wide",                          # ใช้พื้นที่หน้าจอแบบเต็มความกว้าง (Wide mode)
    initial_sidebar_state="collapsed"       # ซ่อนแถบเมนูด้านข้างเริ่มต้น เพื่อให้ดูเหมือน App มือถือ
)

# --- CSS อัจฉริยะ ปรับหน้าตาให้สวยงาม รองรับทั้ง มือถือ (iOS/Android), แท็บเล็ต, iPad และ คอมพิวเตอร์ ---
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

/*  สไตล์การ์ดอาหาร: Responsive Flex Grid ชิดกัน เว้นระยะห่างเล็กน้อย จำนวนตามความกว้างหน้าจอ */
div[class*="st-key-menu_grid_flex"] > div,
div[class*="st-key-menu_grid_flex"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
    row-gap: 12px !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    width: 100% !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-fcard_"]),
div[class*="st-key-fcard_"] {
    width: 124px !important;
    max-width: 124px !important;
    min-width: 124px !important;
    flex: 0 0 124px !important;
    padding: 6px !important;
    border-radius: 12px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stVerticalBlock"],
div[class*="st-key-fcard_"] div[data-testid="stVerticalBlock"] {
    width: 112px !important;
    max-width: 112px !important;
    margin: 0 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stImage"],
div[class*="st-key-fcard_"] div[data-testid="stImage"] {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    margin: 0 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) img,
div[class*="st-key-fcard_"] img {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    height: 104px !important;
    max-height: 104px !important;
    object-fit: cover !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
    display: block !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .no-img-box,
div[class*="st-key-fcard_"] .no-img-box {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    height: 104px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 2rem !important;
    background: linear-gradient(135deg, #fff7ed, #ffedd5) !important;
    border: 1px solid #fed7aa !important;
    border-radius: 8px !important;
    margin: 0 auto 4px auto !important;
}

/* บังคับปุ่มเพิ่มให้กว้างเท่ากับความกว้างของภาพ (112px) เป๊ะ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stButton"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .stButton,
div[class*="st-key-fcard_"] div[data-testid="stButton"],
div[class*="st-key-fcard_"] .stButton {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    margin: 0 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .stButton > button,
div[class*="st-key-fcard_"] .stButton > button {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    min-height: 34px !important;
    height: 34px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    padding: 2px 4px !important;
    border-radius: 8px !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    box-sizing: border-box !important;
}

/* Stepper แถบปรับจำนวน */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stHorizontalBlock"],
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] {
    width: 112px !important;
    max-width: 112px !important;
    min-width: 112px !important;
    gap: 3px !important;
    align-items: center !important;
    margin: 0 auto !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    min-width: 0 !important;
    flex: 1 1 0px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stHorizontalBlock"] .stButton,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stHorizontalBlock"] .stButton > button,
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] .stButton,
div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] .stButton > button {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    min-height: 32px !important;
    height: 32px !important;
    padding: 0px !important;
}
@media (max-width: 640px) {
    div[class*="st-key-menu_grid_flex"] > div,
    div[class*="st-key-menu_grid_flex"] {
        gap: 6px !important;
        row-gap: 8px !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-fcard_"]),
    div[class*="st-key-fcard_"] {
        width: 110px !important;
        max-width: 110px !important;
        min-width: 110px !important;
        flex: 0 0 110px !important;
        padding: 4px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stVerticalBlock"],
    div[class*="st-key-fcard_"] div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stImage"],
    div[class*="st-key-fcard_"] div[data-testid="stImage"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) img,
    div[class*="st-key-fcard_"] img,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .no-img-box,
    div[class*="st-key-fcard_"] .no-img-box,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) div[data-testid="stButton"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .stButton,
    div[class*="st-key-fcard_"] div[data-testid="stButton"],
    div[class*="st-key-fcard_"] .stButton,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .stButton > button,
    div[class*="st-key-fcard_"] .stButton > button,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) [data-testid="stHorizontalBlock"],
    div[class*="st-key-fcard_"] [data-testid="stHorizontalBlock"] {
        width: 102px !important;
        max-width: 102px !important;
        min-width: 102px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) img,
    div[class*="st-key-fcard_"] img,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .no-img-box,
    div[class*="st-key-fcard_"] .no-img-box {
        height: 95px !important;
        max-height: 95px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fcard-marker) .stButton > button,
    div[class*="st-key-fcard_"] .stButton > button {
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

/* รูปภาพอาหารตัดมุมโค้งสวยงาม พร้อมเงา */
img {
    border-radius: 14px !important;
    object-fit: cover !important;
}

/*  ปุ่มเลือกหมวดหมู่อาหาร ให้เป็นปุ่มทรงเหลี่ยมชัดเจน สีสันสดใส */
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

/*  แถบเมนูแท็บสไตล์ที่คั่นหนังสือ (Bookmark Tabs) ขอบบนมน 2 มุม */
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

/*  สไตล์ของแท็บทั้งหมด (Unselected) - สี่เหลี่ยมมุมบนมน 2 มุม */
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

/*  สไตล์แท็บที่ถูกเลือก/คลิกใช้งาน (Active / Selected Tab) - แถบสีพื้นหลังเด่นชัด ทรงมุมบนมน 2 มุม */
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

/* ซ่อนแถบเมนูที่ไม่จำเป็นของ Streamlit เพื่อประสบการณ์แบบ App แท้ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
<script>
(function() {
    try {
        var currentHref = window.location.href;
        var currentPath = window.location.pathname;
        var currentSearch = window.location.search;

        // ถ้าพบว่าติด /~/+/ หรือมี mode=admin ซ้ำซ้อน หรือ parameter เพี้ยน
        if (currentHref.includes('mode=admin') || currentHref.includes('/~/+/')) {
            var isAdmin = currentHref.includes('mode=admin');
            var isTable = currentHref.includes('table=');
            var cleanSearch = '';
            
            if (isAdmin) {
                cleanSearch = '?mode=admin';
            } else if (isTable) {
                var match = currentHref.match(/table=([0-9]+)/);
                cleanSearch = match ? '?table=' + match[1] : '';
            }

            var cleanUrl = window.location.origin + '/' + cleanSearch;

            // 1. ถ้าอยู่ภายใน iframe พรีวิวของ streamlit cloud (/~/+/) ให้ดันออกสู่หน้าต่างหลัก
            if (window.top !== window.self && (window.location.pathname.includes('/~/+/') || currentHref.includes('mode=admin?mode=admin'))) {
                window.top.location.href = cleanUrl;
            } else if (window.location.href !== cleanUrl && (currentHref.includes('mode=admin?mode=admin') || currentHref.includes('/+/'))) {
                // 2. ถ้าเป็นหน้าต่างหลัก แต่ URL มีความซ้ำซ้อน ให้คลีน URL ทันที
                window.history.replaceState(null, '', cleanUrl);
            }
        }
    } catch(e) {}
})();
</script>
""", unsafe_allow_html=True)

# ==============================================================================
#  การจัดการฐานข้อมูล SQLite (Database Setup)
# ==============================================================================
# ระบบใช้ SQLite ซึ่งเก็บข้อมูลทั้งหมดไว้ในไฟล์เดียวชื่อ "restaurant.db"
# ข้อดี: เบา รวดเร็ว พกพาง่าย ไม่ต้องติดตั้ง Database Server เพิ่มเติม

DB_NAME = "restaurant.db"

def init_db():
    """
    ฟังก์ชันสร้างตารางฐานข้อมูลที่จำเป็น (ถ้ายังไม่มี) 
    และบันทึกข้อมูลเมนูอาหารเริ่มต้นของร้านฟ้าใสตำนัว
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. ตารางเมนูอาหาร (menu_items)
    # เก็บชื่ออาหาร หมวดหมู่ ราคา ต้นทุน รูปภาพ และคำอธิบาย
    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,          -- ชื่อเมนูอาหาร (ห้ามซ้ำ)
            category TEXT NOT NULL,             -- หมวดหมู่อาหาร (เช่น ส้มตำ, ย่าง, ต้ม)
            price REAL NOT NULL,                -- ราคาขาย (บาท)
            cost REAL DEFAULT 0,                -- ต้นทุนวัตถุดิบ (บาท)
            image TEXT,                         -- URL รูปภาพอาหาร
            description TEXT                    -- คำอธิบายความอร่อย/จุดเด่น
        )
    ''')

    # 2. ตารางโต๊ะอาหารในร้าน (tables)
    # เก็บหมายเลขโต๊ะ ชื่อโต๊ะ และสถานะ (ว่าง/มีลูกค้า)
    # *หมายเหตุ: ค่าเริ่มต้นไม่มีโต๊ะ โดยเจ้าของร้านสามารถกดเพิ่ม/ลบโต๊ะได้เองตามต้องการ
    c.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY,
            table_number INTEGER NOT NULL UNIQUE, -- หมายเลขโต๊ะ เช่น 1, 2, 3
            name TEXT,                            -- ชื่อเรียกโต๊ะ เช่น "โต๊ะที่ 1", "ซุ้มริมน้ำ 2"
            status TEXT DEFAULT 'available'       -- สถานะโต๊ะ
        )
    ''')

    # 3. ตารางออเดอร์/บิลหลัก (orders)
    # เก็บรหัสบิล โต๊ะที่สั่ง สถานะบิล ยอดเงินรวม และวันเวลาที่สั่ง
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,          -- หมายเลขโต๊ะที่สั่ง
            status TEXT NOT NULL DEFAULT 'pending', -- สถานะบิล: pending -> accepted -> cooked -> served -> paid -> archived
            total_price REAL NOT NULL,          -- ยอดเงินรวมทั้งสิ้นของบิล (บาท)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันและเวลาที่สั่งอาหาร
        )
    ''')

    # 4. ตารางรายการอาหารย่อยในแต่ละบิล (order_items)
    # เก็บว่าในบิลนั้นๆ สั่งอาหารจานใดบ้าง จำนวนกี่จาน ราคา และสถานะการปรุงแต่ละจาน
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,          -- เชื่อมกับ orders.id
            item_name TEXT NOT NULL,            -- ชื่อเมนูอาหารที่สั่ง
            price REAL NOT NULL,                -- ราคาต่อหน่วย ณ ตอนที่สั่ง
            cost REAL DEFAULT 0,                -- ต้นทุนต่อหน่วย
            quantity INTEGER NOT NULL,          -- จำนวนจานที่สั่ง
            note TEXT,                          -- โน้ตเพิ่มเติม เช่น เผ็ดน้อย, ไม่ใส่ชูรส
            status TEXT DEFAULT 'pending'       -- สถานะแต่ละจาน: pending(กำลังปรุง) -> cooked(ปรุงเสร็จ) -> served(เสิร์ฟแล้ว)
        )
    ''')

    # 5. ตารางสมาชิกสะสมแต้ม (members)
    # เก็บข้อมูลสมาชิก: ชื่อ, นามสกุล, หมายเลขโทรศัพท์ และคะแนนสะสม
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,           -- ชื่อสมาชิก
            last_name TEXT NOT NULL,            -- นามสกุล
            phone TEXT NOT NULL UNIQUE,         -- หมายเลขโทรศัพท์ (ห้ามซ้ำ)
            points INTEGER DEFAULT 0,           -- คะแนนสะสม
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันเวลาที่สมัครสมาชิก
        )
    ''')

    # ตรวจสอบและอัปเกรดคอลัมน์ status ในตาราง order_items แบบอัตโนมัติ (Backward Compatibility)
    c.execute("PRAGMA table_info(order_items)")
    existing_cols = [col[1] for col in c.fetchall()]
    if 'status' not in existing_cols:
        c.execute("ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT 'pending'")
    c.execute("UPDATE order_items SET status = 'pending' WHERE status IS NULL")

    # ตรวจสอบและอัปเกรดคอลัมน์ระบบสมาชิกและส่วนลดในตาราง orders แบบอัตโนมัติ
    c.execute("PRAGMA table_info(orders)")
    order_cols = [col[1] for col in c.fetchall()]
    if 'subtotal' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN subtotal REAL DEFAULT 0")
    if 'discount' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN discount REAL DEFAULT 0")
    if 'points_used' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_used INTEGER DEFAULT 0")
    if 'points_earned' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_earned INTEGER DEFAULT 0")
    if 'member_phone' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN member_phone TEXT DEFAULT NULL")

    # บันทึกชุดเมนูอาหารทั้งหมดของร้าน "ฟ้าใสตำนัว" (10 หมวดหมู่ 131 เมนูแซ่บ)
    fahsai_menu = [
        # --- 1. หมวด "ตำนัว" (16 เมนู) ---
        ("ตำไทย", "ตำนัว", 50, 18, "static/img/menu/menu1.png", "รสเปรี้ยวหวานกลมกล่อม ถั่วคั่วใหม่ กุ้งแห้งเกรดเอ"),
        ("ตำไทยไข่เค็ม", "ตำนัว", 60, 22, "static/img/menu/menu8.png", "ตำไทยครบรส ท็อปไข่เค็มเต็มใบ มันนัวเข้ากัน"),
        ("ตำไทยปู", "ตำนัว", 50, 18, "static/img/menu/menu9.png", "ตำไทยรสเด็ด ใส่ปูดองเค็มสะอาด นัวกลมกล่อม"),
        ("ตำไทยปูปลาร้า", "ตำนัว", 50, 18, "static/img/menu/menu10.png", "ตำไทยผสมน้ำปลาร้าต้มสุกสูตรเด็ด แซ่บนัวลงตัว"),
        ("ตำปูปลาร้า", "ตำนัว", 50, 18, "static/img/menu/menu11.png", "เส้นมะละกอกรอบ ปลาร้าต้มสุกนัวเข้มข้น รสอีสานแท้"),
        ("ตำปลาร้า", "ตำนัว", 45, 15, "static/img/menu/menu12.png", "ปลาร้านัวกลิ่นหอม รสแซ่บจัดจ้าน ซดน้ำส้มตำฟิน"),
        ("ตำปู", "ตำนัว", 45, 15, "static/img/menu/menu2.png", "ตำปูเค็มสะอาด รสเปรี้ยวเผ็ดเค็มกำลังดี"),
        ("ตำซั่ว", "ตำนัว", 50, 18, "static/img/menu/menu3.png", "ตำปลาร้าใส่เส้นขนมจีนนุ่มลื่น แคบหมูกรอบ"),
        ("ตำแตง", "ตำนัว", 50, 18, "static/img/menu/menu4.png", "แตงกวาสดกรอบฉ่ำน้ำ คลุกเคล้าน้ำปลาร้าแซ่บนัว"),
        ("ตำถั่ว", "ตำนัว", 50, 18, "static/img/menu/menu5.png", "ถั่วฝักยาวกรุบกรอบ ตำพริกแห้งและปลาร้าเข้มข้น"),
        ("ตำมะม่วง", "ตำนัว", 50, 18, "static/img/menu/menu6.png", "มะม่วงเปรี้ยวกำลังดี ตำใส่น้ำปลาร้า แซ่บจี๊ดถึงใจ"),
        ("ตำข้าวโพด", "ตำนัว", 60, 22, "static/img/menu/menu7.png", "ข้าวโพดหวานเม็ดเต่ง ตำคลุกน้ำยำรสแซ่บกลมกล่อม"),
        ("ตำข้าวโพดไข่เค็ม", "ตำนัว", 70, 26, "static/img/menu/menu13.png", "ข้าวโพดหวานมัน ท็อปไข่เค็มชิ้นโต นัวฟิน"),
        ("ตำหมูยอ", "ตำนัว", 60, 24, "static/img/menu/menu17.png", "หมูยอเนื้อแน่นหอมพริกไทย ตำคลุกน้ำส้มตำนัว"),
        ("ตำหอยดอง", "ตำนัว", 55, 20, "static/img/menu/menu18.png", "หอยดองสะอาดรสกลมกล่อม ตำพริกสดแซ่บถึงใจ"),
        ("ตำป่า", "ตำนัว", 70, 28, "static/img/menu/menu21.png", "ตำป่าเครื่องแน่น หน่อไม้ หอย ผักกาดดอง แคบหมู ขนมจีน"),

        # --- 2. หมวด "ตำพรีเมียม" (13 เมนู) ---
        ("ตำถาดฟ้าใสตำนัว", "ตำพรีเมียม", 159, 60, "static/img/menu/menu20.png", "ตำถาดไซส์ใหญ่ เครื่องแน่น หมูยอ แคบหมู ไข่ต้ม ผักครบ"),
        ("ตำกุ้งสด", "ตำพรีเมียม", 89, 36, "static/img/menu/menu22.png", "กุ้งสดเนื้อเด้งหวานฉ่ำ เคล้าน้ำปลาร้านัวถึงใจ"),
        ("ตำกุ้งสุก", "ตำพรีเมียม", 89, 36, "static/img/menu/menu23.png", "กุ้งลวกสุกพอดีเนื้อหวานเด้ง ตำรสเปรี้ยวเผ็ดกลมกล่อม"),
        ("ตำแซลมอน", "ตำพรีเมียม", 149, 65, "static/img/menu/menu24.png", "แซลมอนสดนำเข้าเกรดซาชิมิ ตำน้ำยำรสเด็ดเข้มข้น"),
        ("ตำหอยแครง", "ตำพรีเมียม", 99, 40, "static/img/menu/menu14.png", "หอยแครงสดลวกสะดุ้ง เนื้อหวานกรุบ ตำแซ่บนัว"),
        ("ตำหมึกสาย", "ตำพรีเมียม", 99, 40, "static/img/menu/menu15.png", "หมึกสายลวกกรุบกรอบ เด้งสู้ฟัน คลุกน้ำปลาร้าแซ่บ"),
        ("ตำทะเลรวม", "ตำพรีเมียม", 139, 55, "static/img/menu/menu16.png", "ยกทะเลมาไว้ในครก กุ้ง หมึก หอยแครง จัดเต็ม"),
        ("ตำหมูกรอบ", "ตำพรีเมียม", 89, 36, "static/img/menu/menu19.png", "หมูกรอบหนังฟูกรอบนอกนุ่มใน คลุกส้มตำรสเด็ด"),
        ("ตำคอหมูย่าง", "ตำพรีเมียม", 89, 36, "static/img/menu/menu25.png", "คอหมูย่างเตาถ่านหอมๆ ตำคลุกน้ำส้มตำสุดฟิน"),
        ("ตำไข่เยี่ยวม้า", "ตำพรีเมียม", 65, 25, "static/img/menu/menu29.png", "ไข่เยี่ยวม้าเนื้อเด้งมันนัว เข้ากันกับส้มตำรสจัด"),
        ("ตำเส้นเล็กหมูยอกากหมู", "ตำพรีเมียม", 79, 30, "static/img/menu/menu30.png", "เส้นเล็กเหนียวนุ่ม คลุกน้ำปลาร้า หมูยอและกากหมูเจียวใหม่"),
        ("ตำมาม่าปลาร้านัว", "ตำพรีเมียม", 69, 26, "static/img/menu/menu31.png", "เส้นมาม่าลวกกำลังดี ตำคลุกน้ำปลาร้าเครื่องแน่น"),
        ("ตำด้องแด้ง", "ตำพรีเมียม", 60, 22, "static/img/menu/menu32.png", "เส้นด้องแด้งหนึบหนับ เอกลักษณ์อีสานแท้ ตำปลาร้านัว"),

        # --- 3. หมวด "ยำแซ่บ" (15 เมนู) ---
        ("ยำวุ้นเส้นหมูสับ", "ยำแซ่บ", 70, 26, "static/img/menu/menu34.png", "วุ้นเส้นเหนียวนุ่ม ยำใส่หมูสับรวน มะนาวสดพริกขี้หนู"),
        ("ยำวุ้นเส้นโบราณ", "ยำแซ่บ", 75, 28, "static/img/menu/menu33.png", "ยำวุ้นเส้นทรงเครื่อง ถั่วคั่ว กุ้งแห้ง หมูสับ หอมพริกเผา"),
        ("ยำวุ้นเส้นทะเล", "ยำแซ่บ", 99, 40, "static/img/menu/menu35.png", "วุ้นเส้นคลุกเคล้ากุ้งและปลาหมึกสด น้ำยำรสจี๊ดจ๊าด"),
        ("ยำมาม่าหมูสับ", "ยำแซ่บ", 70, 26, "static/img/menu/menu36.png", "มาม่าลวกเหนียวนุ่ม ยำหมูสับและหมูยอ รสแซ่บถึงใจ"),
        ("ยำมาม่ารวมมิตร", "ยำแซ่บ", 99, 40, "static/img/menu/menu26.png", "มาม่ารวมมิตร กุ้ง หมึก หมูยอ ไส้กรอก ครบเครื่อง"),
        ("ยำหมูยออุบล", "ยำแซ่บ", 70, 26, "static/img/menu/menu27.png", "หมูยออุบลแท้เนื้อเด้ง หอมพริกไทย ยำน้ำมะนาวสด"),
        ("ยำหมูยอไข่แดงเค็ม", "ยำแซ่บ", 89, 36, "static/img/menu/menu28.png", "หมูยออุบลจับคู่ไข่แดงเค็มมันหนึบ น้ำยำปลาร้า/ไม่ปลาร้า"),
        ("ยำกุนเชียง", "ยำแซ่บ", 70, 26, "static/img/menu/menu37.png", "กุนเชียงหมูทอดหอมหวาน ยำตัดรสเปรี้ยวเผ็ดแตงกวากรอบ"),
        ("ยำเล็บมือนาง", "ยำแซ่บ", 75, 28, "static/img/menu/menu41.png", "เล็บมือนางกรุบกรอบ ยำพริกสดมะนาวแท้ เคี้ยวเพลิน"),
        ("ยำไข่ดาว", "ยำแซ่บ", 60, 22, "static/img/menu/menu42.png", "ไข่ดาวทอดกรอบไข่แดงเยิ้ม ราดน้ำยำหมูสับรสเด็ด"),
        ("ยำไข่เยี่ยวม้า", "ยำแซ่บ", 70, 26, "static/img/menu/menu43.png", "ไข่เยี่ยวม้าทรงเครื่อง โรยขิงดอง หอมแดง พริกขี้หนูซอย"),
        ("ยำกุ้งสดน้ำปลาร้า", "ยำแซ่บ", 99, 42, "static/img/menu/menu44.png", "กุ้งสดเนื้อหวานเด้ง คลุกน้ำยำปลาร้าต้มสุกหอมนัว"),
        ("ยำแซลมอนน้ำปลาร้า", "ยำแซ่บ", 159, 68, "static/img/menu/menu45.png", "แซลมอนซาชิมิชิ้นหนา คลุกเคล้าน้ำยำปลาร้ารสจัดจ้าน"),
        ("ยำหอยแครง", "ยำแซ่บ", 109, 45, "static/img/menu/menu46.png", "หอยแครงลวกสุกพอดี ยำใส่ตะไคร้ซอย หอมแดง พริกสด"),
        ("ยำทะเลรวมน้ำยำซีฟู้ด", "ยำแซ่บ", 149, 62, "static/img/menu/menu47.png", "กุ้ง หมึก หอยแครง ราดน้ำยำซีฟู้ดพริกขี้หนูสวนแท้"),

        # --- 4. หมวด "ลาบ & ก้อย & น้ำตก" (13 เมนู) ---
        ("ลาบหมู", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu48.png", "หมูสับคลุกข้าวคั่วใหม่ พริกป่น มะนาวสด หอมสะระแหน่"),
        ("ลาบหมูตับหวาน", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu38.png", "ลาบหมูสับผสมตับหมูลวกสุกกำลังดี นุ่มหวานไม่แข็ง"),
        ("ลาบไก่", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu39.png", "เนื้อไก่สับนุ่ม คลุกเคล้าเครื่องลาบอีสานแท้หอมข้าวคั่ว"),
        ("ลาบเป็ดอุดร", "ลาบ & ก้อย & น้ำตก", 85, 35, "static/img/menu/menu40.png", "ลาบเป็ดสูตรอุดรแท้ หอมข่าคั่วสมุนไพร โรยหนังเป็ดทอดกรอบ"),
        ("ลาบเนื้อสุก", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu49.png", "เนื้อวัวสับรวนสุก คลุกเครื่องลาบพริกป่นข้าวคั่วหอมกรุ่น"),
        ("ลาบปลาดุกย่าง", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu53.png", "ปลาดุกย่างเตาถ่านแกะเนื้อสับ คลุกเครื่องลาบสมุนไพร"),
        ("ลาบปลาหมึก", "ลาบ & ก้อย & น้ำตก", 99, 40, "static/img/menu/menu54.png", "ปลาหมึกสดลวกเด้งกรอบ คลุกเครื่องลาบรสแซ่บจี๊ด"),
        ("ก้อยเนื้อคั่ว", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu58.png", "ก้อยเนื้อสับคั่วสุกหอมสมุนไพร เลือกขมหรือไม่ขมได้"),
        ("ก้อยเนื้อดิบขม", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu59.png", "ก้อยเนื้อวัวสดคัดพิเศษ ปรุงรสขมอำพันอีสานแท้"),
        ("น้ำตกคอหมูย่าง", "ลาบ & ก้อย & น้ำตก", 85, 35, "static/img/menu/menu57.png", "คอหมูย่างฉ่ำๆ คลุกเครื่องน้ำตกอีสานแท้ สุดยอดเมนูขายดี"),
        ("น้ำตกหมู", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu55.png", "เนื้อหมูย่างนุ่มฉ่ำ คลุกน้ำยำน้ำตกรสแซ่บกลมกล่อม"),
        ("น้ำตกเนื้อ", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu56.png", "เนื้อย่างติดมันหั่นชิ้น ปรุงน้ำตกรสแซ่บหอมข้าวคั่ว"),
        ("ตับหวาน", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu60.png", "ตับหมูชิ้นหนาลวกสุกกำลังดี เนื้อนุ่มหวานฉ่ำคลุกเครื่องลาบ"),

        # --- 5. หมวด "ย่าง & ทอด" (16 เมนู) ---
        ("ไก่ย่างเขาสวนกวาง (ครึ่งตัว)", "ย่าง & ทอด", 110, 45, "static/img/menu/menu50.png", "ไก่หมักสมุนไพรสูตรเขาสวนกวาง ย่างหนังกรอบเนื้อนุ่ม"),
        ("ไก่ย่างเขาสวนกวาง (ตัว)", "ย่าง & ทอด", 210, 85, "static/img/menu/menu51.png", "ไก่ย่างเขาสวนกวางเต็มตัว เสิร์ฟพร้อมน้ำจิ้มแจ่วและน้ำจิ้มหวาน"),
        ("ปีกไก่ย่าง (ไม้ละ)", "ย่าง & ทอด", 25, 10, "static/img/menu/menu52.png", "ปีกไก่หมักเครื่องเทศเสียบไม้ย่างเตาถ่าน หอมกรุ่น"),
        ("คอหมูย่างนมสด", "ย่าง & ทอด", 89, 36, "static/img/menu/menu61.png", "คอหมูแท้หมักนมสด ย่างไฟอ่อนนุ่มละลายในปาก จิ้มแจ่วพริกป่น"),
        ("เนื้อย่างติดมัน", "ย่าง & ทอด", 99, 42, "static/img/menu/menu65.png", "เสือร้องไห้เนื้อติดมันย่างเตาถ่านหอมๆ จิ้มแจ่วขม/เปรี้ยว"),
        ("ไส้ย่าง", "ย่าง & ทอด", 79, 32, "static/img/menu/menu66.png", "ไส้อ่อนหมูต้มสมุนไพรแล้วย่างเตาถ่าน กรอบนอกนุ่มในไม่ขม"),
        ("ลิ้นหมูย่าง", "ย่าง & ทอด", 79, 32, "static/img/menu/menu67.png", "ลิ้นหมูย่างกรุบเด้ง หอมกลิ่นเตาถ่าน ทานคู่กระเทียมโทน"),
        ("ปลาดุกย่าง (ตัว)", "ย่าง & ทอด", 50, 20, "static/img/menu/menu68.png", "ปลาดุกหมักเครื่องเทศย่างสุกเหลืองหอม ทานคู่ส้มตำเข้ากัน"),
        ("ปลานิลเผาเกลือ", "ย่าง & ทอด", 160, 65, "static/img/menu/menu69.png", "ปลานิลสดตัวโตยัดไส้สมุนไพรพอกเกลือเผา เสิร์ฟพร้อมชุดผักและขนมจีน"),
        ("ไก่ทอดเกลือ", "ย่าง & ทอด", 79, 30, "static/img/menu/menu70.png", "เนื้อไก่ทอดเกลือกรอบนอกฉ่ำใน เค็มกำลังดี ทานเล่นเพลิน"),
        ("ปีกไก่ทอดน้ำปลา", "ย่าง & ทอด", 79, 30, "static/img/menu/menu71.png", "ปีกไก่กลางทอดน้ำปลาแท้ หนังกรอบหอมอร่อย"),
        ("เอ็นข้อไก่ทอด", "ย่าง & ทอด", 79, 30, "static/img/menu/menu72.png", "เอ็นข้อไก่ชุบแป้งบางๆ ทอดกรอบโรยงาขาวและใบมะกรูด"),
        ("หมูสามชั้นทอดน้ำปลา", "ย่าง & ทอด", 85, 34, "static/img/menu/menu62.png", "สามชั้นคัดสวยทอดน้ำปลากรอบฉ่ำ เสิร์ฟพร้อมน้ำจิ้มแจ่วซีฟู้ด"),
        ("หมูแดดเดียวทอด", "ย่าง & ทอด", 79, 30, "static/img/menu/menu63.png", "หมูแดดเดียวสูตรทางร้าน ทอดร้อนๆ โรยงาหอม"),
        ("เนื้อแดดเดียวทอด", "ย่าง & ทอด", 89, 38, "static/img/menu/menu64.png", "เนื้อวัวแดดเดียวทอดไฟกลาง นุ่มไม่เหนียว หอมสมุนไพร"),
        ("แคบหมูกรอบ", "ย่าง & ทอด", 25, 10, "static/img/menu/menu73.png", "แคบหมูติดมันทอดใหม่ทุกวัน กรอบฟู ทานคู่ส้มตำ"),

        # --- 6. หมวด "ต้มแซ่บ & แกงอีสาน" (15 เมนู) ---
        ("ต้มแซ่บกระดูกอ่อน", "ต้มแซ่บ & แกงอีสาน", 89, 35, "static/img/menu/menu77.png", "กระดูกอ่อนหมูตุ๋นเปื่อยนุ่ม น้ำซุปต้มแซ่บพริกคั่วหอมข้าวคั่ว"),
        ("ต้มแซ่บเนื้อลาย", "ต้มแซ่บ & แกงอีสาน", 99, 42, "static/img/menu/menu78.png", "เนื้อน่องลายตุ๋นนุ่มเด้ง ซุปสมุนไพรเปรี้ยวเผ็ดจี๊ดจ๊าด"),
        ("ต้มแซ่บเครื่องในเนื้อ", "ต้มแซ่บ & แกงอีสาน", 99, 42, "static/img/menu/menu79.png", "เครื่องในวัวต้มสะอาดไร้กลิ่นคาว ปรุงรสแซ่บถึงเครื่อง"),
        ("ต้มโคล้งปลากรอบ", "ต้มแซ่บ & แกงอีสาน", 89, 35, "static/img/menu/menu80.png", "ปลาเนื้ออ่อนย่างกรอบ ต้มโคล้งน้ำมะขามเปียกหอมพริกแห้งคั่ว"),
        ("ต้มยำกุ้งน้ำข้น", "ต้มแซ่บ & แกงอีสาน", 120, 50, "static/img/menu/menu81.png", "กุ้งสดตัวโต ต้มยำน้ำข้นมันกุ้งแท้ รสเข้มข้นกลมกล่อม"),
        ("ต้มยำรวมมิตรทะเล", "ต้มแซ่บ & แกงอีสาน", 130, 55, "static/img/menu/menu82.png", "กุ้ง หมึก หอย ปลา ต้มยำสมุนไพรสด ซดร้อนคล่องคอ"),
        ("แกงอ่อมหมู", "ต้มแซ่บ & แกงอีสาน", 80, 30, "static/img/menu/menu83.png", "แกงอ่อมหมูใส่ผักชีลาวและผักพื้นบ้าน หอมน้ำปลาร้าและข้าวคั่ว"),
        ("แกงอ่อมไก่บ้าน", "ต้มแซ่บ & แกงอีสาน", 80, 32, "static/img/menu/menu84.png", "ไก่บ้านเนื้อแน่นคั่วพริกแกงอ่อม ใส่ฟักทองและผักชีลาว"),
        ("แกงอ่อมเนื้อ", "ต้มแซ่บ & แกงอีสาน", 90, 38, "static/img/menu/menu74.png", "เนื้อวัวหั่นชิ้นแกงอ่อมสมุนไพรอีสานแท้ เข้มข้นถึงใจ"),
        ("แกงเห็ดรวมอีสาน", "ต้มแซ่บ & แกงอีสาน", 75, 28, "static/img/menu/menu75.png", "เห็ด 3 อย่างต้มน้ำใบย่านางคั้นสด ใส่บวบ ฟักทอง ชะอม และใบแมงลัก"),
        ("แกงหน่อไม้ใบย่านาง", "ต้มแซ่บ & แกงอีสาน", 75, 28, "static/img/menu/menu76.png", "หน่อไม้สดต้มน้ำใบย่านาง ใส่ข้าวเบือเหนียวข้น หอมชะอม"),
        ("แกงผักหวานไข่มดแดง", "ต้มแซ่บ & แกงอีสาน", 120, 55, "static/img/menu/menu85.png", "เมนูหากินยาก ผักหวานป่าอ่อนๆ แกงใส่ไข่มดแดงมันตึ๊บ"),
        ("ต้มซุปเปอร์ขาไก่", "ต้มแซ่บ & แกงอีสาน", 80, 30, "static/img/menu/menu89.png", "ขาไก่ตุ๋นจนเปื่อยร่อน ซุปพริกขี้หนูสวนเปรี้ยวเผ็ดสะใจ"),
        ("ต้มขมเนื้อเปื่อย", "ต้มแซ่บ & แกงอีสาน", 90, 38, "static/img/menu/menu90.png", "เนื้อเปื่อยและเครื่องในต้มขมสูตรอีสานดั้งเดิม หอมใบมะกรูด"),
        ("ต้มจืดเต้าหู้หมูสับ", "ต้มแซ่บ & แกงอีสาน", 65, 24, "static/img/menu/menu91.png", "ซุปใสกลมกล่อม เต้าหู้ไข่ หมูสับปั้นก้อน และผักกาดขาว ช่วยแก้เผ็ด"),

        # --- 7. หมวด "อาหารจานเดียว" (14 เมนู) ---
        ("ผัดกะเพราหมูสับราดข้าว", "อาหารจานเดียว", 55, 20, "static/img/menu/menu92.png", "กะเพราหมูสับผัดพริกแห้งไร้ถั่วฝักยาว หอมกลิ่นกระทะ"),
        ("ผัดกะเพราหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu93.png", "หมูกรอบชิ้นโตผัดกะเพราพริกสด รสจัดจ้านถึงเครื่อง"),
        ("ผัดกะเพราเนื้อสับราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu94.png", "เนื้อโคขุนสับผัดกะเพราใบกะเพราแดงหอมฉุน"),
        ("ผัดกะเพราทะเลรวมราดข้าว", "อาหารจานเดียว", 75, 32, "static/img/menu/menu95.png", "กุ้งและปลาหมึกสดผัดกะเพรารสเผ็ดร้อน เสิร์ฟคู่ข้าวหอมมะลิ"),
        ("ข้าวผัดไข่", "อาหารจานเดียว", 45, 16, "static/img/menu/menu96.png", "ข้าวผัดไข่ร่วนหอมกลิ่นกระทะ เด็กทานได้ผู้ใหญ่ทานดี"),
        ("ข้าวผัดหมู", "อาหารจานเดียว", 55, 20, "static/img/menu/menu86.png", "ข้าวผัดหมูหมักนุ่ม ผัดไฟแรงเม็ดข้าวร่วนสวย"),
        ("ข้าวผัดกุ้ง", "อาหารจานเดียว", 70, 28, "static/img/menu/menu87.png", "ข้าวผัดกุ้งสดตัวโต หอมมันกุ้ง บีบมะนาวพริกน้ำปลาเข้ากัน"),
        ("ข้าวผัดโบราณ", "อาหารจานเดียว", 60, 22, "static/img/menu/menu88.png", "ข้าวผัดซอสดำใส่หมูและคะน้า สีเข้มข้นหอมอร่อยสไตล์โบราณ"),
        ("ข้าวผัดน้ำพริกเผาหมูกรอบ", "อาหารจานเดียว", 70, 28, "static/img/menu/menu97.png", "ข้าวผัดคลุกน้ำพริกเผาหอมมัน ท็อปด้วยหมูกรอบหนังฟู"),
        ("ผัดคะน้าหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu101.png", "ยอดคะน้าอ่อนกรอบผัดไฟแดงกับหมูกรอบชิ้นหนา"),
        ("ผัดพริกแกงหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu102.png", "พริกแกงเผ็ดโขลกเองผัดหมูกรอบ ใส่ใบมะกรูดซอยหอมๆ"),
        ("ข้าวไข่เจียวหมูสับ", "อาหารจานเดียว", 45, 16, "static/img/menu/menu103.png", "ไข่เจียวหมูสับทอดฟูกรอบ ราดข้าวสวยร้อนๆ พร้อมซอสพริก"),
        ("ข้าวคอหมูย่างน้ำจิ้มแจ่ว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu104.png", "ข้าวสวยร้อนๆ โปะคอหมูย่างเตาถ่านฉ่ำๆ และน้ำจิ้มแจ่ว"),
        ("ข้าวหน้าเนื้อย่างแจ่ว", "อาหารจานเดียว", 75, 32, "static/img/menu/menu105.png", "ข้าวหน้าเนื้อย่างติดมันนุ่มๆ เสิร์ฟคู่แจ่วพริกป่นและแตงกวา"),

        # --- 8. หมวด "ของหวาน" (10 เมนู) ---
        ("ลอดช่องสิงคโปร์", "ของหวาน", 35, 12, "static/img/menu/menu106.png", "เส้นลอดช่องเหนียวหนึบ น้ำกะทิสดหอมขนุนฉีก เย็นชื่นใจ"),
        ("ลอดช่องไทยน้ำกะทิแตงไทย", "ของหวาน", 35, 12, "static/img/menu/menu107.png", "ลอดช่องใบเตยแท้ น้ำกะทิน้ำตาลโตนดเคี่ยวหอมและแตงไทย"),
        ("ทับทิมกรอบน้ำกะทิ", "ของหวาน", 40, 15, "static/img/menu/menu108.png", "แห้วกรอบหุ้มแป้งสีทับทิม ราดหัวกะทิสดอบควันเทียน"),
        ("สลิ่มน้ำกะทิอบควันเทียน", "ของหวาน", 35, 12, "static/img/menu/menu98.png", "เส้นสลิ่ม 3 สีเหนียวนุ่ม น้ำกะทิสดหอมกลิ่นควันเทียน"),
        ("รวมมิตรน้ำกะทิสด", "ของหวาน", 35, 12, "static/img/menu/menu99.png", "รวมมิตรเครื่องแน่น ลอดช่อง ทับทิมกรอบ ขนุน มันเชื่อม"),
        ("บัวลอยไข่หวาน", "ของหวาน", 40, 15, "static/img/menu/menu100.png", "บัวลอยแป้งนุ่มสีธรรมชาติในน้ำกะทิอุ่นๆ พร้อมไข่หวานสุกพอดี"),
        ("กล้วยบวชชี", "ของหวาน", 30, 10, "static/img/menu/menu109.png", "กล้วยน้ำว้าห่ามต้มกะทิสด หอมหวานมันเค็มกลมกล่อม"),
        ("เฉาก๊วยชากังราวนมสด", "ของหวาน", 35, 12, "static/img/menu/menu113.png", "เฉาก๊วยแท้เนื้อหนึบ ใส่นมสดและโรยน้ำตาลทรายแดง"),
        ("ไอศกรีมกะทิสดโบราณ", "ของหวาน", 35, 12, "static/img/menu/menu114.png", "ไอศกรีมกะทิสดแท้ โรยถั่วลิสงคั่ว ลูกชิด และข้าวเหนียวมูน"),
        ("ข้าวเหนียวมะม่วงอกร่อง", "ของหวาน", 69, 28, "static/img/menu/menu115.png", "มะม่วงสุกหวานฉ่ำ เสิร์ฟคู่ข้าวเหนียวมูนกะทิสดและถั่วทอง"),

        # --- 9. หมวด "เครื่องเคียง & ข้าว" (9 เมนู) ---
        ("ข้าวเหนียวนึ่ง", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu116.png", "ข้าวเหนียวเขี้ยวงูนึ่งใหม่ร้อนๆ นุ่มติดใจไม่แข็ง"),
        ("ข้าวสวยหอมมะลิ", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu117.png", "ข้าวหอมมะลิแท้ 100% หุงนุ่มหอมกรุ่น"),
        ("ขนมจีน", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu118.png", "เส้นขนมจีนแป้งหมักสดใหม่ นุ่มลื่น ทานคู่ส้มตำ"),
        ("หมูยอลวกจิ้ม", "เครื่องเคียง & ข้าว", 50, 20, "static/img/menu/menu119.png", "หมูยออุบลหั่นชิ้นลวกร้อนๆ จิ้มน้ำจิ้มซีฟู้ด"),
        ("ผักบุ้งลวก", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu120.png", "ผักบุ้งยอดอ่อนลวกกรอบสีเขียวสด ทานคู่ส้มตำ"),
        ("กะหล่ำปลีสด", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu110.png", "กะหล่ำปลีสดแช่เย็นกรอบหวาน ช่วยลดความเผ็ด"),
        ("แตงกวาสด", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu111.png", "แตงกวาสดหั่นชิ้นแช่เย็น กรอบฉ่ำน้ำ"),
        ("ไข่ดาว", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu112.png", "ไข่ไก่สดทอดดาวกรอบนอกไข่แดงเยิ้ม"),
        ("ไข่ต้ม", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu121.png", "ไข่ต้มยางมะตูมมันนัว ทานคู่ส้มตำหรือน้ำตก"),

        # --- 10. หมวด "เครื่องดื่ม" (10 เมนู) ---
        ("น้ำเปล่า", "เครื่องดื่ม", 15, 6, "static/img/menu/menu125.png", "น้ำดื่มบริสุทธิ์ขวดเย็นชื่นใจ"),
        ("น้ำแข็ง", "เครื่องดื่ม", 10, 3, "static/img/menu/menu126.png", "น้ำแข็งหลอดสะอาดใส่กระติก/แก้ว"),
        ("น้ำอัดลม", "เครื่องดื่ม", 25, 12, "static/img/menu/menu127.png", "โคล่า/น้ำอัดลมกระป๋องเย็นซ่าสดชื่น"),
        ("น้ำแดง", "เครื่องดื่ม", 25, 10, "static/img/menu/menu128.png", "น้ำหวานกลิ่นสละ หอมหวานเย็นชื่นใจ"),
        ("น้ำเขียว", "เครื่องดื่ม", 25, 10, "static/img/menu/menu129.png", "น้ำหวานกลิ่นครีมโซดา สดชื่นดับกระหาย"),
        ("ชามะนาว", "เครื่องดื่ม", 35, 12, "static/img/menu/menu130.png", "ชาดำแท้ผสมน้ำมะนาวคั้นสด เปรี้ยวหวานลงตัว"),
        ("ชาเย็น", "เครื่องดื่ม", 35, 12, "static/img/menu/menu131.png", "ชาไทยแท้สูตรโบราณ หอมมันนมสดแท้ ดับเผ็ด"),
        ("น้ำเก๊กฮวย", "เครื่องดื่ม", 30, 10, "static/img/menu/menu132.png", "เก๊กฮวยต้มสมุนไพรแท้ หวานน้อยหอมสดชื่น"),
        ("น้ำกระเจี๊ยบ", "เครื่องดื่ม", 30, 10, "static/img/menu/menu122.png", "กระเจี๊ยบแดงต้มสด เปรี้ยวอมหวานชุ่มคอ"),
        ("น้ำลำไย", "เครื่องดื่ม", 35, 12, "static/img/menu/menu123.png", "น้ำลำไยเนื้อแน่น หวานหอมกลมกล่อม")
    ]
    
    # ตรวจสอบว่าตารางว่างเปล่า หรือยังมีเมนูค้างจากระบบเก่าที่ใช้รูปลิงก์ Unsplash หรือไม่
    c.execute("SELECT COUNT(*) FROM menu_items WHERE image LIKE '%unsplash%'")
    has_old_unsplash = (c.fetchone()[0] > 0)
    
    c.execute("SELECT COUNT(*) FROM menu_items")
    is_empty = (c.fetchone()[0] == 0)

    if is_empty or has_old_unsplash:
        # อัปเดตชุดเมนูหลัก 131 รายการให้ใช้ไฟล์ภาพใน static/img/menu/ ทั้งหมด
        c.execute('DELETE FROM menu_items')
        c.executemany('INSERT OR REPLACE INTO menu_items (name, category, price, cost, image, description) VALUES (?, ?, ?, ?, ?, ?)', fahsai_menu)

    #  ข้อมูลสมาชิกจำลองเริ่มต้น 10 คน (ถ้ายังไม่มีสมาชิกในระบบ)
    c.execute("SELECT COUNT(*) FROM members")
    if c.fetchone()[0] == 0:
        sample_members = [
            ("สมชาย", "สายกิน", "0812345678", 85, "2026-09-15 11:30:00"),
            ("กานดา", "สุขสมบูรณ์", "0898765432", 64, "2026-09-18 12:45:00"),
            ("ปิยะพงษ์", "รักนัว", "0923456789", 52, "2026-09-20 18:20:00"),
            ("อรทัย", "แซ่บหลาย", "0861122334", 41, "2026-09-25 13:10:00"),
            ("นฤมล", "ทองดี", "0956677889", 35, "2026-10-01 17:50:00"),
            ("ธนกร", "มีทรัพย์", "0845566778", 28, "2026-10-02 12:15:00"),
            ("ชญาดา", "พัฒนาเลิศ", "0937734851", 20, "2026-10-04 11:00:00"),
            ("วรวิทย์", "เจริญผล", "0879988776", 15, "2026-10-05 19:30:00"),
            ("สุภาวรรณ", "ใจดี", "0912233445", 10, "2026-10-07 14:00:00"),
            ("กิตติศักดิ์", "ยอดเยี่ยม", "0834455667", 6, "2026-10-08 16:20:00")
        ]
        c.executemany(
            "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, ?, ?)",
            sample_members
        )

    # 6. ตารางผู้ดูแลระบบ / ผู้ใช้งานหลังร้าน (admin_users)
    # เก็บรหัสผ่านแบบเข้ารหัส Secure Hash (SHA-256 + Salt)
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,     -- ชื่อผู้ใช้งานสำหรับล็อกอิน
            password_hash TEXT NOT NULL,       -- รหัสผ่านที่เข้ารหัสแฮชแล้ว
            salt TEXT NOT NULL,                -- ค่า Salt ป้องกัน Rainbow Table
            full_name TEXT,                    -- ชื่อ-นามสกุลเจ้าหน้าที่
            role TEXT DEFAULT 'admin',         -- บทบาท: admin, manager, cashier
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # สร้างบัญชีผู้ดูแลระบบเริ่มต้น (Default Admin) หากยังไม่มี
    def_salt = "fahsai_salt_secure_2026"
    def_hash = hashlib.sha256((def_salt + "adminfahsaitumnua@12").encode('utf-8')).hexdigest()
    old_hash = hashlib.sha256((def_salt + "admin1234").encode('utf-8')).hexdigest()
        
    c.execute("SELECT id, password_hash FROM admin_users WHERE LOWER(username) = 'admin'")
    existing_admin = c.fetchone()
    if not existing_admin:
        c.execute("""
            INSERT INTO admin_users(username, password_hash, salt, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", def_hash, def_salt, "ผู้ดูแลระบบ (Admin)", "admin"))
    elif existing_admin[1] == old_hash:
        # หากในฐานข้อมูลยังคงเป็นรหัสผ่านเดิมสมัยแรก (admin1234) ให้อัปเกรดเป็น adminfahsaitumnua@12 อัตโนมัติ
        c.execute("""
            UPDATE admin_users
            SET password_hash = ?, salt = ?
            WHERE id = ?
        """, (def_hash, def_salt, existing_admin[0]))

    #  สร้างโต๊ะอาหารเริ่มต้น 10 โต๊ะ (หากยังไม่มีโต๊ะในระบบ)
    c.execute("SELECT COUNT(*) FROM tables")
    if c.fetchone()[0] == 0:
        default_tables = [(i, f"โต๊ะที่ {i}", "available") for i in range(1, 11)]
        c.executemany("INSERT INTO tables (table_number, name, status) VALUES (?, ?, ?)", default_tables)

    conn.commit()
    conn.close()


# เรียกใช้งานเพื่อเตรียมฐานข้อมูลพร้อมใช้งานทันทีที่เริ่มโปรแกรม
init_db()

# ==============================================================================
#  ตรวจสอบโหมดการแสดงผล (Admin หรือ ลูกค้า) ผ่าน URL Parameter
# ==============================================================================
# ตัวอย่าง:
# - หน้าจัดการหลังร้าน: https://domain/?mode=admin
# - หน้าร้าน/ลูกค้าสั่งอาหาร: https://domain/?table=1
params = st.query_params
raw_mode = str(params.get("mode", ""))
is_admin_mode = ("admin" in raw_mode.lower())

# ปรับคลีน st.query_params ในระบบให้สะอาดสวยงาม ไม่มีตัวแปรซ้ำ
if is_admin_mode and params.get("mode") != "admin":
    st.query_params.clear()
    st.query_params["mode"] = "admin"

# ที่อยู่ไฟล์รูปภาพโลโก้ของร้านฟ้าใสตำนัว
logo_path = "static/img/logo.png"


# ==============================================================================
#  ฟังก์ชันช่วยเหลือ (Utility / Helper Functions)
# ==============================================================================

def get_base64_image(image_path):
    """
    แปลงไฟล์รูปภาพ (เช่น PNG/JPG) เป็นข้อความ Base64
    ประโยชน์: ช่วยให้แทรกภาพลงในแท็ก HTML <img> ได้โดยตรง 
    ทำให้หน้าเว็บโหลดภาพขึ้นมาทันที ไม่ติดปัญหา Path หรือ CORS
    """
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

def hash_password(password, salt=None):
    """เข้ารหัสผ่านด้วย SHA-256 ผสม Salt ป้องกันการขโมยรหัสผ่าน"""
    if not salt:
        import secrets
        salt = secrets.token_hex(8)
    pw_hash = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return pw_hash, salt

def verify_password(input_password, stored_hash, salt):
    """ตรวจสอบรหัสผ่านที่ป้อนเข้ามา เทียบกับค่า Hash ที่บันทึกไว้ในฐานข้อมูล"""
    calc_hash = hashlib.sha256((salt + input_password).encode('utf-8')).hexdigest()
    return hmac.compare_digest(calc_hash, stored_hash)

def get_current_base_url(default="https://tumnua1-cae26py9kvbzmz4juo3sey.streamlit.app"):
    """
    ตรวจจับ URL ของเว็บไซต์อัตโนมัติจาก Request Headers เพื่อใช้สร้าง QR Code
    ข้อดี: ไม่ว่าจะนำโค้ดไปเปิดใช้งานกับร้านใหม่ บัญชีใหม่ หรือโดเมนใดๆ 
    ระบบจะตรวจจับชื่อโดเมนใหม่อัตโนมัติทันที ไม่ต้องแก้โค้ดด้วยมือ
    """
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

@st.cache_data
def get_bell_sound_b64():
    """
    สังเคราะห์คลื่นเสียงกระดิ่งเตือน (Chime) ความถี่คู่ 784Hz และ 1046.5Hz ขึ้นมาใน RAM
    แล้วบันทึกเป็น WAV ในหน่วยความจำโดยตรง
    ประโยชน์:
    - ไม่ต้องโหลดไฟล์เสียง MP3/WAV จากภายนอก
    - ใช้ @st.cache_data เพื่อสร้างคลื่นเสียงเพียงครั้งเดียว แล้วเก็บแคชไว้ใช้งานซ้ำ
    """
    sample_rate = 22050
    duration = 0.85
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            decay = math.exp(-4.2 * t)
            v1 = math.sin(2 * math.pi * 784.0 * t)
            v2 = math.sin(2 * math.pi * 1046.5 * t) if t > 0.08 else 0
            sample = int(32767 * 0.45 * (v1 * 0.55 + v2 * 0.45) * decay)
            wav_file.writeframes(struct.pack('<h', sample))
    return base64.b64encode(buf.getvalue()).decode()

def play_order_sound():
    """
    สั่งเล่นเสียงกระดิ่งเตือนในเบราว์เซอร์อัตโนมัติ (Autoplay)
    เมื่อมีออเดอร์ใหม่ที่ลูกค้าเพิ่งสั่งเข้ามาในห้องครัว
    """
    sound_b64 = get_bell_sound_b64()
    audio_html = f'''
    <audio autoplay style="display:none;">
        <source src="data:audio/wav;base64,{sound_b64}" type="audio/wav">
    </audio>
    <script>
    try {{
        const snd = new Audio("data:audio/wav;base64,{sound_b64}");
        snd.play().catch(e => {{ console.log("Audio waiting for gesture:", e); }});
    }} catch(e) {{}}
    </script>
    '''
    st.markdown(audio_html, unsafe_allow_html=True)


# ==============================================================================
#  ฟังก์ชันแสดง Footer เครดิตผู้พัฒนาระบบ
# ==============================================================================
def render_app_footer():
    """แสดง Footer เครดิตผู้พัฒนาระบบด้านล่างสุดของหน้าจอ จัดกึ่งกลาง"""
    st.write("---")
    footer_html = """
    <div style="text-align: center; margin-top: 25px; margin-bottom: 25px; padding: 15px 10px; color: #4b5563; line-height: 1.8;">
        <div style="font-weight: 700; color: #c2410c; font-size: 1.05rem;">ระบบสั่งอาหารโต๊ะผ่าน QR Code</div>
        <div style="color: #374151; font-weight: 500;">พัฒนา โดย นางสาวชญาดา สิงหวัฒน์</div>
        <div style="color: #6b7280; font-size: 0.95rem;">อีเมล์ : chayada.sing@kkumail.com &nbsp;&nbsp;&nbsp;&nbsp; โทรศัพท์ : 093-773-4851</div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)


# ==============================================================================
#  ฟังก์ชันสร้างใบเสร็จรับเงินอย่างย่อ (HTML / Print / PDF)
# ==============================================================================
def get_payment_qr_base64():
    """ดึงรูปภาพ QR ธนาคาร/พร้อมเพย์ (payment.jpg) จากโฟลเดอร์ static มาแปลงเป็น Base64 สำหรับแสดงในใบเสร็จ HTML"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "static", "img", "payment.jpg"),
        os.path.join(os.path.dirname(__file__), "static", "payment.jpg"),
        os.path.join("static", "img", "payment.jpg"),
        os.path.join("static", "payment.jpg"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return ""


def generate_receipt_html(order_id, table_id, items, total_price, order_time, subtotal=None, discount=0, points_used=0, points_earned=0, member_phone=None, member_name=None, remaining_points=None):
    total_qty = sum(item[1] for item in items)
    if subtotal is None or subtotal <= 0:
        subtotal = total_price + discount
    vat_included = round(total_price * 7 / 107, 2)
    before_vat = round(total_price - vat_included, 2)
    
    # แปลงภาพ QR ธนาคาร (payment.jpg) เป็น Base64 เพื่อฝังลงในใบเสร็จ
    qr_b64 = get_payment_qr_base64()
    if qr_b64:
        qr_payment_html = f"""
        <div class="dashed"></div>
        <div class="text-center" style="margin: 8px 0;">
            <div style="font-size: 13px; font-weight: bold; color: #1e3a8a; margin-bottom: 2px;">
                 สแกน QR เพื่อชำระเงิน
            </div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">
                (PromptPay / สแกนผ่านแอปธนาคาร)
            </div>
            <div style="display: flex; justify-content: center; align-items: center; margin: 4px 0;">
                <img src="data:image/jpeg;base64,{qr_b64}" 
                     style="width: 175px; max-width: 90%; height: auto; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.06);" 
                     alt="QR ธนาคารชำระเงิน" />
            </div>
            <div style="font-size: 12px; color: #1e293b; margin-top: 5px;">
                ยอดที่ต้องชำระ: <strong style="color: #c2410c; font-size: 14px;">฿{int(total_price):,}</strong>
            </div>
        </div>
        """
    else:
        qr_payment_html = ""
    
    items_rows_html = ""
    for idx, item in enumerate(items, 1):
        iname = item[0]
        iqty = item[1]
        iprice = item[2]
        line_total = int(iqty * iprice)
        items_rows_html += f"""
        <tr>
            <td style="padding: 4px 0; text-align: left; font-size: 13px;">{idx}. {iname}</td>
            <td style="padding: 4px 0; text-align: center; font-size: 13px;">{iqty}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px;">{int(iprice)}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px; font-weight: bold;">{line_total:,}</td>
        </tr>
        """
        
    # ข้อมูลสมาชิกสะสมแต้มในใบเสร็จ
    member_info_html = ""
    if member_phone:
        pts_used_txt = f"<div>• ใช้คะแนนแลกส่วนลด: <strong>{points_used}</strong> แต้ม (-฿{int(discount):,})</div>" if points_used > 0 else ""
        rem_pts_txt = f"<div>• คะแนนสะสมคงเหลือ: <strong style='color: #ea580c;'>{remaining_points}</strong> แต้ม</div>" if remaining_points is not None else ""
        member_info_html = f"""
        <div class="dashed"></div>
        <div style="font-size: 11.5px; background: #fff7ed; padding: 6px 8px; border-radius: 5px; border: 1px dashed #fdba74; margin-top: 4px;">
            <div style="font-weight: bold; color: #c2410c;"> ข้อมูลสมาชิกสะสมแต้ม</div>
            <div>ลูกค้า: <strong>{member_name or 'สมาชิก'}</strong> ({member_phone})</div>
            {pts_used_txt}
            <div>• ได้รับคะแนนบิลนี้: <strong style="color: #16a34a;">+{points_earned}</strong> แต้ม (ทุก 100บ. = 1 แต้ม)</div>
            {rem_pts_txt}
        </div>
        """

    # แถวส่วนลดในตาราง
    discount_row_html = ""
    if discount > 0:
        discount_row_html = f"""
        <tr style="color: #16a34a; font-weight: bold;">
            <td>ส่วนลดจากคะแนน ({points_used} แต้ม):</td>
            <td class="text-right">-฿{int(discount):,}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
    <meta charset="UTF-8">
    <title>ใบเสร็จรับเงินอย่างย่อ #{order_id}</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 3mm;
        }}
        @media print {{
            body {{
                margin: 0 !important;
                padding: 4px !important;
                width: 76mm !important;
                box-shadow: none !important;
                border: none !important;
            }}
            .no-print {{
                display: none !important;
            }}
            img {{
                max-width: 48mm !important;
            }}
        }}
        body {{
            font-family: 'Sarabun', 'Segoe UI', Tahoma, monospace, sans-serif;
            color: #111;
            background: #fff;
            width: 290px;
            margin: 4px auto;
            padding: 14px 10px;
            font-size: 13px;
            line-height: 1.38;
            border: 1px dashed #bbb;
            border-radius: 6px;
            box-sizing: border-box;
        }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .bold {{ font-weight: bold; }}
        .dashed {{
            border-top: 1px dashed #777;
            margin: 8px 0;
        }}
        .double-line {{
            border-top: 2px solid #222;
            margin: 8px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            border-bottom: 1px dashed #777;
            padding: 4px 0;
            font-size: 12px;
        }}
        .btn-print {{
            background: #ea580c;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            transition: background 0.2s;
        }}
        .btn-print:hover {{
            background: #c2410c;
        }}
    </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 12px;">
            <button class="btn-print" onclick="window.print()"> สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF</button>
        </div>
        
        <div class="text-center">
            <div style="font-size: 18px; font-weight: bold; color: #c2410c;"> ฟ้าใสตำนัว</div>
            <div style="font-size: 11px; color: #444;">(FAHSAI TUM NUA)</div>
            <div style="font-size: 12px; margin-top: 3px; font-weight: bold;">ใบเสร็จรับเงิน / ใบกำกับภาษีอย่างย่อ</div>
            <div style="font-size: 11px; color: #666;">โทร. 093-773-4851 • ยินดีให้บริการ</div>
        </div>
        
        <div class="dashed"></div>
        
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span><strong>โต๊ะที่:</strong> โต๊ะที่ {table_id}</span>
            <span><strong>บิลเลขที่:</strong> #{order_id}</span>
        </div>
        <div style="font-size: 12px; color: #444;">
            <strong>วันที่-เวลา:</strong> {order_time}
        </div>
        
        <div class="dashed"></div>
        
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">รายการอาหาร</th>
                    <th style="text-align: center; width: 32px;">จน.</th>
                    <th style="text-align: right; width: 45px;">ราคา</th>
                    <th style="text-align: right; width: 50px;">รวม</th>
                </tr>
            </thead>
            <tbody>
                {items_rows_html}
            </tbody>
        </table>
        
        <div class="dashed"></div>
        
        <table style="font-size: 12.5px;">
            <tr>
                <td>จำนวนรวม:</td>
                <td class="text-right bold">{total_qty} จาน</td>
            </tr>
            <tr>
                <td>ยอดรวมสินค้า:</td>
                <td class="text-right bold">฿{int(subtotal):,}</td>
            </tr>
            {discount_row_html}
            <tr>
                <td>มูลค่าก่อนภาษี:</td>
                <td class="text-right">฿{before_vat:,.2f}</td>
            </tr>
            <tr>
                <td>ภาษีมูลค่าเพิ่ม (VAT 7% รวมแล้ว):</td>
                <td class="text-right">฿{vat_included:,.2f}</td>
            </tr>
            <tr style="font-size: 15px; font-weight: bold; color: #c2410c;">
                <td style="padding-top: 5px;">ยอดจ่ายจริง (TOTAL):</td>
                <td class="text-right" style="padding-top: 5px;">฿{int(total_price):,}</td>
            </tr>
        </table>
        
        {member_info_html}
        
        {qr_payment_html}
        
        <div class="double-line"></div>
        
        <div class="text-center" style="font-size: 11px; color: #444;">
            <div>ชำระโดย: เงินสด / โอนเงินผ่าน QR ธนาคาร</div>
            <div style="margin-top: 4px; font-weight: bold; color: #111;">ขอบพระคุณที่มาอุดหนุนค่ะ </div>
            <div>โอกาสหน้าเชิญใหม่นะคะ แซ่บนัวทุกจาน!</div>
        </div>
    </body>
    </html>
    """
    return html

def render_receipt_box(oid, conn):
    c = conn.cursor()
    c.execute("""
        SELECT table_id, total_price, created_at, status,
               COALESCE(subtotal, total_price), COALESCE(discount, 0),
               COALESCE(points_used, 0), COALESCE(points_earned, 0),
               member_phone
        FROM orders WHERE id = ?
    """, (oid,))
    row = c.fetchone()
    if not row:
        st.session_state['active_receipt_oid'] = None
        return
    t_id, total, otime, st_code, subtotal, discount, pts_used, pts_earned, m_phone = row
    c.execute("SELECT item_name, quantity, price FROM order_items WHERE order_id = ?", (oid,))
    items = c.fetchall()
    
    m_name = None
    rem_pts = None
    if m_phone:
        c.execute("SELECT first_name, last_name, points FROM members WHERE phone = ?", (m_phone,))
        m_row = c.fetchone()
        if m_row:
            m_name = f"{m_row[0]} {m_row[1]}"
            rem_pts = m_row[2]

    receipt_html = generate_receipt_html(
        oid, t_id, items, total, otime,
        subtotal=subtotal, discount=discount,
        points_used=pts_used, points_earned=pts_earned,
        member_phone=m_phone, member_name=m_name,
        remaining_points=rem_pts
    )
    
    with st.container(border=True):
        st.markdown(f"###  ใบเสร็จรับเงินอย่างย่อ — โต๊ะที่ {t_id} (บิล #{oid})")
        st.caption("สามารถกดปุ่ม ** สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF** ด้านล่างนี้ หรือดาวน์โหลดไฟล์ได้ทันทีค่ะ")
        
        components.html(receipt_html, height=750, scrolling=True)
        
        # ส่วนแสดง/ผูกข้อมูลสมาชิกที่เคาน์เตอร์คิดเงิน
        if st_code != 'paid':
            if m_phone:
                st.info(f" สมาชิก: **{m_name}** ({m_phone}) | ใช้แลกส่วนลด: **{pts_used}** แต้ม (-฿{int(discount):,}) | ได้รับแต้มบิลนี้: **+{pts_earned}** แต้ม")
            else:
                with st.expander(" เพิ่มสมาชิกสะสมแต้มสำหรับบิลนี้ (ที่เคาน์เตอร์)", expanded=False):
                    c_ph_in, c_ph_btn = st.columns([3, 1.2])
                    with c_ph_in:
                        attach_phone = st.text_input("เบอร์โทรศัพท์ลูกค้า:", key=f"attach_ph_input_{oid}", placeholder="เช่น 0937734851")
                    with c_ph_btn:
                        st.write("")
                        attach_btn = st.button(" บันทึกเบอร์", key=f"btn_attach_ph_{oid}", use_container_width=True)
                    if attach_btn and attach_phone.strip():
                        cl_ph = attach_phone.strip().replace("-", "").replace(" ", "")
                        c.execute("SELECT id, first_name, last_name, points FROM members WHERE phone = ?", (cl_ph,))
                        m_f = c.fetchone()
                        if m_f:
                            pts_to_earn = int(total // 100)
                            c.execute("UPDATE orders SET member_phone = ?, points_earned = ? WHERE id = ?", (cl_ph, pts_to_earn, oid))
                            conn.commit()
                            st.success(f"ผูกสมาชิก คุณ {m_f[1]} {m_f[2]} (แต้มปัจจุบัน: {m_f[3]}) สำเร็จ!")
                            st.rerun()
                        else:
                            st.warning("ไม่พบเบอร์นี้ในระบบสมาชิกค่ะ สามารถสมัครสมาชิกใหม่ได้ที่แท็บ ' ประวัติลูกค้า' นะคะ")

        rc1, rc2, rc3 = st.columns([1.5, 1.5, 1])
        with rc1:
            st.download_button(
                label=" ดาวน์โหลดไฟล์ใบเสร็จ (.html)",
                data=receipt_html,
                file_name=f"receipt_table{t_id}_order{oid}.html",
                mime="text/html",
                use_container_width=True,
                key=f"dl_receipt_file_{oid}"
            )
        with rc2:
            if st_code != 'paid':
                if st.button(" ยืนยันรับเงิน (ปิดบิล)", key=f"pay_confirm_btn_{oid}", type="primary", use_container_width=True):
                    c.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (oid,))
                    # อัปเดตคะแนนสะสมของสมาชิก
                    if m_phone:
                        net_pts_change = pts_earned - pts_used
                        c.execute("UPDATE members SET points = MAX(0, points + ?) WHERE phone = ?", (net_pts_change, m_phone))
                    conn.commit()
                    st.session_state['active_receipt_oid'] = None
                    st.toast(f"ปิดบิลโต๊ะ {t_id} เรียบร้อยแล้วค่ะ!", icon="")
                    st.rerun()
            else:
                st.info(" บิลนี้ชำระเงินเรียบร้อยแล้ว")
        with rc3:
            if st.button(" ปิดหน้าต่างใบเสร็จ", key=f"close_receipt_btn_{oid}", use_container_width=True):
                st.session_state['active_receipt_oid'] = None
                st.rerun()

# ==============================================================================
#  จอครัว & เคาน์เตอร์คิดเงิน (Fragment ทำงานอัตโนมัติทุก 3 วินาที)
# ==============================================================================
@st.fragment(run_every=3)
def render_pos_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ตรวจจับออเดอร์ใหม่สถานะ pending ที่เพิ่งเข้ามา
    c.execute("SELECT MAX(id) FROM orders WHERE status = 'pending'")
    row_max = c.fetchone()
    cur_max = row_max[0] if (row_max and row_max[0]) else 0
    
    if 'last_seen_pending_id' not in st.session_state:
        st.session_state['last_seen_pending_id'] = cur_max
    elif cur_max > st.session_state['last_seen_pending_id']:
        st.session_state['last_seen_pending_id'] = cur_max
        play_order_sound()
        st.toast(f" มีออเดอร์ใหม่ #{cur_max} เข้ามาในครัวแล้วค่ะ!", icon="")
        st.warning(f" **มีออเดอร์ใหม่ #{cur_max} เพิ่งส่งเข้ามาในครัว!** กำลังรอให้เตรียมอาหาร")

    # แถบแสดงสถานะอัปเดตสดแบบเรียลไทม์
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown(f"** สถานะระบบ:** :green[**● เชื่อมต่อสด • อัปเดตออเดอร์อัตโนมัติทุก 3 วินาที**] <span style='color: #64748b; font-size: 0.85rem;'>(เวลาปัจจุบัน: {get_thai_now().strftime('%H:%M:%S')})</span>", unsafe_allow_html=True)
    with top_c2:
        if st.button(" ทดสอบเสียงกระดิ่ง", key="btn_test_sound", use_container_width=True):
            play_order_sound()
            st.toast("ทดสอบเสียงกระดิ่งเตือนออเดอร์แล้ว ", icon="")

    c.execute("SELECT COALESCE(SUM(total_price), 0), COUNT(*) FROM orders WHERE status IN ('paid', 'archived')")
    revenue, paid_cnt = c.fetchone()
    c.execute("SELECT COUNT(*), COUNT(DISTINCT table_id) FROM orders WHERE status NOT IN ('paid', 'archived')")
    active_cnt, active_tables = c.fetchone()
    
    # Responsive Metrics
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(" ยอดขายรวม", f"฿{int(revenue):,}")
    s2.metric(" กำลังปรุง/เสิร์ฟ", f"{active_cnt} บิล")
    s3.metric(" นั่งทาน", f"{active_tables} โต๊ะ")
    s4.metric(" เช็คบิลแล้ว", f"{paid_cnt} บิล")
    
    st.write("---")
    
    # หากมีการกดเช็คบิล/ดูใบเสร็จ ให้แสดงกล่องใบเสร็จอย่างย่อด้านบนสุด
    active_rec_id = st.session_state.get('active_receipt_oid')
    if active_rec_id:
        render_receipt_box(active_rec_id, conn)
        st.write("---")

    c.execute('''
        SELECT id, table_id, status, total_price, created_at 
        FROM orders 
        WHERE status NOT IN ('paid', 'archived')
        ORDER BY 
            CASE status 
                WHEN 'pending' THEN 1 
                WHEN 'accepted' THEN 2 
                WHEN 'cooked' THEN 3 
                WHEN 'served' THEN 4 
            END, id ASC
    ''')
    orders_to_manage = c.fetchall()
    
    if not orders_to_manage:
        st.success(" ไม่มีออเดอร์ค้างในครัว น้องฟ้าใสพร้อมรับออเดอร์ใหม่เสมอค่ะ ")
    else:
        grid_cols = st.columns(3)
        for idx, (oid, t_id, st_code, total, otime) in enumerate(orders_to_manage):
            with grid_cols[idx % 3]:
                with st.container(border=True):
                    # หัวการ์ดโต๊ะในจอครัวแบบมีสีสันสดใสไล่เฉด (Vibrant KDS Table Header)
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); padding: 8px 14px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 3px 10px rgba(234, 88, 12, 0.28); display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #ffffff; font-weight: 800; font-size: 1.25rem; letter-spacing: 0.5px;"> โต๊ะที่ {t_id}</span>
                        <span style="background: #ffffff; color: #ea580c; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 0.85rem;">บิล #{oid}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f" เวลาสั่งอาหาร: {otime}")
                    
                    c.execute("""
                        SELECT oi.id, oi.item_name, oi.quantity, oi.note, oi.price, COALESCE(oi.status, 'pending'), mi.image
                        FROM order_items oi
                        LEFT JOIN menu_items mi ON oi.item_name = mi.name
                        WHERE oi.order_id = ?
                    """, (oid,))
                    items_in_order = c.fetchall()
                    
                    total_items = len(items_in_order)
                    served_items = sum(1 for it in items_in_order if it[5] == 'served')
                    cooked_items = sum(1 for it in items_in_order if it[5] == 'cooked')
                    all_items_served = (total_items > 0) and (served_items == total_items)
                    
                    st.markdown("** รายการอาหารในบิล:**")
                    for oi_id, iname, iqty, inote, iprice, istatus, dish_img in items_in_order:
                        with st.container(border=True):
                            it_c1, it_c2 = st.columns([1.1, 2.3])
                            with it_c1:
                                if dish_img and (dish_img.startswith("http") or os.path.exists(dish_img)):
                                    st.image(dish_img, use_container_width=True)
                                else:
                                    st.markdown("<div style='font-size: 2.2rem; text-align: center; line-height: 60px;'></div>", unsafe_allow_html=True)
                            with it_c2:
                                st.markdown(f"**{iname}** <span style='color: #ea580c; font-weight: bold;'>x{iqty}</span>", unsafe_allow_html=True)
                                st.caption(f"฿{int(iprice * iqty):,}")
                                if inote:
                                    st.caption(f" {inote}")
                                
                                if istatus == 'pending':
                                    st.markdown("<span style='background: #fff7ed; color: #c2410c; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #fdba74;'> กำลังปรุง</span>", unsafe_allow_html=True)
                                elif istatus == 'cooked':
                                    st.markdown("<span style='background: #f3e8ff; color: #7e22ce; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #d8b4fe;'> เสร็จแล้ว</span>", unsafe_allow_html=True)
                                elif istatus == 'served':
                                    st.markdown("<span style='background: #f0fdf4; color: #15803d; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #86efac;'> เสิร์ฟแล้ว</span>", unsafe_allow_html=True)
                            
                            # ปุ่มเปลี่ยนสถานะแต่ละเมนู: เสร็จแล้ว / นำเสิร์ฟแล้ว
                            act_c1, act_c2 = st.columns(2)
                            if istatus == 'pending':
                                with act_c1:
                                    if st.button(" เสร็จ", key=f"btn_ck_{oi_id}", use_container_width=True, help="เปลี่ยนสถานะเป็นปรุงเสร็จแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'cooked' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'cooked' WHERE id = ? AND status IN ('pending', 'accepted')", (oid,))
                                        conn.commit()
                                        st.rerun()
                                with act_c2:
                                    if st.button(" เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'served' WHERE id = ?", (oi_id,))
                                        c.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ? AND status != 'served'", (oid,))
                                        if c.fetchone()[0] == 0:
                                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                                        else:
                                            c.execute("UPDATE orders SET status = 'cooked' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                            elif istatus == 'cooked':
                                with act_c1:
                                    st.caption("รอพนักงานยกเสิร์ฟ")
                                with act_c2:
                                    if st.button(" เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'served' WHERE id = ?", (oi_id,))
                                        c.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ? AND status != 'served'", (oid,))
                                        if c.fetchone()[0] == 0:
                                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                            elif istatus == 'served':
                                with act_c1:
                                    st.write("")
                                with act_c2:
                                    if st.button("↩ ยกเลิก", key=f"btn_un_{oi_id}", use_container_width=True, help="ย้อนกลับเป็นกำลังปรุง"):
                                        c.execute("UPDATE order_items SET status = 'pending' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'cooked' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                    
                    # ปุ่มทางลัด: เสิร์ฟทุกเมนูพร้อมกัน
                    if not all_items_served:
                        if st.button(" เสิร์ฟทุกเมนูทันที", key=f"btn_all_srv_{oid}", use_container_width=True):
                            c.execute("UPDATE order_items SET status = 'served' WHERE order_id = ?", (oid,))
                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                            conn.commit()
                            st.toast(f"เสิร์ฟอาหารโต๊ะ {t_id} ครบทุกเมนูแล้วค่ะ!", icon="")
                            st.rerun()

                    st.write("---")
                    st.markdown(f"**ยอดรวม: <span style='color: #ea580c; font-size: 1.15rem; font-weight: bold;'>฿{int(total):,}</span>**", unsafe_allow_html=True)
                    
                    # Requirement: เช็คบิลได้เฉพาะเมื่อเสิร์ฟครบทุกเมนูแล้วเท่านั้น
                    if not all_items_served:
                        st.warning(f" เสิร์ฟแล้ว {served_items}/{total_items} เมนู (ปุ่มเช็คบิลจะเปิดเมื่อเสิร์ฟครบ)")
                        st.button(f" เช็คบิลโต๊ะ {t_id} (รอเสิร์ฟครบ)", key=f"btn_bill_{oid}", disabled=True, use_container_width=True)
                    else:
                        st.success(f" เสิร์ฟครบ {served_items}/{total_items} เมนูแล้ว พร้อมเช็คบิลค่ะ!")
                        if st.button(f" เช็คบิล & ออกใบเสร็จอย่างย่อ (โต๊ะ {t_id})", key=f"btn_bill_{oid}", type="primary", use_container_width=True):
                            st.session_state['active_receipt_oid'] = oid
                            st.rerun()

                    # ปุ่มเคลียร์โต๊ะรับลูกค้าใหม่
                    st.write("")
                    if st.button(f" เคลียร์โต๊ะ {t_id}", key=f"adm_clr_{oid}", use_container_width=True, help="ล้างสถานะเพื่อรับลูกค้าใหม่"):
                        c.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_id,))
                        conn.commit()
                        st.toast(f"เคลียร์โต๊ะ {t_id} เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!", icon="")
                        st.rerun()

    # Expander: ประวัติบิลที่ชำระแล้ววันนี้
    st.write("---")
    with st.expander(" ประวัติบิลที่ชำระแล้ววันนี้ (ดู/พิมพ์ใบเสร็จย้อนหลัง)", expanded=False):
        c.execute("""
            SELECT id, table_id, total_price, created_at, status 
            FROM orders 
            WHERE status IN ('paid', 'archived')
            ORDER BY id DESC LIMIT 15
        """)
        past_orders = c.fetchall()
        if not past_orders:
            st.info("ยังไม่มีบิลที่ชำระแล้วในวันนี้ค่ะ")
        else:
            for p_id, p_tid, p_tot, p_time, p_st in past_orders:
                st_p_col1, st_p_col2, st_p_col3 = st.columns([2, 1.5, 1.5])
                st_p_col1.markdown(f"**บิล #{p_id}** — โต๊ะที่ {p_tid} (เวลา: {p_time})")
                st_p_col2.markdown(f"**฿{int(p_tot):,}**")
                with st_p_col3:
                    if st.button(" พิมพ์ใบเสร็จ", key=f"btn_reprint_{p_id}", use_container_width=True):
                        st.session_state['active_receipt_oid'] = p_id
                        st.rerun()
                        
    conn.close()

# ==============================================================================
#  ฝั่งร้านค้า (เคาน์เตอร์ & ครัว & เมนูขายดี) -> https://.../?mode=admin
# ==============================================================================
# หน้านี้สำหรับพนักงานและเจ้าของร้าน โดยเข้าใช้งานผ่านการเติม ?mode=admin ท้าย URL
# ประกอบด้วย 3 แท็บหลัก:
# 1. จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR Code)
# 2. จอครัว & เคาน์เตอร์คิดเงิน (KDS)
# 3. อันดับเมนูขายดี
if is_admin_mode:
    # ตรวจสอบสถานะการเข้าสู่ระบบ (Admin Authentication Check)
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_user_info'] = None

    # Header โลโก้ร้าน
    logo_b64 = get_base64_image(logo_path)
    if logo_b64:
        logo_html = f'''<div style="text-align: center; margin-bottom: 8px;">
            <img src="data:image/png;base64,{logo_b64}" 
                 style="width: 145px; height: 145px; object-fit: cover; border-radius: 50%; box-shadow: 0 6px 20px rgba(234, 88, 12, 0.32); border: 4px solid #ffedd5; display: inline-block;" 
                 alt="โลโก้ฟ้าใสตำนัว" />
        </div>'''
    elif os.path.exists(logo_path):
        logo_html = f'<div style="text-align: center; margin-bottom: 8px;"><img src="{logo_path}" style="width: 145px; height: 145px; object-fit: cover; border-radius: 50%; border: 4px solid #ffedd5; box-shadow: 0 6px 20px rgba(234, 88, 12, 0.32); display: inline-block;" alt="โลโก้ฟ้าใสตำนัว" /></div>'
    else:
        logo_html = '<div style="text-align: center; font-size: 75px; margin-bottom: 4px;"></div>'

    #  กรณีที่ยังไม่ได้ลงชื่อเข้าใช้: แสดงฟอร์ม Login ปลอดภัย
    if not st.session_state['admin_logged_in']:
        login_header_html = f'''
        {logo_html}
        <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.3rem; margin: 4px 0 2px 0; line-height: 1.2;">
            ฟ้าใสตำนัว (ระบบจัดการหลังร้าน)
        </h1>
        <p style="text-align: center; color: #78716c; font-size: 1.05rem; margin: 0 0 16px 0;">
             กรุณาลงชื่อเข้าใช้งานเพื่อเข้าถึงระบบจัดการร้าน จอครัว และเคาน์เตอร์คิดเงิน
        </p>
        '''
        st.markdown(login_header_html, unsafe_allow_html=True)
        st.write("---")

        col_l1, col_l2, col_l3 = st.columns([1, 1.6, 1])
        with col_l2:
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center; color: #431407; margin-bottom: 4px;'>เข้าสู่ระบบผู้ดูแลร้าน</h3>", unsafe_allow_html=True)
                st.caption("ป้อนชื่อผู้ใช้งานและรหัสผ่านเพื่อยืนยันสิทธิ์")
                
                with st.form("admin_login_form"):
                    input_user = st.text_input(" ชื่อผู้ใช้ (Username):", placeholder="เช่น admin", key="inp_admin_user")
                    input_pass = st.text_input(" รหัสผ่าน (Password):", type="password", placeholder="ป้อนรหัสผ่าน", key="inp_admin_pass")
                    submit_login = st.form_submit_button(" ลงชื่อเข้าใช้", type="primary", use_container_width=True)

                    if submit_login:
                        if not input_user.strip() or not input_pass.strip():
                            st.error("กรุณากรอกชื่อผู้ใช้งานและรหัสผ่านให้ครบถ้วนค่ะ")
                        else:
                            conn_auth = sqlite3.connect(DB_NAME)
                            c_auth = conn_auth.cursor()
                            c_auth.execute("SELECT id, username, password_hash, salt, full_name, role FROM admin_users WHERE LOWER(username) = LOWER(?)", (input_user.strip(),))
                            user_record = c_auth.fetchone()
                            conn_auth.close()

                            if user_record and verify_password(input_pass.strip(), user_record[2], user_record[3]):
                                st.session_state['admin_logged_in'] = True
                                st.session_state['admin_user_info'] = {
                                    'id': user_record[0],
                                    'username': user_record[1],
                                    'full_name': user_record[4],
                                    'role': user_record[5]
                                }
                                st.toast(f"ยินดีต้อนรับ {user_record[4]} เข้าสู่ระบบค่ะ! ", icon="")
                                st.rerun()
                            else:
                                st.error(" ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้งค่ะ")

        render_app_footer()
        st.stop()

    #  กรณีที่ลงชื่อเข้าใช้สำเร็จแล้ว: แสดงแถบข้อมูลผู้ใช้งาน + ปุ่มออกจากระบบ
    u_info = st.session_state.get('admin_user_info') or {}
    u_name = u_info.get('full_name', 'ผู้ดูแลระบบ')
    u_role = u_info.get('role', 'admin')

    header_html = f'''
    {logo_html}
    <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.3rem; margin: 4px 0 2px 0; line-height: 1.2;">
        ฟ้าใสตำนัว (ระบบจัดการหลังร้าน)
    </h1>
    <p style="text-align: center; color: #78716c; font-size: 1.05rem; margin: 0 0 10px 0;">
         หน้าจอเคาน์เตอร์คิดเงิน • ครัวปรุงอาหาร • อันดับเมนูขายดี
    </p>
    '''
    st.markdown(header_html, unsafe_allow_html=True)

    # แถบผู้ใช้งานเข้าสู่ระบบ & ปุ่มเปลี่ยนรหัสผ่าน & ปุ่มออกจากระบบ
    col_u1, col_u2, col_u3 = st.columns([2.2, 1.1, 1.1])
    with col_u1:
        st.markdown(f"<div style='font-size: 15px; color: #166534; font-weight: 600; padding-top: 6px;'> เข้าสู่ระบบในนาม: <b>{u_name}</b> (สิทธิ์: {u_role})</div>", unsafe_allow_html=True)
    with col_u2:
        with st.popover(" เปลี่ยนรหัสผ่าน", use_container_width=True):
            st.markdown("###  เปลี่ยนรหัสผ่าน")
            st.caption(f"เปลี่ยนรหัสผ่านสำหรับ: **{u_info.get('username', 'admin')}**")
            with st.form("form_change_admin_pw", clear_on_submit=True):
                old_pw = st.text_input("รหัสผ่านเดิม:", type="password", key="chg_old_pw")
                new_pw = st.text_input("รหัสผ่านใหม่ (อย่างน้อย 6 ตัวอักษร):", type="password", key="chg_new_pw")
                cfm_pw = st.text_input("ยืนยันรหัสผ่านใหม่:", type="password", key="chg_cfm_pw")
                btn_sub_pw = st.form_submit_button(" บันทึกรหัสผ่านใหม่", type="primary", use_container_width=True)
                
                if btn_sub_pw:
                    if not old_pw:
                        st.error("กรุณาระบุรหัสผ่านเดิมค่ะ")
                    elif not new_pw:
                        st.error("กรุณาระบุรหัสผ่านใหม่ค่ะ")
                    elif len(new_pw) < 6:
                        st.error("รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษรค่ะ")
                    elif new_pw != cfm_pw:
                        st.error("รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกันค่ะ")
                    else:
                        conn_pw = sqlite3.connect(DB_NAME)
                        c_pw = conn_pw.cursor()
                        c_pw.execute("SELECT id, password_hash, salt FROM admin_users WHERE id = ?", (u_info.get('id', 1),))
                        u_rec = c_pw.fetchone()
                        
                        if not u_rec or not verify_password(old_pw.strip(), u_rec[1], u_rec[2]):
                            st.error(" รหัสผ่านเดิมไม่ถูกต้อง กรุณาตรวจสอบอีกครั้งค่ะ")
                            conn_pw.close()
                        else:
                            new_hash, new_salt = hash_password(new_pw.strip())
                            c_pw.execute("UPDATE admin_users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, u_info.get('id', 1)))
                            conn_pw.commit()
                            conn_pw.close()
                            st.toast(" เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!", icon="")
                            st.success(" เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว! รหัสผ่านใหม่จะมีผลทันทีค่ะ")
                            st.rerun()

    with col_u3:
        if st.button(" ออกจากระบบ", key="btn_admin_logout", use_container_width=True):
            st.session_state['admin_logged_in'] = False
            st.session_state['admin_user_info'] = None
            st.rerun()

    st.write("---")

    # แยก 5 แท็บสำหรับจัดการหลังร้าน
    tab_tbl, tab_pos, tab_rep, tab_mem, tab_menu = st.tabs([
        " จัดการโต๊ะอาหาร & เคลียร์โต๊ะ", 
        " จอครัว & เคาน์เตอร์คิดเงิน", 
        " เมนูขายดี",
        " ประวัติลูกค้า",
        " จัดการเมนูอาหาร"
    ])


    # --------------------------------------------------------------------------
    # แท็บที่ 1:  จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR-Code)
    # --------------------------------------------------------------------------
    with tab_tbl:
        st.subheader(" จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR-Code)")
        st.caption("เพิ่มหรือลบโต๊ะอาหารในร้าน สร้าง QR-Code ติดโต๊ะให้ลูกค้าสแกนสั่งอาหาร และกดล้างสถานะโต๊ะเพื่อรับลูกค้ารายใหม่")
        
        conn_tb = sqlite3.connect(DB_NAME)
        c_tb = conn_tb.cursor()
        
        # ดึงรายชื่อโต๊ะทั้งหมด พร้อมนับจำนวนออเดอร์ค้าง (active_orders) และบิลที่จ่ายเงินแล้วรอเคลียร์ (paid_orders)
        # ใช้ LEFT JOIN เพื่อให้โต๊ะที่ยังไม่มีออเดอร์ยังคงแสดงผลขึ้นมาได้
        c_tb.execute("""
            SELECT t.table_number, t.name,
                   COUNT(CASE WHEN o.status NOT IN ('paid', 'archived') THEN 1 END) as active_orders,
                   COUNT(CASE WHEN o.status = 'paid' THEN 1 END) as paid_orders
            FROM tables t
            LEFT JOIN orders o ON t.table_number = o.table_id
            GROUP BY t.table_number
            ORDER BY t.table_number ASC
        """)
        table_statuses = c_tb.fetchall()

        existing_nums = [r[0] for r in table_statuses]
        
        # ลิงก์ร้านสำหรับสร้าง QR-Code (ตรวจจับโดเมนอัตโนมัติ ไม่ว่าจะเปิดในร้านใด/บัญชีใด)
        base_url_for_qr = get_current_base_url()

        # ส่วนที่ 1: เมนู เพิ่ม / ลบ โต๊ะอาหารในร้าน
        st.markdown("###  1. เพิ่ม / ลบ โต๊ะอาหารในร้าน")
        t_c1, t_c2 = st.columns(2)
        
        with t_c1:
            with st.container(border=True):
                st.markdown("####  เพิ่มโต๊ะใหม่")
                st.caption("เมื่อเพิ่มแล้ว ระบบจะสร้าง QR-Code และลิงก์สั่งอาหารของโต๊ะนั้นให้ทันที")
                next_t_num = (max(existing_nums) + 1) if existing_nums else 1
                new_t_num = st.number_input("หมายเลขโต๊ะที่จะเพิ่ม:", min_value=1, max_value=999, value=next_t_num, step=1, key="add_t_num_input")
                new_t_name = st.text_input("ชื่อเรียกโต๊ะ:", value=f"โต๊ะที่ {new_t_num}", key="add_t_name_input")
                
                if st.button(" ยืนยันเพิ่มโต๊ะและสร้าง QR-Code", key="btn_add_new_table", type="primary", use_container_width=True):
                    if new_t_num in existing_nums:
                        st.error(f"หมายเลขโต๊ะ {new_t_num} มีอยู่ในระบบแล้วค่ะ")
                    else:
                        c_tb.execute("INSERT INTO tables (table_number, name) VALUES (?, ?)", (new_t_num, new_t_name))
                        conn_tb.commit()
                        st.success(f"เพิ่ม '{new_t_name}' สำเร็จ พร้อมเปิดใช้งาน QR-Code เรียบร้อยแล้วค่ะ! ")
                        st.rerun()

        with t_c2:
            with st.container(border=True):
                st.markdown("####  ลบโต๊ะอาหาร")
                st.caption("ลบโต๊ะที่ไม่ใช้งานออกจากระบบ")
                if existing_nums:
                    table_options = [f"โต๊ะที่ {r[0]} ({r[1]})" for r in table_statuses]
                    table_to_del_str = st.selectbox("เลือกโต๊ะที่ต้องการลบ:", table_options, key="select_del_t")
                    del_t_num = int(table_to_del_str.split(" ")[1])
                    
                    if st.button(f" ยืนยันลบโต๊ะที่ {del_t_num}", key="btn_del_table", use_container_width=True):
                        c_tb.execute("DELETE FROM tables WHERE table_number = ?", (del_t_num,))
                        conn_tb.commit()
                        st.warning(f"ลบโต๊ะที่ {del_t_num} ออกจากระบบเรียบร้อยแล้ว")
                        st.rerun()
                else:
                    st.info("ปัจจุบันยังไม่มีโต๊ะอาหารในระบบ")
        
        st.write("---")

        # ส่วนที่ 2: รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & เคลียร์สถานะโต๊ะ
        st.markdown("###  2. รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & ล้างสถานะโต๊ะ")
        
        if not table_statuses:
            st.info("ℹ **ขณะนี้ยังไม่มีโต๊ะอาหารในร้าน** (ค่าเริ่มต้น 0 โต๊ะ)\n\n สามารถเพิ่มโต๊ะใหม่ได้ที่แบบฟอร์ม **' เพิ่มโต๊ะใหม่'** ด้านบนค่ะ เมื่อเพิ่มแล้ว QR-Code สำหรับติดโต๊ะและระบบสั่งอาหารจะแสดงที่นี่ทันที ")
        else:
            total_tbls = len(table_statuses)
            busy_tbls = sum(1 for r in table_statuses if (r[2] > 0 or r[3] > 0))
            free_tbls = total_tbls - busy_tbls
            
            # สรุปภาพรวมของโต๊ะ
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric(" โต๊ะอาหารทั้งหมด", f"{total_tbls} โต๊ะ")
            col_m2.metric(" โต๊ะว่างพร้อมรับลูกค้า", f"{free_tbls} โต๊ะ")
            col_m3.metric(" มีลูกค้า / รอเคลียร์", f"{busy_tbls} โต๊ะ")

            # ปุ่มล้างทุกโต๊ะที่เช็คบิลแล้วพร้อมกัน
            total_paid_orders = sum(r[3] for r in table_statuses)
            if total_paid_orders > 0:
                if st.button(" ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วพร้อมกันทั้งหมด", type="primary", use_container_width=True):
                    c_tb.execute("UPDATE orders SET status = 'archived' WHERE status = 'paid'")
                    conn_tb.commit()
                    st.toast("ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วเรียบร้อย!", icon="")
                    st.rerun()
                st.write("")

            st.caption(" แนะนำ: พิมพ์หรือเปิดภาพ **QR-Code** ด้านล่างนี้ไปติดไว้ที่โต๊ะอาหาร ลูกค้าสแกนเพื่อเปิดเมนูสั่งอาหารได้ทันที")
            
            clr_cols = st.columns(3)
            for idx, (t_no, t_name, act_cnt, paid_cnt) in enumerate(table_statuses):
                with clr_cols[idx % 3]:
                    with st.container(border=True):
                        # หัวการ์ดโต๊ะและสถานะแบบสีสันสดใส มีมิติ
                        if act_cnt > 0:
                            hdr_gradient = "linear-gradient(135deg, #f97316 0%, #ea580c 100%)"
                            badge_html = "<span style='background: #fef3c7; color: #9a3412; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'> มีออเดอร์ค้าง</span>"
                            stat_text = f"<span style='color: #ea580c; font-weight: 700;'>มีออเดอร์ค้าง {act_cnt} บิล (กำลังทำ/รอเสิร์ฟ)</span>"
                        elif paid_cnt > 0:
                            hdr_gradient = "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
                            badge_html = "<span style='background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'> เช็คบิลแล้ว</span>"
                            stat_text = f"<span style='color: #2563eb; font-weight: 700;'>เช็คบิลแล้ว {paid_cnt} บิล (รอเคลียร์โต๊ะ)</span>"
                        else:
                            hdr_gradient = "linear-gradient(135deg, #10b981 0%, #059669 100%)"
                            badge_html = "<span style='background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'> โต๊ะว่าง</span>"
                            stat_text = "<span style='color: #059669; font-weight: 700;'>โต๊ะว่าง (พร้อมรับลูกค้า)</span>"

                        st.markdown(f"""
                        <div style="background: {hdr_gradient}; padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #ffffff; font-weight: 800; font-size: 1.15rem;"> {t_name}</span>
                            {badge_html}
                        </div>
                        <div style="font-size: 0.9rem; margin-bottom: 8px;">สถานะ: {stat_text}</div>
                        """, unsafe_allow_html=True)

                        # ลิงก์สำหรับลูกค้าโต๊ะนี้
                        cust_table_url = f"{base_url_for_qr}/?table={t_no}"
                        qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={quote(cust_table_url)}&margin=10"
                        
                        # แสดงภาพ QR Code
                        st.image(qr_image_url, caption=f"QR-Code สั่งอาหาร {t_name}", use_container_width=True)
                        
                        # ลิงก์ตรงเปิดหน้าสั่งอาหาร
                        st.markdown(f"""
                        <div style="text-align: center; margin-bottom: 8px;">
                            <a href="{cust_table_url}" target="_blank" style="display: inline-block; background: #fff7ed; color: #ea580c; border: 1.5px solid #fdba74; padding: 4px 12px; border-radius: 6px; font-weight: 600; text-decoration: none; font-size: 0.85rem;">
                                 เปิดหน้าสั่งอาหารโต๊ะนี้ (ทดสอบ)
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ปุ่มล้างสถานะโต๊ะเพื่อรับลูกค้าใหม่
                        btn_type = "primary" if (paid_cnt > 0 or act_cnt > 0) else "secondary"
                        if st.button(f" ล้างสถานะโต๊ะ {t_no} (รับลูกค้าใหม่)", key=f"btn_clr_tbl_{t_no}", use_container_width=True, type=btn_type):
                            c_tb.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_no,))
                            conn_tb.commit()
                            st.toast(f"ล้างสถานะ '{t_name}' เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!", icon="")
                            st.rerun()

                        # ปุ่มลบโต๊ะ
                        with st.popover(f" ลบ {t_name}"):
                            st.markdown(f"ยืนยันการลบ **{t_name}** ออกจากระบบ?")
                            if st.button(f"ยืนยันลบโต๊ะ {t_no}", key=f"btn_pop_del_{t_no}", type="primary", use_container_width=True):
                                c_tb.execute("DELETE FROM tables WHERE table_number = ?", (t_no,))
                                conn_tb.commit()
                                st.warning(f"ลบ {t_name} เรียบร้อยแล้วค่ะ")
                                st.rerun()

        conn_tb.close()

    # --------------------------------------------------------------------------
    # แท็บที่ 2:  จอครัว & เคาน์เตอร์คิดเงิน (Kitchen POS Dashboard)
    # --------------------------------------------------------------------------
    with tab_pos:
        # เรียกใช้ฟังก์ชัน fragment ที่รีเฟรชออเดอร์อัตโนมัติทุก 3 วินาที
        render_pos_dashboard()

    # --------------------------------------------------------------------------
    # แท็บที่ 3:  อันดับเมนูขายดี (Best Selling Menus Dashboard)
    # --------------------------------------------------------------------------
    with tab_rep:
        st.subheader(" อันดับเมนูขายดี (Best Selling Menus)")
        st.caption("จัดอันดับเมนูยอดนิยมของฟ้าใสตำนัว ตามจำนวนจานและยอดขายรวม")
        
        conn_bs = sqlite3.connect(DB_NAME)
        c_bs = conn_bs.cursor()

        
        # ตัวกรองช่วงเวลาและการเรียงลำดับ
        c_f1, c_f2 = st.columns([1.5, 2])
        with c_f1:
            filter_period = st.pills(" ช่วงเวลา:", ["ทั้งหมด", "วันนี้"], default="ทั้งหมด", key="pills_period_filter")
        with c_f2:
            sort_by = st.pills(" จัดอันดับตาม:", ["จำนวนจานที่ขายได้ (จาน)", "ยอดขายรวม (บาท)"], default="จำนวนจานที่ขายได้ (จาน)", key="pills_sort_filter")

        thai_today_str = get_thai_now().strftime('%Y-%m-%d')
        date_sql = f"AND DATE(o.created_at) = '{thai_today_str}'" if filter_period == "วันนี้" else ""
        order_sql = "total_qty DESC, total_sales DESC" if "จำนวนจาน" in sort_by else "total_sales DESC, total_qty DESC"
        
        c_bs.execute(f'''
            SELECT 
                oi.item_name,
                COALESCE(mi.category, 'ทั่วไป') as category,
                COALESCE(mi.image, '') as image,
                COALESCE(mi.price, oi.price) as unit_price,
                SUM(oi.quantity) as total_qty,
                SUM(oi.quantity * oi.price) as total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN menu_items mi ON oi.item_name = mi.name
            WHERE o.status != 'cancelled' {date_sql}
            GROUP BY oi.item_name
            ORDER BY {order_sql}
        ''')
        best_sellers = c_bs.fetchall()
        
        if not best_sellers:
            st.info("ยังไม่มีข้อมูลการขายในช่วงเวลานี้ค่ะ")
        else:
            total_sold_all = sum(r[4] for r in best_sellers)
            total_revenue_all = sum(r[5] for r in best_sellers)
            top_seller = best_sellers[0]
            
            # สถิติภาพรวมด้านบน
            m1, m2, m3 = st.columns(3)
            m1.metric(" จำนวนอาหารที่ขายได้รวม", f"{total_sold_all:,} จาน")
            m2.metric(" ยอดขายรวม", f"฿{int(total_revenue_all):,}")
            m3.metric(" เมนูขายดีอันดับ 1", f"{top_seller[0]}", f"{top_seller[4]} จาน (฿{int(top_seller[5]):,})")
            
            st.write("---")
            
            # 3 อันดับแรก (Podium Top 3)
            st.markdown("###  3 อันดับเมนูยอดนิยมสูงสุด")
            podium_cols = st.columns(min(3, len(best_sellers)))
            medals = [" อันดับ 1 (แชมป์)", " อันดับ 2", " อันดับ 3"]
            badge_bg = ["#fef3c7", "#f1f5f9", "#ffedd5"]
            badge_border = ["#f59e0b", "#94a3b8", "#f97316"]
            
            for p_idx in range(min(3, len(best_sellers))):
                p_name, p_cat, p_img, p_price, p_qty, p_sales = best_sellers[p_idx]
                with podium_cols[p_idx]:
                    with st.container(border=True):
                        st.markdown(f"<div style='background: {badge_bg[p_idx]}; border: 1.5px solid {badge_border[p_idx]}; border-radius: 6px; padding: 4px 8px; text-align: center; font-weight: bold; font-size: 1rem; margin-bottom: 8px;'>{medals[p_idx]}</div>", unsafe_allow_html=True)
                        if p_img and (p_img.startswith("http") or os.path.exists(p_img)):
                            st.image(p_img, use_container_width=True)
                        st.markdown(f"**{p_name}**")
                        st.caption(f"หมวดหมู่: {p_cat}")
                        st.markdown(f" ขายได้: <span style='color: #ea580c; font-size: 1.25rem; font-weight: bold;'>{p_qty} จาน</span>", unsafe_allow_html=True)
                        st.markdown(f" รวมเงิน: **฿{int(p_sales):,}**")

            st.write("---")
            
            # ตารางจัดอันดับทั้งหมด
            st.markdown("###  ตารางจัดอันดับเมนูขายดีทั้งหมด")
            max_qty = best_sellers[0][4] if best_sellers and best_sellers[0][4] > 0 else 1
            
            for rank, (iname, icat, iimg, iprice, iqty, isales) in enumerate(best_sellers, 1):
                with st.container(border=True):
                    rc1, rc2, rc3, rc4 = st.columns([0.8, 1.2, 3, 2])
                    with rc1:
                        if rank == 1:
                            r_badge = " #1"
                        elif rank == 2:
                            r_badge = " #2"
                        elif rank == 3:
                            r_badge = " #3"
                        else:
                            r_badge = f"#{rank}"
                        st.markdown(f"<div style='font-size: 1.3rem; font-weight: 800; line-height: 60px; text-align: center; color: #ea580c;'>{r_badge}</div>", unsafe_allow_html=True)
                    with rc2:
                        if iimg and (iimg.startswith("http") or os.path.exists(iimg)):
                            st.image(iimg, use_container_width=True)
                        else:
                            st.markdown("<div style='font-size: 2.2rem; text-align: center; line-height: 60px;'></div>", unsafe_allow_html=True)
                    with rc3:
                        st.markdown(f"**{iname}**")
                        st.caption(f"หมวด: {icat} • ราคา ฿{int(iprice)}/จาน")
                        pct_of_top = min(1.0, float(iqty) / float(max_qty))
                        st.progress(pct_of_top)
                    with rc4:
                        st.markdown(f"<div style='text-align: right;'><span style='font-size: 1.25rem; font-weight: bold; color: #ea580c;'>{iqty} จาน</span><br><span style='font-size: 0.95rem; color: #555;'>฿{int(isales):,}</span></div>", unsafe_allow_html=True)

            # สรุปยอดขายแยกตามหมวดหมู่อาหาร
            st.write("---")
            st.markdown("###  สรุปยอดขายแยกตามหมวดหมู่อาหาร")
            c_bs.execute(f'''
                SELECT 
                    COALESCE(mi.category, 'ทั่วไป') as category,
                    SUM(oi.quantity) as cat_qty,
                    SUM(oi.quantity * oi.price) as cat_sales
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                LEFT JOIN menu_items mi ON oi.item_name = mi.name
                WHERE o.status != 'cancelled' {date_sql}
                GROUP BY mi.category
                ORDER BY cat_qty DESC
            ''')
            cat_summary = c_bs.fetchall()
            if cat_summary:
                cat_cols = st.columns(min(len(cat_summary), 4))
                for c_idx, (cname, cqty, csales) in enumerate(cat_summary):
                    with cat_cols[c_idx % len(cat_cols)]:
                        with st.container(border=True):
                            st.markdown(f"**{cname}**")
                            st.markdown(f" ขายได้: **{cqty} จาน**")
                            st.caption(f"ยอดรวม: ฿{int(csales):,}")
        conn_bs.close()

    # --------------------------------------------------------------------------
    # แท็บที่ 4:  ประวัติลูกค้า (Customer History & Loyalty Members)
    # --------------------------------------------------------------------------
    with tab_mem:
        st.subheader(" ประวัติลูกค้า & ระบบสมาชิกสะสมแต้ม")
        st.caption("ดูข้อมูลสมาชิก จัดการคะแนนสะสม เรียงลำดับจากคะแนนมากไปน้อย และสมัครสมาชิกใหม่หน้าร้าน")
        
        conn_mem = sqlite3.connect(DB_NAME)
        c_mem = conn_mem.cursor()

        # ฟอร์มสมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)
        with st.expander(" สมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)", expanded=False):
            st.markdown("##### กรอกข้อมูลสมาชิกลูกค้า")
            st.caption("ข้อมูลที่ใช้: ชื่อ, นามสกุล และหมายเลขโทรศัพท์")
            mf_c1, mf_c2, mf_c3 = st.columns(3)
            with mf_c1:
                adm_fname = st.text_input("ชื่อ:", key="adm_reg_fname", placeholder="ชื่อจริง")
            with mf_c2:
                adm_lname = st.text_input("นามสกุล:", key="adm_reg_lname", placeholder="นามสกุล")
            with mf_c3:
                adm_phone = st.text_input("หมายเลขโทรศัพท์:", key="adm_reg_phone", placeholder="เช่น 0937734851")
                
            if st.button(" บันทึกข้อมูลสมาชิก", key="btn_adm_save_member", type="primary", use_container_width=True):
                cl_adm_ph = adm_phone.strip().replace("-", "").replace(" ", "")
                if not adm_fname.strip() or not adm_lname.strip() or not cl_adm_ph:
                    st.error("กรุณากรอกข้อมูล ชื่อ นามสกุล และหมายเลขโทรศัพท์ให้ครบถ้วนค่ะ")
                else:
                    c_mem.execute("SELECT id FROM members WHERE phone = ?", (cl_adm_ph,))
                    if c_mem.fetchone():
                        st.error(f"หมายเลขโทรศัพท์ {cl_adm_ph} มีอยู่ในระบบสมาชิกแล้วค่ะ")
                    else:
                        reg_now = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                        c_mem.execute(
                            "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, 0, ?)",
                            (adm_fname.strip(), adm_lname.strip(), cl_adm_ph, reg_now)
                        )
                        conn_mem.commit()
                        st.success(f"บันทึกสมาชิก 'คุณ {adm_fname} {adm_lname}' เรียบร้อยแล้วค่ะ! ")
                        st.rerun()

        st.write("---")

        # ช่องค้นหาลูกค้า
        search_kw = st.text_input(" ค้นหาลูกค้า (ชื่อ, นามสกุล หรือ เบอร์โทรศัพท์):", placeholder="พิมพ์คำค้นหา...", key="mem_search_input")
        kw_pattern = f"%{search_kw.strip()}%"

        # ดึงรายชื่อลูกค้า เรียงตามคะแนนสะสมจากมากไปน้อย (ORDER BY points DESC)
        c_mem.execute("""
            SELECT 
                m.id, 
                m.first_name, 
                m.last_name, 
                m.phone, 
                m.points, 
                m.created_at,
                COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN o.id END) as paid_orders,
                COALESCE(SUM(CASE WHEN o.status = 'paid' THEN o.total_price ELSE 0 END), 0) as total_spent
            FROM members m
            LEFT JOIN orders o ON m.phone = o.member_phone
            WHERE (m.first_name LIKE ? OR m.last_name LIKE ? OR m.phone LIKE ?)
            GROUP BY m.id
            ORDER BY m.points DESC, total_spent DESC, m.id ASC
        """, (kw_pattern, kw_pattern, kw_pattern))
        members_list = c_mem.fetchall()

        # สถิติภาพรวมสมาชิก
        c_mem.execute("SELECT COUNT(*), COALESCE(SUM(points), 0) FROM members")
        tot_m_cnt, tot_pts_sum = c_mem.fetchone()

        sm1, sm2, sm3 = st.columns(3)
        sm1.metric(" สมาชิกทั้งหมด", f"{tot_m_cnt} คน")
        sm2.metric(" คะแนนสะสมรวมทั้งระบบ", f"{tot_pts_sum:,} แต้ม")
        top_member_txt = f"{members_list[0][1]} {members_list[0][2]} ({members_list[0][4]} แต้ม)" if members_list else "-"
        sm3.metric(" แชมป์แต้มสูงสุด", top_member_txt)

        st.markdown(f"###  รายชื่อสมาชิกลูกค้า (เรียงตามคะแนนสะสมมากที่สุด)")
        st.caption("กฎคะแนน: ทุก ๆ 100 บาท (ยอดสุทธิ) ได้รับ 1 คะแนน | 10 คะแนน แลกส่วนลด 25 บาท")

        if not members_list:
            if search_kw:
                st.warning(f"ไม่พบข้อมูลสมาชิกที่ตรงกับคำค้นหา '{search_kw}'")
            else:
                st.info("ขณะนี้ยังไม่มีข้อมูลสมาชิกลูกค้าในระบบ สามารถกด **' สมัครสมาชิกลูกค้าใหม่'** ด้านบนได้เลยค่ะ")
        else:
            for idx, (mid, fname, lname, phone, pts, reg_date, order_cnt, spent) in enumerate(members_list, 1):
                # ตราอันดับคะแนน
                if idx == 1:
                    badge = " อันดับ 1"
                elif idx == 2:
                    badge = " อันดับ 2"
                elif idx == 3:
                    badge = " อันดับ 3"
                else:
                    badge = f"#{idx}"

                with st.container(border=True):
                    mc1, mc2, mc3, mc4 = st.columns([1.2, 3.5, 2.5, 2.5])
                    with mc1:
                        st.markdown(f"<div style='font-size: 1.15rem; font-weight: 700; color: #ea580c; text-align: center; line-height: 40px;'>{badge}</div>", unsafe_allow_html=True)
                    with mc2:
                        st.markdown(f"**คุณ{fname} {lname}**")
                        st.caption(f" เบอร์โทร: **{phone}** • สมัครเมื่อ: {reg_date[:10] if reg_date else '-'}")
                    with mc3:
                        st.markdown(f" คะแนนสะสม: <span style='font-size: 1.25rem; font-weight: 800; color: #ea580c;'>{pts:,}</span> แต้ม", unsafe_allow_html=True)
                        discount_avail = (pts // 10) * 25
                        st.caption(f"แลกส่วนลดได้สูงสุด: **฿{discount_avail:,}**")
                    with mc4:
                        st.markdown(f" มาทาน: **{order_cnt} ครั้ง**")
                        st.caption(f"ยอดซื้อสะสม: **฿{int(spent):,}**")

        conn_mem.close()

    # --------------------------------------------------------------------------
    # แท็บที่ 5:  จัดการเมนูอาหาร (เพิ่ม / ลบ / ค้นหารายการอาหาร)
    # --------------------------------------------------------------------------
    with tab_menu:
        st.subheader(" จัดการรายการอาหาร (เพิ่ม / ลบ / ค้นหา)")
        st.caption("ระบบจัดการเมนูของร้าน เพิ่มเมนูใหม่ กำหนดราคาขาย ต้นทุน รูปภาพ คำอธิบาย และลบเมนูที่ไม่จำหน่ายแล้ว")

        conn_mng = sqlite3.connect(DB_NAME)
        c_mng = conn_mng.cursor()

        # ดึงหมวดหมู่ที่มีอยู่ในปัจจุบันจากฐานข้อมูล
        c_mng.execute("SELECT DISTINCT category FROM menu_items ORDER BY category ASC")
        db_cats = [r[0] for r in c_mng.fetchall()]
        default_cat_options = [
            "ตำนัว", 
            "ตำพรีเมียม", 
            "ยำแซ่บ", 
            "ลาบ & ก้อย & น้ำตก", 
            "ย่าง & ทอด", 
            "ต้มแซ่บ & แกงอีสาน", 
            "อาหารจานเดียว", 
            "ของหวาน", 
            "เครื่องเคียง & ข้าว", 
            "เครื่องดื่ม"
        ]
        all_cat_options = [c for c in default_cat_options if c in db_cats]
        for c in db_cats:
            if c not in all_cat_options:
                all_cat_options.append(c)
        for c in default_cat_options:
            if c not in all_cat_options:
                all_cat_options.append(c)

        # =========================================================
        # 1. ฟอร์มเพิ่มเมนูอาหารใหม่
        # =========================================================
        with st.expander(" เพิ่มรายการอาหารใหม่", expanded=True):
            st.markdown("####  กรอกข้อมูลเมนูใหม่")
            with st.form("form_add_new_menu", clear_on_submit=True):
                col_n1, col_n2 = st.columns([1.5, 1])
                with col_n1:
                    new_name = st.text_input("ชื่อเมนูอาหาร *", placeholder="เช่น ตำถาดทะเลเดือด, กุ้งแช่น้ำปลา", key="in_new_menu_name")
                    
                    cat_select_list = all_cat_options + [" เพิ่มหมวดหมู่ใหม่..."]
                    sel_cat_choice = st.selectbox("หมวดหมู่อาหาร *", cat_select_list, index=0, key="in_new_menu_cat_sel")
                    
                    custom_cat_val = ""
                    if sel_cat_choice == " เพิ่มหมวดหมู่ใหม่...":
                        custom_cat_val = st.text_input("ระบุชื่อหมวดหมู่ใหม่:", placeholder="เช่น เมนูแนะนำพิเศษ, อาหารทานเล่น", key="in_new_custom_cat")
                
                with col_n2:
                    new_price = st.number_input("ราคาขาย (บาท) *", min_value=0.0, value=60.0, step=5.0, format="%.2f", key="in_new_menu_price")
                    new_cost = st.number_input("ต้นทุนวัตถุดิบ (บาท)", min_value=0.0, value=25.0, step=5.0, format="%.2f", key="in_new_menu_cost")
                    margin_val = new_price - new_cost
                    margin_pct = (margin_val / new_price * 100) if new_price > 0 else 0
                    st.caption(f"กำไรเบื้องต้น: **฿{margin_val:,.2f}** ({margin_pct:.1f}%)")

                new_img = st.text_input(
                    "URL หรือ Path รูปภาพอาหาร", 
                    placeholder="เช่น https://example.com/dish.jpg หรือ static/img/menu/menu50.png", 
                    key="in_new_menu_img"
                )

                new_desc = st.text_area(
                    "คำอธิบายเมนูอาหาร", 
                    placeholder="เช่น ส้มตำรสเด็ดใส่เครื่องแน่น รสจัดจ้านถึงใจ ทานคู่กับผักสด...", 
                    key="in_new_menu_desc"
                )

                btn_add_menu = st.form_submit_button(" บันทึกและเพิ่มรายการอาหาร", type="primary", use_container_width=True)
                if btn_add_menu:
                    final_name = new_name.strip()
                    final_cat = custom_cat_val.strip() if sel_cat_choice == " เพิ่มหมวดหมู่ใหม่..." else sel_cat_choice
                    final_img = new_img.strip()
                    final_desc = new_desc.strip()

                    if not final_name:
                        st.error("กรุณาระบุ 'ชื่อเมนูอาหาร' ให้เรียบร้อยค่ะ")
                    elif not final_cat:
                        st.error("กรุณาระบุ 'หมวดหมู่อาหาร' ให้เรียบร้อยค่ะ")
                    else:
                        c_mng.execute("SELECT id FROM menu_items WHERE name = ?", (final_name,))
                        exist_m = c_mng.fetchone()
                        if exist_m:
                            st.error(f" มีเมนูชื่อ '{final_name}' อยู่ในระบบแล้ว กรุณาใช้ชื่ออื่นค่ะ")
                        else:
                            try:
                                c_mng.execute(
                                    "INSERT INTO menu_items (name, category, price, cost, image, description) VALUES (?, ?, ?, ?, ?, ?)",
                                    (final_name, final_cat, new_price, new_cost, final_img, final_desc)
                                )
                                conn_mng.commit()
                                st.success(f" เพิ่มเมนู **'{final_name}'** (หมวด: {final_cat}, ราคา: ฿{new_price:,.2f}) สำเร็จเรียบร้อยแล้วค่ะ!")
                                st.rerun()
                            except Exception as err:
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {err}")

        st.write("---")

        # =========================================================
        # 2. รายการเมนูอาหารทั้งหมด & ค้นหา & ลบเมนู
        # =========================================================
        st.markdown("###  รายการอาหารทั้งหมดในระบบ & จัดการลบ")
        
        f_c1, f_c2 = st.columns([2, 1.5])
        with f_c1:
            search_menu_kw = st.text_input(" ค้นหาตามชื่อเมนู หรือคำอธิบาย:", placeholder="พิมพ์ชื่อเมนูเพื่อค้นหา...", key="in_search_menu_kw").strip()
        with f_c2:
            filter_cat_choice = st.selectbox(" กรองตามหมวดหมู่:", ["ทั้งหมด"] + all_cat_options, key="sel_filter_cat_choice")

        query_sql = "SELECT id, name, category, price, cost, image, description FROM menu_items WHERE 1=1"
        query_params = []
        if filter_cat_choice != "ทั้งหมด":
            query_sql += " AND category = ?"
            query_params.append(filter_cat_choice)
        if search_menu_kw:
            query_sql += " AND (name LIKE ? OR description LIKE ?)"
            kw_param = f"%{search_menu_kw}%"
            query_params.extend([kw_param, kw_param])
        
        query_sql += " ORDER BY category ASC, id ASC"
        c_mng.execute(query_sql, query_params)
        found_menus = c_mng.fetchall()

        c_mng.execute("SELECT COUNT(*), AVG(price), AVG(cost) FROM menu_items")
        tot_cnt, avg_p, avg_c = c_mng.fetchone()
        tot_cnt = tot_cnt or 0
        avg_p = avg_p or 0
        avg_c = avg_c or 0

        m_stat1, m_stat2, m_stat3, m_stat4 = st.columns(4)
        m_stat1.metric(" รายการทั้งหมด", f"{tot_cnt} เมนู")
        m_stat2.metric(" ตรงตามตัวกรอง", f"{len(found_menus)} เมนู")
        m_stat3.metric(" ราคาเฉลี่ย", f"฿{avg_p:,.1f}")
        m_stat4.metric(" ต้นทุนเฉลี่ย", f"฿{avg_c:,.1f}")

        st.caption(f"แสดงผล {len(found_menus)} รายการ (กดที่ปุ่ม ' ลบ' เพื่อลบเมนูที่ไม่ต้องการ)")

        if not found_menus:
            st.warning("ไม่พบรายการอาหารที่ตรงกับเงื่อนไขการค้นหา")
        else:
            for item_id, m_name, m_cat, m_price, m_cost, m_img, m_desc in found_menus:
                with st.container(border=True):
                    row_img, row_info, row_price, row_action = st.columns([1.1, 3.2, 1.8, 1.1])
                    
                    with row_img:
                        if m_img and (m_img.startswith("http") or os.path.exists(m_img)):
                            st.image(m_img, use_container_width=True)
                        else:
                            st.markdown("<div style='font-size: 2.2rem; text-align: center; line-height: 65px; background: #fff7ed; border-radius: 8px;'></div>", unsafe_allow_html=True)
                    
                    with row_info:
                        st.markdown(f"**{m_name}** <span style='font-size: 0.8rem; background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 999px; margin-left: 6px; font-weight: 600;'>{m_cat}</span>", unsafe_allow_html=True)
                        if m_desc:
                            st.caption(m_desc)
                        if m_img:
                            st.caption(f" `{m_img}`")
                    
                    with row_price:
                        st.markdown(f"ราคา: <b style='color: #ea580c; font-size: 1.1rem;'>฿{m_price:,.2f}</b>", unsafe_allow_html=True)
                        p_margin = m_price - (m_cost or 0)
                        st.caption(f"ต้นทุน: ฿{m_cost or 0:,.2f} (กำไร: ฿{p_margin:,.2f})")
                    
                    with row_action:
                        with st.popover(" ลบ", use_container_width=True):
                            st.markdown(f" **ยืนยันลบเมนู?**")
                            st.caption(f"ต้องการลบ **'{m_name}'** ออกจากระบบหรือไม่?")
                            if st.button(" ยืนยันลบ", key=f"btn_del_menu_{item_id}", type="primary", use_container_width=True):
                                try:
                                    conn_del = sqlite3.connect(DB_NAME)
                                    c_del = conn_del.cursor()
                                    c_del.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
                                    conn_del.commit()
                                    conn_del.close()
                                    st.success(f"ลบเมนู '{m_name}' เรียบร้อยแล้ว")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"เกิดข้อผิดพลาดในการลบ: {err}")

        conn_mng.close()

    # Footer ล่างสุดสำหรับหน้าระบบจัดการหลังร้าน (?mode=admin)
    render_app_footer()

# ==============================================================================
#  ฝั่งลูกค้าสั่งอาหารที่โต๊ะ (Customer Menu & Ordering View)
# ==============================================================================
# ทำงานเมื่อลูกค้าสแกน QR Code เข้ามา เช่น https://domain/?table=1
# หน้าที่หลัก:
# 1. ตรวจสอบหมายเลขโต๊ะจาก URL Query Parameter (?table=N)
# 2. แสดงรายการอาหารแยกตามหมวดหมู่ พร้อมรูปภาพและราคา
# 3. จัดการตะกร้าสินค้าแบบเรียลไทม์ (บันทึกใน st.session_state)
# 4. บันทึกคำสั่งซื้อเข้าห้องครัว (บันทึกลงตาราง orders และ order_items)
# 5. ติดตามสถานะอาหารแบบเรียลไทม์ (Auto-refresh ทุก 3 วินาที)
else:
    table_from_param = params.get("table", None)
    conn_chk = sqlite3.connect(DB_NAME)
    c_chk = conn_chk.cursor()
    c_chk.execute("SELECT table_number, name FROM tables ORDER BY table_number ASC")
    valid_tables_data = c_chk.fetchall()
    conn_chk.close()
    
    valid_tables = [row[0] for row in valid_tables_data]
    table_names_map = {row[0]: row[1] for row in valid_tables_data}

    # Header โลโก้ลูกค้า: จัดกลางเสมอ สวยงาม ชัดเจน รองรับทุกขนาดหน้าจอ
    logo_b64 = get_base64_image(logo_path)
    if logo_b64:
        logo_html = f'''<div style="text-align: center; margin-bottom: 6px;">
            <img src="data:image/png;base64,{logo_b64}" 
                 style="width: 105px; height: 105px; object-fit: cover; border-radius: 50%; box-shadow: 0 4px 16px rgba(234, 88, 12, 0.28); display: inline-block; border: 3px solid #ffedd5;" 
                 alt="โลโก้ฟ้าใสตำนัว" />
        </div>'''
    else:
        logo_html = '<div style="text-align: center; font-size: 55px; margin-bottom: 4px;"></div>'

    # กรณีทางร้านยังไม่ได้เปิดโต๊ะใดๆ (0 โต๊ะเริ่มต้น)
    if not valid_tables:
        header_html = f'''
        {logo_html}
        <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.25rem; margin: 2px 0 0 0; letter-spacing: -0.5px; line-height: 1.2;">
            ฟ้าใสตำนัว
        </h1>
        <p style="text-align: center; color: #78716c; font-size: 0.95rem; margin: 0 0 10px 0;">
            ส้มตำ ยำ ลาบ ย่าง แซ่บนัว สดใหม่ทุกครก 
        </p>
        '''
        st.markdown(header_html, unsafe_allow_html=True)
        st.write("---")
        st.warning(" ขณะนี้ทางร้านยังไม่ได้เปิดโต๊ะอาหารในระบบ")
        st.info("กรุณาติดต่อพนักงานที่เคาน์เตอร์ หรือเปิดโต๊ะในระบบหลังร้านก่อนนะคะ ")
        
        col_adm1, col_adm2, col_adm3 = st.columns([1, 2, 1])
        with col_adm2:
            if st.button(" ไปที่ระบบจัดการหลังร้าน (Admin)", type="primary", use_container_width=True):
                st.query_params["mode"] = "admin"
                st.rerun()
            st.markdown("<div style='text-align: center; margin-top: 8px;'><a href='/?mode=admin' target='_top' style='color: #ea580c; text-decoration: underline; font-weight: bold; font-size: 14px;'>หรือคลิกที่นี่หากปุ่มไม่ตอบสนอง</a></div>", unsafe_allow_html=True)
        st.stop()
        valid_tables = [1]

    # กำหนดหมายเลขโต๊ะปัจจุบัน (หาก URL ไม่ได้ระบุ ให้เลือกโต๊ะแรกในระบบ)
    current_table_num = None
    if table_from_param is not None:
        try:
            p_val = int(table_from_param)
            if p_val in valid_tables:
                current_table_num = p_val
        except:
            pass
            
    if current_table_num is None:
        current_table_num = valid_tables[0]
        
    current_table_name = table_names_map.get(current_table_num, f"โต๊ะที่ {current_table_num}")

    # ==========================================================================
    #  ข้อมูลสมาชิกที่เข้าสู่ระบบอยู่ (เก็บใน Session State แยกตามโต๊ะ)
    # ==========================================================================
    mem_tbl_key = f"member_phone_table_{current_table_num}"
    mem_obj_key = f"member_obj_{current_table_num}"
    current_member = st.session_state.get(mem_obj_key)
    if current_member:
        # ดึงคะแนนล่าสุดจากฐานข้อมูลทุกครั้ง (คะแนนอาจเปลี่ยนหลังเช็คบิล)
        conn_m = sqlite3.connect(DB_NAME)
        c_m = conn_m.cursor()
        c_m.execute("SELECT id, first_name, last_name, phone, points FROM members WHERE phone = ?", (current_member['phone'],))
        m_row = c_m.fetchone()
        conn_m.close()
        if m_row:
            current_member = {'id': m_row[0], 'first_name': m_row[1], 'last_name': m_row[2], 'phone': m_row[3], 'points': m_row[4]}
            st.session_state[mem_obj_key] = current_member
        else:
            current_member = None
            st.session_state[mem_obj_key] = None

    # ==========================================================================
    #  ฟังก์ชันจัดการตะกร้าสินค้า (Cart Callbacks)
    # ==========================================================================
    # เก็บข้อมูลใน st.session_state.cart เพื่อไม่ให้หายเวลากดเพิ่ม/ลดรายการ
    # โครงสร้าง: { 'ชื่ออาหาร': {'price': ราคา, 'qty': จำนวน, 'note': โน้ตพิเศษ} }

    def add_to_cart_item(item_name, item_price):
        """เพิ่มจำนวนอาหารในตะกร้า (+1) หรือเพิ่มรายการใหม่ลงตะกร้า"""
        if 'cart' not in st.session_state:
            st.session_state.cart = {}
        if item_name in st.session_state.cart:
            st.session_state.cart[item_name]['qty'] += 1
        else:
            st.session_state.cart[item_name] = {'price': item_price, 'qty': 1, 'note': ''}

    def dec_from_cart_item(item_name):
        """ลดจำนวนอาหารในตะกร้า (-1) หากเหลือ 0 จะลบรายการออกอัตโนมัติ"""
        if 'cart' in st.session_state and item_name in st.session_state.cart:
            if st.session_state.cart[item_name]['qty'] > 1:
                st.session_state.cart[item_name]['qty'] -= 1
            else:
                del st.session_state.cart[item_name]

    def del_from_cart_item(item_name):
        """ลบรายการอาหารชิ้นนั้นออกจากตะกร้าทันที"""
        if 'cart' in st.session_state and item_name in st.session_state.cart:
            del st.session_state.cart[item_name]

    if 'cart' not in st.session_state:
        st.session_state.cart = {}

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, category, price, image, description 
        FROM menu_items 
        ORDER BY 
            CASE category 
                WHEN 'ตำนัว' THEN 1 
                WHEN 'ตำพรีเมียม' THEN 2 
                WHEN 'ยำแซ่บ' THEN 3 
                WHEN 'ลาบ & ก้อย & น้ำตก' THEN 4 
                WHEN 'ย่าง & ทอด' THEN 5 
                WHEN 'ต้มแซ่บ & แกงอีสาน' THEN 6 
                WHEN 'อาหารจานเดียว' THEN 7 
                WHEN 'ของหวาน' THEN 8 
                WHEN 'เครื่องเคียง & ข้าว' THEN 9 
                WHEN 'เครื่องดื่ม' THEN 10 
                ELSE 11 
            END, id ASC
    ''')
    all_menus = c.fetchall()

    cat_order_list = [
        "ตำนัว", 
        "ตำพรีเมียม", 
        "ยำแซ่บ", 
        "ลาบ & ก้อย & น้ำตก", 
        "ย่าง & ทอด", 
        "ต้มแซ่บ & แกงอีสาน", 
        "อาหารจานเดียว", 
        "ของหวาน", 
        "เครื่องเคียง & ข้าว", 
        "เครื่องดื่ม"
    ]

    available_cats = list(set(m[2] for m in all_menus))
    categories = [cat for cat in cat_order_list if cat in available_cats]
    for cat in available_cats:
        if cat not in categories:
            categories.append(cat)

    # คำนวณยอดตะกร้า (ใช้แสดงตัวเลขบนไอคอนตะกร้าที่แถบด้านบน)
    total_cart_qty = sum(item['qty'] for item in st.session_state.cart.values())
    total_cart_sum = sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

    # ดึงออเดอร์ของโต๊ะนี้ที่ยังไม่ปิดบิล เพื่อแสดงในปุ่มแจ้งเตือน (สถานะอาหาร)
    c.execute("""
        SELECT id, status, total_price, created_at FROM orders
        WHERE table_id = ? AND status NOT IN ('paid', 'archived')
        ORDER BY id DESC
    """, (current_table_num,))
    notif_orders = c.fetchall()
    notif_count = len(notif_orders)

    # ==========================================================================
    #  เนื้อหาภายในตะกร้าอาหาร (แสดงเมื่อกดไอคอนตะกร้าที่แถบด้านบน)
    # ==========================================================================
    def render_cart_body():
        st.markdown(f"###  ตะกร้าอาหาร ({current_table_name})")
        if total_cart_qty == 0:
            st.info("ยังไม่มีอาหารในตะกร้า เลือกเมนูด้านล่างแล้วกด  เพิ่ม ได้เลยค่ะ ")
            return
        for item_name, data in list(st.session_state.cart.items()):
            subtotal = data['price'] * data['qty']
            with st.container():
                st.markdown(f"**{item_name}** • <span style='color: #ea580c; font-weight: 600;'>฿{int(data['price'])} / จาน</span>", unsafe_allow_html=True)

                # แถวปุ่มปรับจำนวน:  | ตัวเลขจำนวน |  |  ลบ
                c_minus, c_num, c_plus, c_del = st.columns([1, 1.2, 1, 1.2])
                with c_minus:
                    st.button("", key=f"cart_dec_{item_name}", on_click=dec_from_cart_item, args=(item_name,), use_container_width=True)
                with c_num:
                    st.markdown(f"<div style='text-align: center; font-size: 1.25rem; font-weight: 700; line-height: 42px; background: #fff7ed; border-radius: 6px; border: 1.5px solid #fdba74; color: #c2410c;'>{data['qty']}</div>", unsafe_allow_html=True)
                with c_plus:
                    st.button("", key=f"cart_inc_{item_name}", on_click=add_to_cart_item, args=(item_name, data['price']), use_container_width=True)
                with c_del:
                    st.button(" ลบ", key=f"cart_rem_{item_name}", on_click=del_from_cart_item, args=(item_name,), use_container_width=True)

                st.caption(f"รวมย่อย: ฿{int(subtotal):,}")
                note = st.text_input("โน้ตพิเศษ (เช่น เผ็ดน้อย/ไม่ใส่ชูรส):", value=data['note'], key=f"cart_note_{item_name}", placeholder="ระบุความต้องการ...")
                st.session_state.cart[item_name]['note'] = note
                st.write("---")

        discount_val = 0
        points_used_val = 0

        if current_member:
            m_pts = current_member['points']
            # กฎ:
            # 1. ทุก ๆ 10 คะแนน สามารถแลกเป็นส่วนลด 25 บาท
            # 2. ผู้ใช้ต้องแลกเป็นจำนวนชุดของ 10 คะแนนเท่านั้น (10, 20, 30...)
            # 3. ส่วนลดที่ได้รับต้องไม่เกินยอดราคาที่ต้องชำระจริง
            max_sets_by_pts = m_pts // 10
            max_sets_by_bill = int(total_cart_sum // 25)
            max_sets = min(max_sets_by_pts, max_sets_by_bill)

            if max_sets >= 1:
                st.markdown("#####  ใช้คะแนนสะสมแลกส่วนลด")
                st.caption(f"แต้มสะสมที่คุณมี: **{m_pts:,}** คะแนน (แลกได้ชุดละ 10 คะแนน = 25 บาท)")
                redeem_options = [s * 10 for s in range(max_sets + 1)]
                sel_pts_to_use = st.selectbox(
                    "เลือกจำนวนคะแนนที่ต้องการใช้แลกส่วนลด:",
                    options=redeem_options,
                    format_func=lambda x: "ไม่ใช้คะแนน" if x == 0 else f"ใช้ {x} คะแนน (ส่วนลด ฿{(x // 10) * 25:,})",
                    key=f"sel_redeem_pts_{current_table_num}"
                )
                points_used_val = sel_pts_to_use
                discount_val = (sel_pts_to_use // 10) * 25
            elif m_pts > 0:
                st.caption(f" คุณมีคะแนนสะสม **{m_pts}** คะแนน (สะสมครบ 10 คะแนนเพื่อแลกส่วนลด 25 บาท)")
        else:
            st.caption(" สมัครสมาชิก / เข้าสู่ระบบ ที่แถบด้านบน เพื่อสะสมแต้มและแลกส่วนลดได้ค่ะ")

        net_cart_sum = max(0, total_cart_sum - discount_val)
        points_to_earn = int(net_cart_sum // 100)

        st.write("---")
        st.markdown(f"**ยอดรวมสินค้า:** ฿{int(total_cart_sum):,}")
        if discount_val > 0:
            st.markdown(f"**ส่วนลดจากคะแนน ({points_used_val} แต้ม):** :green[-฿{int(discount_val):,}]")
        st.markdown(f"#### ยอดชำระสุทธิ: <span style='color: #ea580c;'>฿{int(net_cart_sum):,}</span>", unsafe_allow_html=True)

        if current_member:
            st.caption(f" เมื่อชำระบิลนี้ คุณจะได้รับแต้มสะสมเพิ่ม: **+{points_to_earn}** คะแนน (ทุก 100 บาท = 1 คะแนน)")

        if st.button(" ยืนยันส่งออเดอร์เข้าครัว", type="primary", use_container_width=True):
            order_time_th = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
            m_phone_to_save = current_member['phone'] if current_member else None
            c.execute("""
                INSERT INTO orders (table_id, status, subtotal, discount, total_price, points_used, points_earned, member_phone, created_at) 
                VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?)
            """, (current_table_num, total_cart_sum, discount_val, net_cart_sum, points_used_val, points_to_earn, m_phone_to_save, order_time_th))
            new_order_id = c.lastrowid
            for iname, idata in st.session_state.cart.items():
                c.execute("INSERT INTO order_items (order_id, item_name, price, quantity, note, status) VALUES (?, ?, ?, ?, ?, 'pending')", (new_order_id, iname, idata['price'], idata['qty'], idata['note']))
            c.execute("UPDATE tables SET status = 'busy' WHERE table_number = ?", (current_table_num,))
            conn.commit()
            st.session_state.cart = {}
            st.toast(f" ส่งออเดอร์ #{new_order_id} เข้าครัวเรียบร้อยแล้วค่ะ!", icon="")
            st.rerun()

    # ==========================================================================
    #  เนื้อหาภายในปุ่มแจ้งเตือน (สถานะอาหารของโต๊ะนี้ แสดงแบบละเอียดและเรียลไทม์)
    # ==========================================================================
    def render_notif_body():
        st.markdown(f"###  ติดตามสถานะอาหาร ({current_table_name})")
        conn_trk = sqlite3.connect(DB_NAME)
        c_trk = conn_trk.cursor()
        c_trk.execute("""
            SELECT id, status, total_price, created_at 
            FROM orders 
            WHERE table_id = ? AND status != 'archived'
            ORDER BY id DESC LIMIT 5
        """, (current_table_num,))
        cur_orders = c_trk.fetchall()

        if not cur_orders:
            st.info("ยังไม่มีรายการอาหารที่สั่งในขณะนี้ค่ะ สามารถเลือกเมนูแล้วสั่งเข้าครัวได้เลยนะคะ ")
            conn_trk.close()
            return

        st_map = {
            'pending': (' รอร้านรับออเดอร์', 'orange', 0.25, 'กำลังส่งออเดอร์เข้าจอครัว...'),
            'accepted': (' ครัวกำลังปรุงอาหาร', 'blue', 0.50, 'แม่ครัวกำลังตั้งกระทะ ปรุงสดใหม่ค่ะ'),
            'cooked': (' ปรุงเสร็จ กำลังทยอยเสิร์ฟ', 'purple', 0.75, 'อาหารปรุงเสร็จแล้ว พนักงานกำลังยกไปเสิร์ฟค่ะ'),
            'served': (' เสิร์ฟถึงโต๊ะครบแล้ว', 'green', 1.0, 'เสิร์ฟครบทุกเมนูแล้ว ทานให้อร่อยแซ่บนัวนะคะ!'),
            'paid': (' เช็คบิลเรียบร้อยแล้ว', 'gray', 1.0, 'ขอบคุณที่มาอุดหนุนฟ้าใสตำนัวนะคะ ')
        }

        for oid, status, total, otime in cur_orders:
            c_trk.execute("SELECT item_name, quantity, note, COALESCE(status, 'pending') FROM order_items WHERE order_id = ?", (oid,))
            order_items_trk = c_trk.fetchall()
            
            total_it = len(order_items_trk)
            served_it = sum(1 for it in order_items_trk if it[3] == 'served')
            
            if status == 'paid':
                prog_val = 1.0
                label, color, _, desc_status = st_map['paid']
            elif status == 'served' or (total_it > 0 and served_it == total_it):
                prog_val = 1.0
                label, color, _, desc_status = st_map['served']
            elif served_it > 0:
                prog_val = 0.5 + 0.4 * (served_it / total_it)
                label, color, _, desc_status = (f' กำลังทยอยเสิร์ฟ ({served_it}/{total_it})', 'purple', prog_val, 'พนักงานกำลังยกอาหารมาเสิร์ฟที่โต๊ะค่ะ')
            elif status == 'cooked':
                prog_val = 0.65
                label, color, _, desc_status = st_map['cooked']
            elif status == 'accepted':
                prog_val = 0.45
                label, color, _, desc_status = st_map['accepted']
            else:
                prog_val = 0.25
                label, color, _, desc_status = st_map['pending']

            with st.container(border=True):
                c_oh1, c_oh2 = st.columns([2.5, 1])
                with c_oh1:
                    st.markdown(f"**ออเดอร์ #{oid}** — <span style='font-size: 0.95rem; font-weight: bold;'>:{color}[{label}]</span>", unsafe_allow_html=True)
                    st.caption(f" {desc_status} • สั่งเมื่อ {otime}")
                with c_oh2:
                    st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 1.05rem; color: #ea580c;'>฿{int(total):,}</div>", unsafe_allow_html=True)
                
                st.progress(prog_val)
                
                with st.expander(" ดูรายการอาหาร & สถานะแต่ละจาน", expanded=(status != 'paid')):
                    for iname, iqty, inote, ist in order_items_trk:
                        note_text = f" *(โน้ต: {inote})*" if inote else ""
                        if ist == 'served':
                            st_badge = ":green[**[ เสิร์ฟแล้ว]**]"
                        elif ist == 'cooked':
                            st_badge = ":purple[**[ ปรุงเสร็จแล้ว]**]"
                        else:
                            st_badge = ":orange[**[ กำลังปรุง]**]"
                        st.markdown(f"• **{iname}** x{iqty}{note_text} — {st_badge}")
                
                if status != 'paid':
                    with st.expander(" สแกน QR ชำระเงิน (PromptPay / ธนาคาร)", expanded=(status == 'served')):
                        p_img = "static/payment.jpg" if os.path.exists("static/payment.jpg") else "static/img/payment.jpg"
                        if os.path.exists(p_img):
                            st.image(p_img, caption=f"สแกนชำระเงินยอด ฿{int(total):,} (บิล #{oid})", width=200)
                            st.caption(" เมื่อสแกนชำระเงินเรียบร้อยแล้ว แจ้งพนักงานเพื่อเช็คบิลได้เลยนะคะ ")
        conn_trk.close()

    # ==========================================================================
    #  เนื้อหาภายในปุ่มสมัครสมาชิก / เข้าสู่ระบบ
    # ==========================================================================
    def render_member_body():
        if current_member:
            st.markdown(f"###  คุณ{current_member['first_name']} {current_member['last_name']}")
            st.markdown(f" เบอร์โทร: **{current_member['phone']}**")
            st.markdown(f" คะแนนสะสม: <span style='color: #ea580c; font-weight: 800; font-size: 1.2rem;'>{current_member['points']:,}</span> คะแนน", unsafe_allow_html=True)
            if current_member['points'] >= 10:
                st.caption(f" ใช้คะแนนแลกส่วนลดได้สูงสุด ฿{(current_member['points'] // 10) * 25:,} (เลือกใช้ได้ในตะกร้าอาหาร)")
            else:
                st.caption(f" สะสมเพิ่มอีก {10 - current_member['points']} คะแนน เพื่อแลกส่วนลด 25 บาท")
            if st.button(" ออกจากระบบสมาชิก", key=f"btn_mem_logout_{current_table_num}", use_container_width=True):
                st.session_state[mem_obj_key] = None
                st.session_state[mem_tbl_key] = ""
                st.rerun()
            return

        st.caption("สะสมแต้มทุก 100 บาท = 1 คะแนน • แลก 10 คะแนน = ส่วนลด 25 บาท")
        tab_login, tab_reg = st.tabs([" เข้าสู่ระบบ", " สมัครสมาชิก"])
        with tab_login:
            with st.form(f"form_mem_login_{current_table_num}"):
                lg_phone = st.text_input("หมายเลขโทรศัพท์:", placeholder="เช่น 0812345678")
                if st.form_submit_button(" เข้าสู่ระบบ", type="primary", use_container_width=True):
                    lg_clean = lg_phone.strip().replace("-", "").replace(" ", "")
                    conn_lg = sqlite3.connect(DB_NAME)
                    c_lg = conn_lg.cursor()
                    c_lg.execute("SELECT id, first_name, last_name, phone, points FROM members WHERE phone = ?", (lg_clean,))
                    lg_row = c_lg.fetchone()
                    conn_lg.close()
                    if not lg_clean:
                        st.error("กรุณากรอกหมายเลขโทรศัพท์ค่ะ")
                    elif not lg_row:
                        st.error("ไม่พบหมายเลขนี้ในระบบ กรุณาสมัครสมาชิกที่แท็บ 'สมัครสมาชิก' ค่ะ")
                    else:
                        st.session_state[mem_obj_key] = {'id': lg_row[0], 'first_name': lg_row[1], 'last_name': lg_row[2], 'phone': lg_row[3], 'points': lg_row[4]}
                        st.session_state[mem_tbl_key] = lg_clean
                        st.toast(f"ยินดีต้อนรับคุณ{lg_row[1]} ค่ะ!  {lg_row[4]:,} คะแนน", icon="")
                        st.rerun()
        with tab_reg:
            with st.form(f"form_mem_reg_{current_table_num}"):
                rg_fname = st.text_input("ชื่อ:", placeholder="ระบุชื่อจริง")
                rg_lname = st.text_input("นามสกุล:", placeholder="ระบุนามสกุล")
                rg_phone = st.text_input("หมายเลขโทรศัพท์:", placeholder="เช่น 0812345678")
                if st.form_submit_button(" ยืนยันสมัครสมาชิก", type="primary", use_container_width=True):
                    rg_clean = rg_phone.strip().replace("-", "").replace(" ", "")
                    if not rg_fname.strip() or not rg_lname.strip() or not rg_clean:
                        st.error("กรุณากรอกชื่อ นามสกุล และหมายเลขโทรศัพท์ให้ครบถ้วนค่ะ")
                    elif not rg_clean.isdigit() or len(rg_clean) not in (9, 10):
                        st.error("หมายเลขโทรศัพท์ต้องเป็นตัวเลข 9–10 หลักค่ะ")
                    else:
                        conn_rg = sqlite3.connect(DB_NAME)
                        c_rg = conn_rg.cursor()
                        c_rg.execute("SELECT id FROM members WHERE phone = ?", (rg_clean,))
                        if c_rg.fetchone():
                            conn_rg.close()
                            st.error("หมายเลขนี้เป็นสมาชิกอยู่แล้ว กรุณาเข้าสู่ระบบที่แท็บ 'เข้าสู่ระบบ' ค่ะ")
                        else:
                            reg_time = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                            c_rg.execute(
                                "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, 0, ?)",
                                (rg_fname.strip(), rg_lname.strip(), rg_clean, reg_time)
                            )
                            conn_rg.commit()
                            new_mid = c_rg.lastrowid
                            conn_rg.close()
                            st.session_state[mem_obj_key] = {'id': new_mid, 'first_name': rg_fname.strip(), 'last_name': rg_lname.strip(), 'phone': rg_clean, 'points': 0}
                            st.session_state[mem_tbl_key] = rg_clean
                            st.toast(f" สมัครสมาชิกสำเร็จ! ยินดีต้อนรับคุณ{rg_fname.strip()} ค่ะ", icon="")
                            st.rerun()

    # ==========================================================================
    #  แถบเมนูด้านบนของหน้าโต๊ะลูกค้า (Header Bar สไตล์ร้านค้าออนไลน์)
    # ==========================================================================
    # แถวบน : ติดตามเราบน Facebook / Instagram / LINE |  แจ้งเตือน |  สมัครสมาชิก / เข้าสู่ระบบ
    # แถวกลาง: โลโก้ร้าน | ช่องค้นหาเมนูอาหาร |  ตะกร้า (มีตัวเลขจำนวนจานเล็กๆ)
    # แถวล่าง: วัน เดือน ปี (พ.ศ.) | ชื่อโต๊ะ | ปุ่มเปลี่ยนโต๊ะ
    #  แก้ไขลิงก์โซเชียลของร้านได้ที่ตัวแปร SOCIAL_LINKS ด้านล่างนี้
    SOCIAL_LINKS = {
        "facebook": "https://www.facebook.com/",
        "instagram": "https://www.instagram.com/",
        "line": "https://line.me/",
    }

    thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                   "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now_th = get_thai_now()
    thai_date_str = f"วัน{thai_days[now_th.weekday()]}ที่ {now_th.day} {thai_months[now_th.month - 1]} พ.ศ. {now_th.year + 543}"

    st.markdown("""
    <style>
    .st-key-cust_header {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%);
        border-radius: 14px;
        padding: 10px 18px 12px 18px;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.30);
        margin-bottom: 12px;
        gap: 6px !important;
    }
    .st-key-cust_header [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 10px !important;
    }
    .st-key-cust_header [data-testid="stColumn"] { min-width: 0 !important; }
    .st-key-cust_header [data-testid="stPopover"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
        min-height: 36px !important;
        padding: 4px 8px !important;
    }
    .st-key-cust_header [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.18) !important;
    }
    .st-key-cust_header [data-testid="stPopover"] button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    .st-key-cart_wrap [data-testid="stPopover"] button p { font-size: 30px !important; line-height: 1 !important; }
    .st-key-cust_header [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #1c1917 !important;
        height: 44px !important;
        font-size: 15px !important;
    }
    .st-key-cust_header [data-testid="stTextInput"] > div > div {
        border: 2px solid #ffffff !important;
        border-radius: 4px !important;
    }
    .hdr-social { color: #ffffff; font-size: 14px; display: flex; align-items: center; gap: 8px; white-space: nowrap; }
    .hdr-social a { display: inline-flex; align-items: center; }
    .hdr-social img { width: 18px !important; height: 18px !important; border-radius: 0 !important; }
    .hdr-logo { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
    .hdr-logo img { width: 54px !important; height: 54px !important; border-radius: 50% !important; border: 2px solid #ffffff; background: #ffffff; }
    .hdr-logo .hdr-name { color: #ffffff; font-size: 1.45rem; font-weight: 800; line-height: 1.1; }
    .hdr-logo .hdr-tag { color: #ffedd5; font-size: 0.78rem; }
    .hdr-date { color: #ffffff; font-size: 0.9rem; white-space: nowrap; }
    .hdr-table { display: inline-block; background: #ffffff; color: #c2410c; font-weight: 800; padding: 3px 14px; border-radius: 999px; font-size: 0.95rem; white-space: nowrap; }
    .hdr-badge {
        display: inline-block; background: #ffffff; color: #ea580c;
        border: 1.5px solid #ea580c; border-radius: 999px;
        font-size: 11px; font-weight: 800; line-height: 1; padding: 2px 6px;
    }
    .st-key-cart_wrap, .st-key-notif_wrap { position: relative; }
    .st-key-cart_wrap [data-testid="stElementContainer"]:has(.hdr-badge) {
        position: absolute !important; top: -4px; right: 18%; width: auto !important; z-index: 10; pointer-events: none;
    }
    .st-key-notif_wrap [data-testid="stElementContainer"]:has(.hdr-badge) {
        position: absolute !important; top: -6px; left: 14px; width: auto !important; z-index: 10; pointer-events: none;
    }
    @media (max-width: 640px) {
        .st-key-cust_header { padding: 8px 10px 10px 10px; }
        .hdr-social .hdr-follow, .hdr-logo .hdr-tag { display: none; }
        .hdr-logo img { width: 40px !important; height: 40px !important; }
        .hdr-logo .hdr-name { font-size: 1.05rem; }
        .st-key-cust_header [data-testid="stPopover"] button p { font-size: 12px !important; }
        .st-key-cart_wrap [data-testid="stPopover"] button p { font-size: 24px !important; }
        .hdr-date { font-size: 0.75rem; white-space: normal; }
    }
    </style>
    """, unsafe_allow_html=True)

    if logo_b64:
        hdr_logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="โลโก้ฟ้าใสตำนัว" />'
    else:
        hdr_logo_img = '<span style="font-size: 40px;"></span>'

    with st.container(key="cust_header"):
        # ---------- แถวบน: โซเชียล | แจ้งเตือน | สมัครสมาชิก / เข้าสู่ระบบ ----------
        r1_social, r1_notif, r1_member = st.columns([3, 1.3, 2])
        with r1_social:
            st.markdown(f"""
            <div class="hdr-social">
                <span class="hdr-follow">ติดตามเราบน</span>
                <a href="{SOCIAL_LINKS['facebook']}" target="_blank" title="Facebook"><img src="https://cdn.simpleicons.org/facebook/ffffff" alt="Facebook" /></a>
                <a href="{SOCIAL_LINKS['instagram']}" target="_blank" title="Instagram"><img src="https://cdn.simpleicons.org/instagram/ffffff" alt="Instagram" /></a>
                <a href="{SOCIAL_LINKS['line']}" target="_blank" title="LINE"><img src="https://cdn.simpleicons.org/line/ffffff" alt="LINE" /></a>
            </div>
            """, unsafe_allow_html=True)
        with r1_notif:
            with st.container(key="notif_wrap"):
                with st.popover(" แจ้งเตือน", use_container_width=True):
                    render_notif_body()
                if notif_count > 0:
                    st.markdown(f'<span class="hdr-badge">{notif_count if notif_count < 10 else "9+"}</span>', unsafe_allow_html=True)
        with r1_member:
            if current_member:
                member_label = f" คุณ{current_member['first_name']} {current_member['points']:,}"
            else:
                member_label = " สมัครสมาชิก / เข้าสู่ระบบ"
            with st.popover(member_label, use_container_width=True):
                render_member_body()

        # ---------- แถวกลาง: โลโก้ | ช่องค้นหา | ตะกร้า ----------
        r2_logo, r2_search, r2_cart = st.columns([2, 5, 1])
        with r2_logo:
            st.markdown(f"""
            <div class="hdr-logo">
                {hdr_logo_img}
                <div>
                    <div class="hdr-name">ฟ้าใสตำนัว</div>
                    <div class="hdr-tag">ส้มตำ ยำ ลาบ ย่าง แซ่บนัว</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with r2_search:
            search_kw = st.text_input(
                "ค้นหาเมนูอาหาร",
                placeholder=" ค้นหาเมนู เช่น ตำปู, ลาบหมู, คอหมูย่าง",
                key="cust_search_kw",
                label_visibility="collapsed"
            ).strip()
        with r2_cart:
            with st.container(key="cart_wrap"):
                with st.popover("", use_container_width=True):
                    render_cart_body()
                if total_cart_qty > 0:
                    st.markdown(f'<span class="hdr-badge">{total_cart_qty if total_cart_qty < 100 else "99+"}</span>', unsafe_allow_html=True)

        # ---------- แถวล่าง: วัน เดือน ปี | ชื่อโต๊ะ | เปลี่ยนโต๊ะ ----------
        r3_date, r3_table, r3_switch = st.columns([3, 1.3, 1.5])
        with r3_date:
            st.markdown(f'<div class="hdr-date"> {thai_date_str}</div>', unsafe_allow_html=True)
        with r3_table:
            st.markdown(f'<div style="text-align: right;"><span class="hdr-table"> {current_table_name}</span></div>', unsafe_allow_html=True)
        with r3_switch:
            # ปุ่มสลับ / เปลี่ยนโต๊ะอาหาร (สำหรับกรณีทดสอบโต๊ะอื่นๆ หรือลูกค้าเดินเข้าร้านเลือกโต๊ะเอง)
            with st.popover(" เปลี่ยนโต๊ะ", use_container_width=True):
                st.markdown("#####  เลือกโต๊ะอาหารที่ท่านนั่ง")
                st.caption("สามารถเลือกหมายเลขโต๊ะเพื่อสั่งอาหารของโต๊ะนั้นๆ ได้เลยค่ะ")
                table_select_options = [f"โต๊ะที่ {num} ({table_names_map.get(num, f'โต๊ะที่ {num}')})" for num in valid_tables]
                curr_idx = valid_tables.index(current_table_num) if current_table_num in valid_tables else 0
                sel_new_t = st.selectbox("เลือกโต๊ะ:", table_select_options, index=curr_idx, key="sb_switch_table")
                if st.button(" ยืนยันเปลี่ยนโต๊ะ", type="primary", use_container_width=True, key="btn_confirm_switch_t"):
                    chosen_num = int(sel_new_t.split(" ")[1])
                    st.query_params["table"] = chosen_num
                    st.rerun()

    # ==========================================================================
    #  เลือกหมวดหมู่อาหาร / ผลการค้นหา
    # ==========================================================================
    st.markdown("<p style='text-align: center; font-weight: 600; color: #44403c; margin-bottom: 4px; font-size: 1.05rem;'> เลือกหมวดหมู่อาหาร</p>", unsafe_allow_html=True)
    default_cat = categories[0] if categories else "ทั้งหมด"
    sel_cat = st.pills("เลือกหมวดหมู่อาหาร:", categories + ["ทั้งหมด"], default=default_cat, key="pills_cat_sel", label_visibility="collapsed")
    if not sel_cat:
        sel_cat = default_cat

    # แสดงรายการเมนูอาหาร แถวการ์ดแนวนอน (กดได้ทุกรายการ พร้อม Stepper / บนการ์ดโดยตรง)
    # หากลูกค้าพิมพ์คำค้นหา จะค้นจากทุกหมวดหมู่ (ทั้งชื่อเมนูและคำอธิบาย)
    if search_kw:
        kw_low = search_kw.lower()
        filtered_menus = [m for m in all_menus if kw_low in (m[1] or "").lower() or kw_low in (m[5] or "").lower()]
        st.markdown(f"<div style='color: #57534e; margin-bottom: 8px;'> ผลการค้นหา <b>\"{search_kw}\"</b> พบ <b style='color: #ea580c;'>{len(filtered_menus)}</b> รายการ (ค้นหาจากทุกหมวดหมู่)</div>", unsafe_allow_html=True)
        if not filtered_menus:
            st.warning("ไม่พบเมนูที่ค้นหา ลองพิมพ์คำอื่น หรือเลือกจากหมวดหมู่ด้านบนค่ะ")
    else:
        filtered_menus = all_menus if sel_cat == "ทั้งหมด" else [m for m in all_menus if m[2] == sel_cat]
    
    # แสดงรายการเมนูอาหารแบบ Responsive Flex Grid ชิดกัน เว้นระยะห่างเล็กน้อย จำนวนตามความกว้างหน้าจอของแต่ละอุปกรณ์
    grid_container = st.container(horizontal=True, wrap=True, gap=10, key="menu_grid_flex")
    with grid_container:
        for m_id, name, cat, price, img, desc in filtered_menus:
            with st.container(border=True, key=f"fcard_{m_id}", width=124):
                st.markdown("<div class='fcard-marker' style='display:none;'></div>", unsafe_allow_html=True)
                # รูปภาพอาหารขนาดกะทัดรัด (สูงประมาณ 104px กว้าง 112px ขนาดพอดีเป๊ะ)
                if img and (img.startswith("http") or os.path.exists(img)):
                    st.image(img, width=112)
                else:
                    st.markdown("<div class='no-img-box'></div>", unsafe_allow_html=True)
                
                # ชื่ออาหาร & หมวดหมู่
                st.markdown(f"<div style='font-size: 0.92rem; font-weight: 700; color: #1c1917; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;' title='{name}'>{name}</div>", unsafe_allow_html=True)
                
                # ราคาอาหารแบบ Pill สดใส
                st.markdown(f"<div style='margin: 2px 0 6px 0; width: 100%;'><span style='color: #ea580c; font-weight: 800; font-size: 1.05rem;'>฿{int(price)}</span> <span style='font-size: 0.72rem; color: #78716c;'>/จาน</span></div>", unsafe_allow_html=True)
                
                # ปุ่ม เพิ่ม / ปรับจำนวน (Stepper)
                cur_qty = st.session_state.cart.get(name, {}).get('qty', 0)
                if cur_qty == 0:
                    st.button(" เพิ่ม", key=f"btn_add_menu_{m_id}", on_click=add_to_cart_item, args=(name, price), width=112, type="primary")
                else:
                    c_m, c_q, c_p = st.columns([1, 1.2, 1], gap="small")
                    with c_m:
                        st.button("", key=f"btn_dec_card_{m_id}", on_click=dec_from_cart_item, args=(name,), use_container_width=True)
                    with c_q:
                        st.markdown(f"<div style='text-align: center; font-weight: 800; line-height: 34px; color: #ffffff; font-size: 0.95rem; background: linear-gradient(135deg, #ea580c, #dc2626); border-radius: 8px; box-shadow: 0 2px 6px rgba(234, 88, 12, 0.30);'>{cur_qty}</div>", unsafe_allow_html=True)
                    with c_p:
                        st.button("", key=f"btn_inc_card_{m_id}", on_click=add_to_cart_item, args=(name, price), use_container_width=True, type="primary")

    conn.close()

    # Footer ล่างสุดสำหรับฝั่งลูกค้า
    render_app_footer()

