# ==============================================================================
# โมดูลระบบจัดการหลังร้าน (Admin POS & Backoffice Views)
# ==============================================================================
import streamlit as st
from config import render_app_footer
from views.admin.auth_view import check_admin_auth
from views.admin.table_view import render_table_tab
from views.admin.kds_pos_view import render_pos_dashboard
from views.admin.report_view import render_report_tab
from views.admin.member_view import render_member_tab
from views.admin.menu_view import render_menu_tab

def render_admin_view():
    """แสดงหน้าจอระบบจัดการหลังร้าน (5 แท็บหลัก)"""
    # 1. ตรวจสอบสิทธิ์และแสดงฟอร์มล็อกอิน / แถบผู้ใช้
    check_admin_auth()

    # CSS เฉพาะสำหรับ 5 แท็บของหลังร้าน ให้แยกสีเด่นชัดตามที่ผู้ใช้กำหนด
    st.markdown("""
    <style>
    /* ให้แถบแท็บเลื่อนแนวนอนได้อย่างลื่นไหลบนทุกขนาดหน้าจอ */
    .st-key-admin_main_tabs [data-baseweb="tab-list"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        scrollbar-width: thin !important;
        padding-bottom: 2px !important;
        gap: 6px !important;
    }

    /* 1. แท็บ - จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (สีแดง - Red) */
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1),
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5) {
        background-color: #fef2f2 !important;
        border: 1.5px solid #fecaca !important;
        border-bottom: none !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1) p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5) p {
        color: #991b1b !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1):hover,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5):hover {
        background-color: #fee2e2 !important;
        border-color: #ef4444 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1):hover p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5):hover p {
        color: #b91c1c !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1)[aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5)[aria-selected="true"] {
        background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important;
        background-color: #ef4444 !important;
        border: 1.5px solid #b91c1c !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(239, 68, 68, 0.35) !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(1)[aria-selected="true"] p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(1):nth-last-of-type(5)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 2. แท็บ - จอครัว & เคาน์เตอร์คิดเงิน (สีเขียว - Green) */
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2),
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4) {
        background-color: #f0fdf4 !important;
        border: 1.5px solid #bbf7d0 !important;
        border-bottom: none !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2) p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4) p {
        color: #166534 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2):hover,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4):hover {
        background-color: #dcfce7 !important;
        border-color: #22c55e !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2):hover p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4):hover p {
        color: #15803d !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2)[aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4)[aria-selected="true"] {
        background: linear-gradient(180deg, #10b981 0%, #059669 100%) !important;
        background-color: #10b981 !important;
        border: 1.5px solid #047857 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(16, 185, 129, 0.35) !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(2)[aria-selected="true"] p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(2):nth-last-of-type(4)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 3. แท็บ - รายงานยอดขาย (สีม่วง - Purple) */
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3),
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3) {
        background-color: #faf5ff !important;
        border: 1.5px solid #e9d5ff !important;
        border-bottom: none !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3) p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3) p {
        color: #581c87 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3):hover,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3):hover {
        background-color: #f3e8ff !important;
        border-color: #a855f7 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3):hover p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3):hover p {
        color: #7e22ce !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3)[aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3)[aria-selected="true"] {
        background: linear-gradient(180deg, #8b5cf6 0%, #7c3aed 100%) !important;
        background-color: #8b5cf6 !important;
        border: 1.5px solid #6d28d9 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(139, 92, 246, 0.35) !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(3)[aria-selected="true"] p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(3):nth-last-of-type(3)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 4. แท็บ - ประวัติลูกค้า (สีส้ม - Orange) */
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4),
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2) {
        background-color: #fff7ed !important;
        border: 1.5px solid #fed7aa !important;
        border-bottom: none !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4) p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2) p {
        color: #9a3412 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4):hover,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2):hover {
        background-color: #ffedd5 !important;
        border-color: #f97316 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4):hover p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2):hover p {
        color: #ea580c !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4)[aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2)[aria-selected="true"] {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%) !important;
        background-color: #f97316 !important;
        border: 1.5px solid #c2410c !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(249, 115, 22, 0.35) !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(4)[aria-selected="true"] p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(4):nth-last-of-type(2)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 5. แท็บ - จัดการเมนูอาหาร (สีฟ้า - Sky Blue / Cyan) */
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5),
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1) {
        background-color: #f0f9ff !important;
        border: 1.5px solid #bae6fd !important;
        border-bottom: none !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5) p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1) p {
        color: #075985 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5):hover,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1):hover {
        background-color: #e0f2fe !important;
        border-color: #0ea5e9 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5):hover p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1):hover p {
        color: #0284c7 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5)[aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1)[aria-selected="true"] {
        background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%) !important;
        background-color: #0ea5e9 !important;
        border: 1.5px solid #0369a1 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(14, 165, 233, 0.35) !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"] > button:nth-of-type(5)[aria-selected="true"] p,
    div[data-testid="stTabs"] [data-baseweb="tab-list"] > button:nth-of-type(5):nth-last-of-type(1)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* เส้นขอบใต้แท็บลิสต์เปลี่ยนสีตามแท็บที่ถูกเลือก */
    .st-key-admin_main_tabs [data-baseweb="tab-list"]:has(button:nth-of-type(1)[aria-selected="true"]),
    div[data-testid="stTabs"] [data-baseweb="tab-list"]:has(button:nth-of-type(1)[aria-selected="true"]) {
        border-bottom: 2.5px solid #dc2626 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"]:has(button:nth-of-type(2)[aria-selected="true"]),
    div[data-testid="stTabs"] [data-baseweb="tab-list"]:has(button:nth-of-type(2)[aria-selected="true"]) {
        border-bottom: 2.5px solid #059669 !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"]:has(button:nth-of-type(3)[aria-selected="true"]),
    div[data-testid="stTabs"] [data-baseweb="tab-list"]:has(button:nth-of-type(3)[aria-selected="true"]) {
        border-bottom: 2.5px solid #7c3aed !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"]:has(button:nth-of-type(4)[aria-selected="true"]),
    div[data-testid="stTabs"] [data-baseweb="tab-list"]:has(button:nth-of-type(4)[aria-selected="true"]) {
        border-bottom: 2.5px solid #ea580c !important;
    }
    .st-key-admin_main_tabs [data-baseweb="tab-list"]:has(button:nth-of-type(5)[aria-selected="true"]),
    div[data-testid="stTabs"] [data-baseweb="tab-list"]:has(button:nth-of-type(5)[aria-selected="true"]) {
        border-bottom: 2.5px solid #0284c7 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. เมนูแท็บ 5 ส่วนหลัก
    with st.container(key="admin_main_tabs"):
        tab_tbl, tab_pos, tab_rep, tab_mem, tab_menu = st.tabs([
            "จัดการโต๊ะอาหาร & เคลียร์โต๊ะ", 
            "จอครัว & เคาน์เตอร์คิดเงิน", 
            "รายงานยอดขาย",
            "ประวัติลูกค้า",
            "จัดการเมนูอาหาร"
        ])

        with tab_tbl:
            render_table_tab()

        with tab_pos:
            render_pos_dashboard()

        with tab_rep:
            render_report_tab()

        with tab_mem:
            render_member_tab()

        with tab_menu:
            render_menu_tab()

    # Footer ล่างสุด
    render_app_footer()
