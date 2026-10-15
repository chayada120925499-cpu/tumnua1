# ==============================================================================
# ฟ้าใสตำนัว (Fahsai Tum Nua) - ระบบสั่งอาหารโต๊ะ & จอครัวอัจฉริยะ (Smart POS)
# ==============================================================================
# ไฟล์หลัก (Main Entry Point) ควบคุมการกำหนดค่า Routing และ Session ของระบบ
# ==============================================================================

import os
import streamlit as st
from config import apply_custom_css
from database import init_db
from views.admin import render_admin_view
from views.customer_view import render_customer_view

# --- 1. ตั้งค่าหน้าเว็บเบื้องต้น ---
st.set_page_config(
    page_title="ฟ้าใสตำนัว",
    page_icon="static/img/favicon.ico" if os.path.exists("static/img/favicon.ico") else None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ใช้งาน CSS ธีมหลักของระบบ ---
apply_custom_css()

# --- 3. ตรวจสอบและเตรียมโครงสร้างฐานข้อมูล SQLite ---
init_db()

# --- 4. ตรวจสอบโหมดการแสดงผลจาก URL Query Parameters ---
# - หน้าจัดการหลังร้าน: https://domain/?mode=admin
# - หน้าร้านสั่งอาหาร:  https://domain/?table=1
params = st.query_params
raw_mode = str(params.get("mode", ""))
is_admin_mode = ("admin" in raw_mode.lower())

# ปรับคลีน URL พารามิเตอร์ไม่ให้มีค่าซ้ำซ้อน
if is_admin_mode and params.get("mode") != "admin":
    st.query_params["mode"] = "admin"

# --- 5. สลับหน้าจอตามโหมดผู้ใช้งาน ---
if is_admin_mode:
    render_admin_view()
else:
    render_customer_view()
