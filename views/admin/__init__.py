# ==============================================================================
# 🔴 โมดูลระบบจัดการหลังร้าน (Admin POS & Backoffice Views)
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

    # 2. เมนูแท็บ 5 ส่วนหลัก
    tab_tbl, tab_pos, tab_rep, tab_mem, tab_menu = st.tabs([
        "🪑 จัดการโต๊ะอาหาร & เคลียร์โต๊ะ", 
        "🍳 จอครัว & เคาน์เตอร์คิดเงิน", 
        "📊 รายงานยอดขาย",
        "👥 ประวัติลูกค้า",
        "🍲 จัดการเมนูอาหาร"
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
