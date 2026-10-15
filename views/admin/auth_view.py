# ==============================================================================
# 🔐 ระบบยืนยันตัวตนผู้ดูแลร้าน & กู้คืนรหัสผ่าน (Admin Auth & Password Recovery)
# ==============================================================================
import os
import secrets
import sqlite3
import streamlit as st
from datetime import timedelta
from config import DB_NAME, LOGO_PATH, get_base64_image, get_thai_now, render_app_footer
from utils.auth import hash_password, verify_password
from utils.email_service import send_otp_email, is_smtp_configured

def check_admin_auth():
    """ตรวจสอบสถานะล็อกอินของผู้ดูแล หากยังไม่ล็อกอินจะแสดงฟอร์มและ st.stop()"""
    logo_path = LOGO_PATH
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
        logo_html = '<div style="text-align: center; font-size: 75px; margin-bottom: 4px;">🌶️</div>'

    # 🔒 กรณีที่ยังไม่ได้ลงชื่อเข้าใช้: แสดงฟอร์ม Login และระบบกู้คืนรหัสผ่าน
    if not st.session_state['admin_logged_in']:
        login_header_html = f'''
        {logo_html}
        <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.3rem; margin: 4px 0 2px 0; line-height: 1.2;">
            ฟ้าใสตำนัว (ระบบจัดการหลังร้าน)
        </h1>
        <p style="text-align: center; color: #78716c; font-size: 1.05rem; margin: 0 0 16px 0;">
            🔐 กรุณาลงชื่อเข้าใช้งานเพื่อเข้าถึงระบบจัดการร้าน จอครัว และเคาน์เตอร์คิดเงิน
        </p>
        '''
        st.markdown(login_header_html, unsafe_allow_html=True)
        st.write("---")

        col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
        with col_l2:
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center; color: #431407; margin-bottom: 4px;'>เข้าสู่ระบบผู้ดูแลร้าน</h3>", unsafe_allow_html=True)
                st.caption("ป้อนชื่อผู้ใช้งานและรหัสผ่านเพื่อยืนยันสิทธิ์")
                
                with st.form("admin_login_form"):
                    input_user = st.text_input("👤 ชื่อผู้ใช้ (Username):", placeholder="เช่น admin", key="inp_admin_user")
                    input_pass = st.text_input("🔑 รหัสผ่าน (Password):", type="password", placeholder="ป้อนรหัสผ่าน", key="inp_admin_pass")
                    submit_login = st.form_submit_button("🔓 ลงชื่อเข้าใช้", type="primary", use_container_width=True)

                    if submit_login:
                        if not input_user.strip() or not input_pass.strip():
                            st.error("กรุณากรอกชื่อผู้ใช้งานและรหัสผ่านให้ครบถ้วนค่ะ")
                        else:
                            conn_auth = sqlite3.connect(DB_NAME)
                            c_auth = conn_auth.cursor()
                            c_auth.execute("SELECT id, username, password_hash, salt, full_name, role, email FROM admin_users WHERE LOWER(username) = LOWER(?)", (input_user.strip(),))
                            user_record = c_auth.fetchone()
                            conn_auth.close()

                            if user_record and verify_password(input_pass.strip(), user_record[2], user_record[3]):
                                st.session_state['admin_logged_in'] = True
                                st.session_state['admin_user_info'] = {
                                    'id': user_record[0],
                                    'username': user_record[1],
                                    'full_name': user_record[4],
                                    'role': user_record[5],
                                    'email': user_record[6]
                                }
                                st.toast(f"ยินดีต้อนรับ {user_record[4]} เข้าสู่ระบบค่ะ! 🎉", icon="✅")
                                st.rerun()
                            else:
                                st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้งค่ะ")

                # ==============================================================
                # ❓ ส่วนกู้คืนรหัสผ่านผ่านอีเมลของเจ้าของร้าน (Owner Email OTP)
                # ==============================================================
                with st.expander("❓ ลืมรหัสผ่าน? (กู้คืนบัญชีผู้ดูแลผ่านอีเมล)"):
                    reset_step = st.session_state.get('reset_step', 'request_otp')

                    if reset_step == 'request_otp':
                        st.markdown("##### 📩 รับรหัส OTP ทางอีเมลของเจ้าของร้าน")
                        st.caption("ระบบจะส่งรหัส OTP 6 หลักไปยังอีเมลส่วนตัวที่เจ้าของร้านผูกไว้ เพื่อความปลอดภัยสูงสุด (ไม่มีใครสามารถเข้าถึงได้นอกจากเจ้าของอีเมล)")

                        with st.form("form_req_otp"):
                            inp_id = st.text_input("👤 ชื่อผู้ใช้ หรือ อีเมลของร้าน:", value="admin", key="inp_rec_id")
                            btn_req_otp = st.form_submit_button("📩 ส่งรหัส OTP ไปยังอีเมล", type="primary", use_container_width=True)

                            if btn_req_otp:
                                if not inp_id.strip():
                                    st.error("กรุณาระบุชื่อผู้ใช้หรืออีเมลค่ะ")
                                else:
                                    conn_otp = sqlite3.connect(DB_NAME)
                                    c_otp = conn_otp.cursor()
                                    c_otp.execute("SELECT id, username, full_name, email FROM admin_users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)", (inp_id.strip(), inp_id.strip()))
                                    user_found = c_otp.fetchone()

                                    if not user_found:
                                        st.error("❌ ไม่พบบัญชีผู้ใช้หรืออีเมลนี้ในระบบค่ะ")
                                        conn_otp.close()
                                    else:
                                        u_id, u_user, u_fname, u_email = user_found
                                        if not u_email:
                                            u_email = "owner@fahsaitumnua.com"
                                            c_otp.execute("UPDATE admin_users SET email = ? WHERE id = ?", (u_email, u_id))
                                            conn_otp.commit()

                                        # สร้างรหัส OTP 6 หลัก
                                        otp_code = f"{secrets.randbelow(900000) + 100000}"
                                        now_thai = get_thai_now()
                                        expires_at = (now_thai + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

                                        # บันทึกลงตาราง password_resets
                                        c_otp.execute("""
                                            INSERT INTO password_resets (user_id, email, otp_code, expires_at, is_used)
                                            VALUES (?, ?, ?, ?, 0)
                                        """, (u_id, u_email, otp_code, expires_at))
                                        conn_otp.commit()
                                        conn_otp.close()

                                        # ส่งอีเมล
                                        success, msg = send_otp_email(u_email, otp_code, u_fname)

                                        # พรางอีเมลเพื่อความปลอดภัย เช่น o***r@gmail.com
                                        parts = u_email.split('@')
                                        masked_email = f"{parts[0][0]}***{parts[0][-1]}@{parts[1]}" if len(parts[0]) > 2 else u_email

                                        st.session_state['reset_step'] = 'verify_otp'
                                        st.session_state['reset_uid'] = u_id
                                        st.session_state['reset_username'] = u_user
                                        st.session_state['reset_email_masked'] = masked_email

                                        if msg == "DEV_MODE":
                                            st.session_state['dev_otp'] = otp_code
                                        else:
                                            st.session_state.pop('dev_otp', None)

                                        st.rerun()

                    elif reset_step == 'verify_otp':
                        masked_e = st.session_state.get('reset_email_masked', 'อีเมลของท่าน')
                        st.markdown(f"##### 🔢 กรอกรหัส OTP และตั้งรหัสผ่านใหม่")
                        st.caption(f"ระบบส่งรหัส OTP ไปที่: **{masked_e}** เรียบร้อยแล้ว (รหัสมีอายุ 10 นาที)")

                        if 'dev_otp' in st.session_state:
                            st.info(f"💡 **[โหมดทดสอบ - ยังไม่ตั้งค่า Gmail ใน config.py]** รหัส OTP สำหรับทดสอบคือ: **`{st.session_state['dev_otp']}`**")

                        with st.form("form_verify_otp"):
                            inp_otp = st.text_input("🔢 รหัส OTP 6 หลัก:", max_chars=6, placeholder="ป้อนตัวเลข 6 หลัก", key="inp_otp_code")
                            inp_new_pw = st.text_input("🔑 รหัสผ่านใหม่ (อย่างน้อย 6 ตัวอักษร):", type="password", key="inp_new_pw_otp")
                            inp_cfm_pw = st.text_input("🔑 ยืนยันรหัสผ่านใหม่:", type="password", key="inp_cfm_pw_otp")
                            btn_sub_otp = st.form_submit_button("🔄 ยืนยันและเปลี่ยนรหัสผ่าน", type="primary", use_container_width=True)

                            if btn_sub_otp:
                                if not inp_otp.strip() or not inp_new_pw.strip():
                                    st.error("กรุณากรอกข้อมูลให้ครบถ้วนค่ะ")
                                elif len(inp_new_pw.strip()) < 6:
                                    st.error("รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษรค่ะ")
                                elif inp_new_pw.strip() != inp_cfm_pw.strip():
                                    st.error("รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกันค่ะ")
                                else:
                                    conn_v = sqlite3.connect(DB_NAME)
                                    c_v = conn_v.cursor()
                                    c_v.execute("""
                                        SELECT id FROM password_resets 
                                        WHERE user_id = ? AND otp_code = ? AND is_used = 0 
                                        AND expires_at >= ?
                                        ORDER BY id DESC LIMIT 1
                                    """, (st.session_state.get('reset_uid'), inp_otp.strip(), get_thai_now().strftime('%Y-%m-%d %H:%M:%S')))
                                    valid_otp = c_v.fetchone()

                                    if not valid_otp:
                                        st.error("❌ รหัส OTP ไม่ถูกต้อง หรือหมดอายุแล้ว กรุณาลองใหม่อีกครั้งค่ะ")
                                        conn_v.close()
                                    else:
                                        # อัปเดตรหัสผ่านใหม่
                                        new_h, new_s = hash_password(inp_new_pw.strip())
                                        c_v.execute("UPDATE admin_users SET password_hash = ?, salt = ? WHERE id = ?", (new_h, new_s, st.session_state.get('reset_uid')))
                                        c_v.execute("UPDATE password_resets SET is_used = 1 WHERE id = ?", (valid_otp[0],))
                                        conn_v.commit()
                                        conn_v.close()

                                        st.session_state['reset_step'] = 'request_otp'
                                        st.session_state.pop('dev_otp', None)
                                        st.toast("🎉 ตั้งรหัสผ่านใหม่สำเร็จเรียบร้อยแล้ว!", icon="✅")
                                        st.success("🎉 ตั้งรหัสผ่านใหม่สำเร็จเรียบร้อยแล้ว! ท่านสามารถเข้าสู่ระบบด้านบนได้ทันทีค่ะ")

                        if st.button("🔙 ขอส่งรหัสใหม่อีกครั้ง", key="btn_cancel_otp", use_container_width=True):
                            st.session_state['reset_step'] = 'request_otp'
                            st.rerun()

        render_app_footer()
        st.stop()

    # 🔓 กรณีที่ลงชื่อเข้าใช้สำเร็จแล้ว: แสดงแถบข้อมูลผู้ใช้งาน + จัดการบัญชี
    u_info = st.session_state.get('admin_user_info') or {}
    u_name = u_info.get('full_name', 'ผู้ดูแลระบบ')
    u_role = u_info.get('role', 'admin')
    u_email = u_info.get('email', 'owner@fahsaitumnua.com')

    # --------------------------------------------------------------------------
    # 🧭 แถบหัวเว็บ Admin Header Bar สไตล์โต๊ะลูกค้า (สีส้มโค้งมน 3 แถว)
    # --------------------------------------------------------------------------
    thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                   "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now_th = get_thai_now()
    thai_date_str = f"วัน{thai_days[now_th.weekday()]}ที่ {now_th.day} {thai_months[now_th.month - 1]} พ.ศ. {now_th.year + 543}"

    SOCIAL_LINKS = {
        "facebook": "https://www.facebook.com/",
        "instagram": "https://www.instagram.com/",
        "line": "https://line.me/",
    }

    # ดึงข้อมูลออเดอร์ใหม่ และสถานะโต๊ะจากฐานข้อมูล
    conn_hdr = sqlite3.connect(DB_NAME)
    c_hdr = conn_hdr.cursor()
    c_hdr.execute("SELECT COUNT(*) FROM orders WHERE status IN ('pending', 'accepted')")
    new_orders_cnt = c_hdr.fetchone()[0] or 0

    c_hdr.execute("SELECT COUNT(*) FROM tables")
    total_tables_cnt = c_hdr.fetchone()[0] or 0
    c_hdr.execute("SELECT COUNT(DISTINCT table_id) FROM orders WHERE status NOT IN ('archived', 'cancelled', 'paid')")
    occupied_tables_cnt = c_hdr.fetchone()[0] or 0
    available_tables_cnt = max(0, total_tables_cnt - occupied_tables_cnt)

    c_hdr.execute("""
        SELECT id, table_id, status, total_price, created_at 
        FROM orders 
        WHERE status IN ('pending', 'accepted') 
        ORDER BY created_at DESC LIMIT 5
    """)
    recent_active_orders = c_hdr.fetchall()
    conn_hdr.close()

    if logo_b64:
        hdr_logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="โลโก้ฟ้าใสตำนัว" />'
    else:
        hdr_logo_img = '<span style="font-size: 38px;">🌶️</span>'

    st.markdown("""
    <style>
    .st-key-admin_header {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%);
        border-radius: 14px;
        padding: 10px 18px 12px 18px;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.30);
        margin-bottom: 12px;
        gap: 6px !important;
    }
    .st-key-admin_header [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 10px !important;
    }
    .st-key-admin_header [data-testid="stColumn"] { min-width: 0 !important; }
    .st-key-admin_header [data-testid="stPopover"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
        min-height: 36px !important;
        padding: 4px 8px !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.18) !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #1c1917 !important;
        height: 44px !important;
        font-size: 15px !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] > div > div {
        border: 2px solid #ffffff !important;
        border-radius: 4px !important;
    }
    .admin-hdr-logo-hero {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 114px;
    }
    .admin-hdr-logo-hero img {
        width: 114px !important;
        height: 114px !important;
        border-radius: 50% !important;
        border: 3.5px solid #ffffff !important;
        background: #ffffff !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.22) !important;
        object-fit: cover !important;
        display: block !important;
    }
    .admin-hdr-name { color: #ffffff; font-size: 1.65rem; font-weight: 800; line-height: 1.15; }
    .admin-hdr-tag { color: #ffedd5; font-size: 0.85rem; font-weight: 600; }
    .admin-hdr-social { color: #ffffff; font-size: 13px; display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
    .admin-hdr-social a { display: inline-flex; align-items: center; }
    .admin-hdr-social img { width: 17px !important; height: 17px !important; border-radius: 0 !important; }
    .admin-hdr-date { color: #ffffff; font-size: 0.88rem; white-space: nowrap; }
    .admin-hdr-table { display: inline-block; background: #ffffff; color: #c2410c; font-weight: 800; padding: 4px 14px; border-radius: 999px; font-size: 0.92rem; white-space: nowrap; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
    .admin-hdr-badge {
        display: inline-block; background: #dc2626; color: #ffffff;
        border: 1.5px solid #ffffff; border-radius: 999px;
        font-size: 11px; font-weight: 800; line-height: 1; padding: 2px 6px;
    }
    .st-key-admin_notif_wrap { position: relative; }
    .st-key-admin_notif_wrap [data-testid="stElementContainer"]:has(.admin-hdr-badge) {
        position: absolute !important; top: -6px; left: 14px; width: auto !important; z-index: 10; pointer-events: none;
    }
    .admin-hdr-user-box {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
        height: 28px;
        color: #ffffff;
        font-size: 0.88rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .admin-hdr-user-badge {
        background: rgba(255,255,255,0.22);
        padding: 2px 7px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1;
        display: inline-flex;
        align-items: center;
    }
    .st-key-btn_admin_logout_top {
        display: flex !important;
        align-items: center !important;
        height: 28px !important;
    }
    .st-key-btn_admin_logout_top div[data-testid="stButton"] {
        display: flex !important;
        align-items: center !important;
        height: 100% !important;
    }
    .st-key-btn_admin_logout_top button {
        height: 20px !important;
        min-height: 20px !important;
        max-height: 20px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        padding: 0 8px !important;
        line-height: 18px !important;
        background: rgba(255, 255, 255, 0.22) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        box-shadow: none !important;
        margin: 0 !important;
        transform: translateY(4px) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .st-key-btn_admin_logout_top button:hover {
        background: #dc2626 !important;
        border-color: #ef4444 !important;
        color: #ffffff !important;
    }
    .st-key-btn_ack_sec_alert button {
        min-height: 34px !important;
        height: 34px !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        padding: 4px 12px !important;
        background: #ffffff !important;
        border: 1px solid #d97706 !important;
        color: #b45309 !important;
        border-radius: 6px !important;
        margin-top: 5px !important;
    }
    .st-key-btn_ack_sec_alert button:hover {
        background: #fef3c7 !important;
        color: #92400e !important;
    }
    @media (max-width: 640px) {
        .st-key-admin_header { padding: 8px 10px 10px 10px; }
        .admin-hdr-logo-hero img { width: 56px !important; height: 56px !important; }
        .admin-hdr-social .admin-hdr-follow, .admin-hdr-tag { display: none; }
        .admin-hdr-name { font-size: 1.15rem; }
        .st-key-admin_header [data-testid="stPopover"] button p { font-size: 12px !important; }
        .admin-hdr-date { font-size: 0.75rem; white-space: normal; }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="admin_header"):
        col_logo, col_main = st.columns([1.15, 7.3])
        with col_logo:
            st.markdown(f"""
            <div class="admin-hdr-logo-hero">
                {hdr_logo_img}
            </div>
            """, unsafe_allow_html=True)
        with col_main:
            # ---------- แถวบน: แจ้งเตือนออเดอร์ใหม่ | ผู้ใช้งานล็อกอิน & ปุ่มออก ----------
            r1_spacer, r1_notif, r1_user = st.columns([3.2, 1.4, 2.4])
            with r1_spacer:
                st.write("")
            with r1_notif:
                with st.container(key="admin_notif_wrap"):
                    with st.popover("🔔 ออเดอร์ใหม่", use_container_width=True):
                        st.markdown("##### 🔔 รายการออเดอร์เข้าใหม่")
                        if not recent_active_orders:
                            st.info("ไม่มีออเดอร์ใหม่ค้างในขณะนี้ค่ะ")
                        else:
                            for ord_id, ord_tbl, ord_stat, ord_tot, ord_time in recent_active_orders:
                                st.markdown(f"**บิล #{ord_id}** • โต๊ะ {ord_tbl} • **฿{int(ord_tot):,}** <span style='color: #ea580c; font-size: 12px;'>({ord_stat})</span>", unsafe_allow_html=True)
                                st.caption(f"เวลาสั่ง: {ord_time}")
                                st.write("---")
                    if new_orders_cnt > 0:
                        st.markdown(f'<span class="admin-hdr-badge">{new_orders_cnt if new_orders_cnt < 10 else "9+"}</span>', unsafe_allow_html=True)
            with r1_user:
                u_info_col, u_logout_col = st.columns([3.2, 1.0])
                with u_info_col:
                    st.markdown(f"""
                    <div class="admin-hdr-user-box">
                        <span>🟢</span>
                        <b>{u_name}</b>
                        <span class="admin-hdr-user-badge">{u_role.upper()}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with u_logout_col:
                    if st.button("ออก", key="btn_admin_logout_top", use_container_width=False):
                        st.session_state['admin_logged_in'] = False
                        st.session_state['admin_user_info'] = None
                        st.rerun()

            # ---------- แถวกลาง: ชื่อระบบ | ช่องค้นหาด่วน ----------
            r2_title, r2_search = st.columns([2.6, 4.4])
            with r2_title:
                st.markdown("""
                <div style="padding-top: 2px;">
                    <div class="admin-hdr-name">ฟ้าใสตำนัว</div>
                    <div class="admin-hdr-tag">ระบบจัดการหลังร้าน (POS & Kitchen)</div>
                </div>
                """, unsafe_allow_html=True)
            with r2_search:
                st.text_input(
                    "ค้นหาข้อมูลหลังร้าน",
                    placeholder="🔍 ค้นหาโต๊ะ, รหัสบิล, เมนูอาหาร หรือชื่อลูกค้า...",
                    key="admin_header_search",
                    label_visibility="collapsed"
                )

            # ---------- แถวล่าง: วัน เดือน ปี & โซเชียล | สถานะโต๊ะ | ตั้งค่าบัญชี ----------
            r3_date_social, r3_table_stat, r3_settings = st.columns([3.8, 1.5, 1.5])
            with r3_date_social:
                st.markdown(f"""
                <div class="admin-hdr-date" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; line-height: 36px;">
                    <span>📅 {thai_date_str}</span>
                    <span style="opacity: 0.5;">|</span>
                    <span class="admin-hdr-social">
                        <span class="admin-hdr-follow">ติดต่อเรา:</span>
                        <a href="{SOCIAL_LINKS['facebook']}" target="_blank" title="Facebook"><img src="https://cdn.simpleicons.org/facebook/ffffff" alt="Facebook" /></a>
                        <a href="{SOCIAL_LINKS['instagram']}" target="_blank" title="Instagram"><img src="https://cdn.simpleicons.org/instagram/ffffff" alt="Instagram" /></a>
                        <a href="{SOCIAL_LINKS['line']}" target="_blank" title="LINE"><img src="https://cdn.simpleicons.org/line/ffffff" alt="LINE" /></a>
                    </span>
                </div>
                """, unsafe_allow_html=True)
            with r3_table_stat:
                st.markdown(f"""
                <div style="text-align: center;">
                    <span class="admin-hdr-table">🪑 โต๊ะว่าง {available_tables_cnt}/{total_tables_cnt} โต๊ะ</span>
                </div>
                """, unsafe_allow_html=True)
            with r3_settings:
                with st.popover("⚙️ ตั้งค่าบัญชี", use_container_width=True):
                    st.markdown("### ⚙️ จัดการบัญชีผู้ดูแล")
                    p_tab1, p_tab2 = st.tabs(["🔑 เปลี่ยนรหัสผ่าน", "📧 ผูกอีเมลกู้คืน"])

                    # แท็บเปลี่ยนรหัสผ่าน
                    with p_tab1:
                        with st.form("form_change_admin_pw", clear_on_submit=True):
                            old_pw = st.text_input("รหัสผ่านเดิม:", type="password", key="chg_old_pw")
                            new_pw = st.text_input("รหัสผ่านใหม่ (อย่างน้อย 6 ตัวอักษร):", type="password", key="chg_new_pw")
                            cfm_pw = st.text_input("ยืนยันรหัสผ่านใหม่:", type="password", key="chg_cfm_pw")
                            btn_sub_pw = st.form_submit_button("💾 บันทึกรหัสผ่านใหม่", type="primary", use_container_width=True)
                            
                            if btn_sub_pw:
                                if not old_pw or not new_pw:
                                    st.error("กรุณาระบุรหัสผ่านให้ครบถ้วนค่ะ")
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
                                        st.error("❌ รหัสผ่านเดิมไม่ถูกต้อง กรุณาตรวจสอบอีกครั้งค่ะ")
                                        conn_pw.close()
                                    else:
                                        new_hash, new_salt = hash_password(new_pw.strip())
                                        c_pw.execute("UPDATE admin_users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, u_info.get('id', 1)))
                                        conn_pw.commit()
                                        conn_pw.close()
                                        st.toast("🎉 เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!", icon="✅")
                                        st.success("🎉 เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!")
                                        st.rerun()

                    # แท็บผูกอีเมลกู้คืน
                    with p_tab2:
                        st.caption("อีเมลนี้ใช้สำหรับรับรหัส OTP เมื่อลืมรหัสผ่าน")
                        with st.form("form_update_email"):
                            new_email_input = st.text_input("อีเมลสำหรับกู้คืนรหัสผ่าน:", value=u_email, key="inp_upd_email")
                            btn_sub_email = st.form_submit_button("💾 อัปเดตอีเมล", type="primary", use_container_width=True)
                            if btn_sub_email:
                                if not new_email_input.strip() or "@" not in new_email_input:
                                    st.error("กรุณาระบุรูปแบบอีเมลที่ถูกต้องค่ะ")
                                else:
                                    conn_em = sqlite3.connect(DB_NAME)
                                    c_em = conn_em.cursor()
                                    c_em.execute("UPDATE admin_users SET email = ? WHERE id = ?", (new_email_input.strip(), u_info.get('id', 1)))
                                    conn_em.commit()
                                    conn_em.close()
                                    st.session_state['admin_user_info']['email'] = new_email_input.strip()
                                    st.toast("🎉 อัปเดตอีเมลเรียบร้อยแล้ว!", icon="✅")
                                    st.success("🎉 อัปเดตอีเมลกู้คืนรหัสผ่านเรียบร้อยแล้ว!")
                                    st.rerun()

    if u_email == 'owner@fahsaitumnua.com' and not st.session_state.get('dismiss_sec_alert', False):
        col_warn, col_ack = st.columns([5.5, 1.1])
        with col_warn:
            st.warning("🔒 **ข้อแนะนำด้านความปลอดภัย:** บัญชีนี้ยังใช้อีเมลตั้งต้นของระบบ กรุณาคลิกที่ **'⚙️ ตั้งค่าบัญชี'** ที่แถบหัวเว็บด้านบน เพื่อผูก **อีเมลส่วนตัวของเจ้าของร้าน** และเปลี่ยนรหัสผ่าน เพื่อป้องกันไม่ให้บุคคลอื่นสามารถเข้าถึงหรือกู้คืนรหัสผ่านได้ค่ะ")
        with col_ack:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            if st.button("รับทราบ", key="btn_ack_sec_alert", use_container_width=True):
                st.session_state['dismiss_sec_alert'] = True
                st.rerun()


