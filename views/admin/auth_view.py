# ==============================================================================
# ระบบยืนยันตัวตนผู้ดูแลร้าน & กู้คืนรหัสผ่าน (Admin Auth & Password Recovery)
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
        logo_html = '<div style="text-align: center; font-size: 28px; font-weight: 800; color: #ea580c; margin-bottom: 4px;">ฟ้าใสตำนัว</div>'

    # กรณีที่ยังไม่ได้ลงชื่อเข้าใช้: แสดงฟอร์ม Login และระบบกู้คืนรหัสผ่าน
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

        col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
        with col_l2:
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center; color: #431407; margin-bottom: 4px;'>เข้าสู่ระบบผู้ดูแลร้าน</h3>", unsafe_allow_html=True)
                st.caption("ป้อนชื่อผู้ใช้งานและรหัสผ่านเพื่อยืนยันสิทธิ์")
                
                with st.form("admin_login_form"):
                    input_user = st.text_input("ชื่อผู้ใช้ (Username):", placeholder="เช่น admin", key="inp_admin_user")
                    input_pass = st.text_input("รหัสผ่าน (Password):", type="password", placeholder="ป้อนรหัสผ่าน", key="inp_admin_pass")
                    submit_login = st.form_submit_button("ลงชื่อเข้าใช้", type="primary", use_container_width=True)

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
                                st.toast(f"ยินดีต้อนรับ {user_record[4]} เข้าสู่ระบบค่ะ!")
                                st.rerun()
                            else:
                                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้งค่ะ")

                # ==============================================================
                # ส่วนกู้คืนรหัสผ่านผ่านอีเมลของเจ้าของร้าน (Owner Email OTP)
                # ==============================================================
                with st.expander("ลืมรหัสผ่าน? (กู้คืนบัญชีผู้ดูแลผ่านอีเมล)"):
                    reset_step = st.session_state.get('reset_step', 'request_otp')

                    if reset_step == 'request_otp':
                        st.markdown("##### รับรหัส OTP ทางอีเมลของเจ้าของร้าน")
                        st.caption("ระบบจะส่งรหัส OTP 6 หลักไปยังอีเมลส่วนตัวที่เจ้าของร้านผูกไว้ เพื่อความปลอดภัยสูงสุด (ไม่มีใครสามารถเข้าถึงได้นอกจากเจ้าของอีเมล)")

                        with st.form("form_req_otp"):
                            inp_id = st.text_input("ชื่อผู้ใช้ หรือ อีเมลของร้าน:", value="admin", key="inp_rec_id")
                            btn_req_otp = st.form_submit_button("ส่งรหัส OTP ไปยังอีเมล", type="primary", use_container_width=True)

                            if btn_req_otp:
                                if not inp_id.strip():
                                    st.error("กรุณาระบุชื่อผู้ใช้หรืออีเมลค่ะ")
                                else:
                                    conn_otp = sqlite3.connect(DB_NAME)
                                    c_otp = conn_otp.cursor()
                                    c_otp.execute("SELECT id, username, full_name, email FROM admin_users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)", (inp_id.strip(), inp_id.strip()))
                                    user_found = c_otp.fetchone()

                                    if not user_found:
                                        st.error("ไม่พบบัญชีผู้ใช้หรืออีเมลนี้ในระบบค่ะ")
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
                        st.markdown(f"##### กรอกรหัส OTP และตั้งรหัสผ่านใหม่")
                        st.caption(f"ระบบส่งรหัส OTP ไปที่: **{masked_e}** เรียบร้อยแล้ว (รหัสมีอายุ 10 นาที)")

                        if 'dev_otp' in st.session_state:
                            st.info(f"**[โหมดทดสอบ - ยังไม่ตั้งค่า Gmail ใน config.py]** รหัส OTP สำหรับทดสอบคือ: **`{st.session_state['dev_otp']}`**")

                        with st.form("form_verify_otp"):
                            inp_otp = st.text_input("รหัส OTP 6 หลัก:", max_chars=6, placeholder="ป้อนตัวเลข 6 หลัก", key="inp_otp_code")
                            inp_new_pw = st.text_input("รหัสผ่านใหม่ (อย่างน้อย 6 ตัวอักษร):", type="password", key="inp_new_pw_otp")
                            inp_cfm_pw = st.text_input("ยืนยันรหัสผ่านใหม่:", type="password", key="inp_cfm_pw_otp")
                            btn_sub_otp = st.form_submit_button("ยืนยันและเปลี่ยนรหัสผ่าน", type="primary", use_container_width=True)

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
                                        st.error("รหัส OTP ไม่ถูกต้อง หรือหมดอายุแล้ว กรุณาลองใหม่อีกครั้งค่ะ")
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
                                        st.toast("ตั้งรหัสผ่านใหม่สำเร็จเรียบร้อยแล้ว!")
                                        st.success("ตั้งรหัสผ่านใหม่สำเร็จเรียบร้อยแล้ว! ท่านสามารถเข้าสู่ระบบด้านบนได้ทันทีค่ะ")

                        if st.button("ขอส่งรหัสใหม่อีกครั้ง", key="btn_cancel_otp", use_container_width=True):
                            st.session_state['reset_step'] = 'request_otp'
                            st.rerun()

        render_app_footer()
        st.stop()

    # กรณีที่ลงชื่อเข้าใช้สำเร็จแล้ว: แสดงแถบข้อมูลผู้ใช้งาน + จัดการบัญชี
    u_info = st.session_state.get('admin_user_info') or {}
    u_name = u_info.get('full_name', 'ผู้ดูแลระบบ')
    u_role = u_info.get('role', 'admin')
    u_email = u_info.get('email', 'owner@fahsaitumnua.com')

    # --------------------------------------------------------------------------
    # แถบหัวเว็บ Admin Header Bar สไตล์โต๊ะลูกค้า (สีส้มโค้งมน 3 แถว)
    # --------------------------------------------------------------------------
    thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    thai_short_days = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
    thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                   "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now_th = get_thai_now()
    thai_time_str = now_th.strftime('%H:%M') + " น."
    thai_date_str = f"วัน{thai_days[now_th.weekday()]}ที่ {now_th.day} {thai_months[now_th.month - 1]} พ.ศ. {now_th.year + 543} เวลา {thai_time_str}"
    thai_date_short = f"{thai_short_days[now_th.weekday()]} {now_th.day}/{now_th.month}/{str(now_th.year + 543)[-2:]} {now_th.strftime('%H:%M')} น."

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
        hdr_logo_img = '<span style="font-size: 18px; font-weight: 800; color: #ffffff;">ฟ้าใส</span>'

    st.markdown("""
    <style>
    .st-key-admin_header {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%);
        border-radius: 14px;
        padding: 12px 16px 14px 16px;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.30);
        margin-bottom: 14px;
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
    }
    /* ล้างค่า margin ติดลบของ stMarkdown ใน Streamlit เพื่อไม่ให้องค์ประกอบเหลื่อมหรือซ้อนทับกัน */
    .st-key-admin_header [data-testid="stMarkdown"],
    .st-key-admin_header [data-testid="stMarkdownContainer"],
    .st-key-admin_header [data-testid="stElementContainer"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stColumn"] > div,
    .st-key-admin_header [data-testid="stColumn"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    .st-key-admin_header [data-testid="stColumn"] {
        min-width: 0 !important;
        display: flex !important;
        align-items: center !important;
    }

    /* ======================================================================
       แถวที่ 1 (บน): "ติดตามเรา" + ไอคอนโซเชียล (ชิดซ้าย) | "ออเดอร์ใหม่", "Admin", "ตั้งค่า" (ชิดขวา)
       ====================================================================== */
    .st-key-adm_row_top [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 8px !important;
        width: 100% !important;
    }
    .st-key-adm_row_top [data-testid="stColumn"]:nth-child(1) {
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
        margin-right: auto !important;
    }
    .st-key-adm_row_top [data-testid="stColumn"]:nth-child(2),
    .st-key-adm_row_top [data-testid="stColumn"]:nth-child(3),
    .st-key-adm_row_top [data-testid="stColumn"]:nth-child(4) {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
        min-height: 34px !important;
        height: 34px !important;
        padding: 4px 8px !important;
        white-space: nowrap !important;
        width: auto !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        white-space: nowrap !important;
    }
    .st-key-adm_action_wrap [data-testid="stPopover"] button,
    .st-key-adm_action_wrap button {
        background: rgba(255, 255, 255, 0.18) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.55) !important;
        border-radius: 8px !important;
        padding: 4px 12px !important;
        min-height: 34px !important;
        height: 34px !important;
        width: auto !important;
    }
    .st-key-adm_action_wrap [data-testid="stPopover"] button p,
    .st-key-adm_action_wrap button p {
        font-size: 13.5px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        color: #ffffff !important;
    }

    .adm-hdr-social {
        color: #ffffff !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 8px !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }
    .adm-hdr-social a {
        display: inline-flex !important;
        align-items: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .adm-hdr-social img, .st-key-admin_header .adm-hdr-social img {
        width: 18px !important; min-width: 18px !important; max-width: 18px !important;
        height: 18px !important; min-height: 18px !important; max-height: 18px !important;
        border-radius: 0 !important; margin: 0 !important; display: inline-block !important; object-fit: contain !important;
    }
    .adm-hdr-badge {
        display: inline-block !important;
        background: #ef4444 !important;
        color: #ffffff !important;
        border: 1.5px solid #ffffff !important;
        border-radius: 999px !important;
        font-size: 11px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        padding: 2px 6px !important;
    }
    .st-key-adm_notif_wrap {
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        width: auto !important;
    }
    .st-key-adm_notif_wrap [data-testid="stElementContainer"]:has(.adm-hdr-badge) {
        position: absolute !important;
        top: -4px !important;
        right: -8px !important;
        width: auto !important;
        z-index: 10 !important;
        pointer-events: none !important;
    }

    /* ======================================================================
       แถวที่ 2 (กลาง): โลโก้ขนาดใหญ่ + ชื่อร้าน + คำอธิบาย (ซ้าย) และ ช่องค้นหา (ขวา) อยู่แถวเดียวกัน ไม่ซ้อนทับกัน
       ====================================================================== */
    .st-key-adm_row_main {
        width: 100% !important;
        height: auto !important;
        margin: 2px 0 !important;
        position: relative !important;
        z-index: 2 !important;
    }
    .st-key-adm_row_main [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 14px !important;
        width: 100% !important;
    }
    .st-key-adm_row_main [data-testid="stColumn"]:nth-child(1) {
        flex: 1 1 52% !important;
        width: 52% !important;
        max-width: 54% !important;
        min-width: 0 !important;
    }
    .st-key-adm_row_main [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 48% !important;
        width: 48% !important;
        max-width: 48% !important;
        min-width: 150px !important;
    }
    .adm-hdr-logo {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
        margin: 0 !important;
        padding: 2px 0 !important;
        text-align: left !important;
        width: 100% !important;
        min-width: 0 !important;
    }
    .adm-hdr-logo img, .st-key-admin_header .adm-hdr-logo img {
        width: clamp(72px, 14vw, 115px) !important;
        min-width: clamp(72px, 14vw, 115px) !important;
        max-width: clamp(72px, 14vw, 115px) !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        aspect-ratio: 1 / 1 !important;
        border-radius: 50% !important;
        border: 2.5px solid #ffffff !important;
        background: #ffffff !important;
        padding: 2px !important;
        box-sizing: border-box !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.16) !important;
        margin: 0 !important;
        display: block !important;
        object-fit: contain !important;
        flex-shrink: 0 !important;
    }
    .adm-hdr-logo-text {
        min-width: 0 !important;
        flex: 1 1 auto !important;
    }
    .adm-hdr-logo .adm-hdr-name {
        color: #ffffff !important;
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        text-align: left !important;
        white-space: nowrap !important;
    }
    .adm-hdr-logo .adm-hdr-tag {
        color: #ffedd5 !important;
        font-size: 0.82rem !important;
        line-height: 1.25 !important;
        text-align: left !important;
        margin-top: 2px !important;
    }

    /* ช่องค้นหาในแถวกลาง: ล็อกความสูง 42px และซ่อน Label เพื่อจัดกึ่งกลางแนวตั้งตรงกับโลโก้ */
    .st-key-adm_row_main [data-testid="stTextInput"],
    .st-key-adm_row_main [data-testid="stTextInputRootElement"] {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] label,
    .st-key-admin_header [data-testid="stTextInput"] [data-testid="stWidgetLabel"],
    .st-key-admin_header [data-testid="stTextInput"] [data-testid="InputInstructions"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] > div,
    .st-key-admin_header [data-testid="stTextInput"] [data-baseweb="input"],
    .st-key-admin_header [data-testid="stTextInput"] [data-baseweb="base-input"] {
        background: #ffffff !important;
        border: 2px solid #ffffff !important;
        border-radius: 8px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
        display: flex !important;
        align-items: center !important;
        overflow: hidden !important;
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] input {
        background: transparent !important;
        color: #1c1917 !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        line-height: 38px !important;
        font-size: 14px !important;
        padding: 0 12px !important;
        margin: 0 !important;
        border: none !important;
        box-sizing: border-box !important;
        width: 100% !important;
    }

    /* ======================================================================
       แถวที่ 3 (ล่าง): วันเดือนปี เวลา (ชิดซ้าย) | ป้ายโต๊ะว่าง/จำนวนโต๊ะ + ปุ่มออก (ชิดขวา)
       ====================================================================== */
    .st-key-adm_row_bottom {
        margin-top: 2px !important;
        padding-top: 8px !important;
        border-top: 1px solid rgba(255, 255, 255, 0.26) !important;
        position: relative !important;
        z-index: 1 !important;
        width: 100% !important;
    }
    .st-key-adm_row_bottom [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 10px !important;
        width: 100% !important;
    }
    .st-key-adm_row_bottom [data-testid="stColumn"]:nth-child(1) {
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
        margin-right: auto !important;
    }
    .st-key-adm_row_bottom [data-testid="stColumn"]:nth-child(2),
    .st-key-adm_row_bottom [data-testid="stColumn"]:nth-child(3) {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    .adm-hdr-date {
        color: #ffffff !important;
        font-size: 0.88rem !important;
        white-space: nowrap !important;
        text-align: left !important;
    }
    .adm-hdr-date-short { display: none !important; }
    .adm-hdr-table {
        display: inline-block !important;
        background: #ffffff !important;
        color: #c2410c !important;
        font-weight: 800 !important;
        padding: 4px 12px !important;
        border-radius: 999px !important;
        font-size: 0.88rem !important;
        white-space: nowrap !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.10) !important;
    }
    .st-key-adm_logout_wrap button {
        background: rgba(255, 255, 255, 0.18) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.55) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        min-height: 34px !important;
        height: 34px !important;
        padding: 2px 14px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        box-shadow: none !important;
        width: auto !important;
    }

    /* สไตล์สำหรับแท็บเล็ตแนวตั้งและหน้าจอกลาง (ความกว้างไม่เกิน 768px) */
    @media (max-width: 768px) {
        .adm-hdr-date-full {
            display: none !important;
        }
        .adm-hdr-date-short {
            display: inline-block !important;
            font-size: 12.5px !important;
        }
    }

    /* สไตล์สำหรับสมาร์ตโฟนและหน้าจอขนาดเล็ก (ความกว้างหน้าจอไม่เกิน 640px) */
    @media (max-width: 640px) {
        .st-key-admin_header {
            padding: 10px 12px 12px 12px !important;
            gap: 8px !important;
        }
        .adm-hdr-social {
            font-size: 12px !important;
            gap: 5px !important;
        }
        .adm-hdr-social img, .st-key-admin_header .adm-hdr-social img {
            width: 15px !important; min-width: 15px !important; max-width: 15px !important;
            height: 15px !important; min-height: 15px !important; max-height: 15px !important;
        }
        .st-key-admin_header [data-testid="stPopover"] button {
            padding: 2px 5px !important;
            min-height: 30px !important;
            height: 30px !important;
        }
        .st-key-admin_header [data-testid="stPopover"] button p {
            font-size: 11.5px !important;
        }
        .st-key-adm_action_wrap [data-testid="stPopover"] button,
        .st-key-adm_action_wrap button {
            padding: 2px 8px !important;
            min-height: 30px !important;
            height: 30px !important;
        }
        .st-key-adm_action_wrap [data-testid="stPopover"] button p,
        .st-key-adm_action_wrap button p {
            font-size: 11.5px !important;
            font-weight: 700 !important;
        }
        .st-key-adm_row_main [data-testid="stHorizontalBlock"] {
            gap: 8px !important;
        }
        .adm-hdr-logo {
            gap: 8px !important;
        }
        .adm-hdr-logo img, .st-key-admin_header .adm-hdr-logo img {
            width: clamp(58px, 16vw, 84px) !important;
            min-width: clamp(58px, 16vw, 84px) !important;
            max-width: clamp(58px, 16vw, 84px) !important;
            height: auto !important;
            aspect-ratio: 1 / 1 !important;
            object-fit: contain !important;
        }
        .adm-hdr-logo .adm-hdr-name {
            font-size: 1.05rem !important;
        }
        .adm-hdr-logo .adm-hdr-tag {
            font-size: 0.68rem !important;
        }
        .st-key-admin_header [data-testid="stTextInput"] > div,
        .st-key-admin_header [data-testid="stTextInput"] [data-baseweb="input"],
        .st-key-admin_header [data-testid="stTextInput"] [data-baseweb="base-input"] {
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
        }
        .st-key-admin_header [data-testid="stTextInput"] input {
            height: 34px !important;
            min-height: 34px !important;
            max-height: 34px !important;
            line-height: 34px !important;
            font-size: 12.5px !important;
            padding: 0 8px !important;
        }
        .adm-hdr-date-full {
            display: none !important;
        }
        .adm-hdr-date-short {
            display: inline-block !important;
            font-size: 11.5px !important;
        }
        .adm-hdr-table {
            font-size: 0.78rem !important;
            padding: 3px 9px !important;
        }
        .st-key-adm_logout_wrap button {
            min-height: 30px !important;
            height: 30px !important;
            padding: 2px 10px !important;
            font-size: 12px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="admin_header"):
        # ---------- แถวที่ 1 (บน): "ติดตามเรา" + โซเชียล (ชิดซ้าย) | ออเดอร์ใหม่, Admin, ตั้งค่า (ชิดขวา) ----------
        with st.container(key="adm_row_top"):
            r1_social, r1_notif, r1_user, r1_settings = st.columns([2.2, 1.0, 1.2, 0.9])
            with r1_social:
                st.markdown(f"""
                <div class="adm-hdr-social">
                    <span class="adm-hdr-follow">ติดตามเรา</span>
                    <a href="{SOCIAL_LINKS['facebook']}" target="_blank" title="Facebook"><img src="https://cdn.simpleicons.org/facebook/ffffff" alt="Facebook" /></a>
                    <a href="{SOCIAL_LINKS['instagram']}" target="_blank" title="Instagram"><img src="https://cdn.simpleicons.org/instagram/ffffff" alt="Instagram" /></a>
                    <a href="{SOCIAL_LINKS['line']}" target="_blank" title="LINE"><img src="https://cdn.simpleicons.org/line/ffffff" alt="LINE" /></a>
                </div>
                """, unsafe_allow_html=True)
            with r1_notif:
                with st.container(key="adm_notif_wrap"):
                    with st.popover("ออเดอร์ใหม่", use_container_width=False):
                        st.markdown("##### รายการออเดอร์เข้าใหม่")
                        if not recent_active_orders:
                            st.info("ไม่มีออเดอร์ใหม่ค้างในขณะนี้ค่ะ")
                        else:
                            for ord_id, ord_tbl, ord_stat, ord_tot, ord_time in recent_active_orders:
                                st.markdown(f"**บิล #{ord_id}** • โต๊ะ {ord_tbl} • **฿{int(ord_tot):,}** <span style='color: #ea580c; font-size: 12px;'>({ord_stat})</span>", unsafe_allow_html=True)
                                st.caption(f"เวลาสั่ง: {ord_time}")
                                st.write("---")
                    if new_orders_cnt > 0:
                        st.markdown(f'<span class="adm-hdr-badge">{new_orders_cnt if new_orders_cnt < 10 else "9+"}</span>', unsafe_allow_html=True)
            with r1_user:
                with st.popover(f"คุณ{u_name}", use_container_width=False):
                    st.markdown(f"**{u_name}** ({u_role.upper()})")
                    st.caption(f"อีเมล: {u_email}")
                    st.write("---")
                    if st.button("ออกจากระบบ (Logout)", key="btn_admin_pop_logout", type="primary", use_container_width=True):
                        st.session_state['admin_logged_in'] = False
                        st.session_state['admin_user_info'] = None
                        st.rerun()
            with r1_settings:
                with st.container(key="adm_action_wrap"):
                    with st.popover("ตั้งค่า", use_container_width=False):
                        st.markdown("### จัดการบัญชีผู้ดูแล")
                        p_tab1, p_tab2 = st.tabs(["เปลี่ยนรหัสผ่าน", "ผูกอีเมลกู้คืน"])

                        # แท็บเปลี่ยนรหัสผ่าน
                        with p_tab1:
                            with st.form("form_change_admin_pw", clear_on_submit=True):
                                old_pw = st.text_input("รหัสผ่านเดิม:", type="password", key="chg_old_pw")
                                new_pw = st.text_input("รหัสผ่านใหม่ (อย่างน้อย 6 ตัวอักษร):", type="password", key="chg_new_pw")
                                cfm_pw = st.text_input("ยืนยันรหัสผ่านใหม่:", type="password", key="chg_cfm_pw")
                                btn_sub_pw = st.form_submit_button("บันทึกรหัสผ่านใหม่", type="primary", use_container_width=True)
                                
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
                                            st.error("รหัสผ่านเดิมไม่ถูกต้อง กรุณาตรวจสอบอีกครั้งค่ะ")
                                            conn_pw.close()
                                        else:
                                            new_hash, new_salt = hash_password(new_pw.strip())
                                            c_pw.execute("UPDATE admin_users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, u_info.get('id', 1)))
                                            conn_pw.commit()
                                            conn_pw.close()
                                            st.toast("เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!")
                                            st.success("เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้วค่ะ")
                                            st.rerun()

                        # แท็บผูกอีเมลกู้คืน
                        with p_tab2:
                            st.caption("อีเมลนี้ใช้สำหรับรับรหัส OTP เมื่อลืมรหัสผ่าน")
                            with st.form("form_update_email"):
                                new_email_input = st.text_input("อีเมลสำหรับกู้คืนรหัสผ่าน:", value=u_email, key="inp_upd_email")
                                btn_sub_email = st.form_submit_button("อัปเดตอีเมล", type="primary", use_container_width=True)
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
                                        st.toast("อัปเดตอีเมลเรียบร้อยแล้ว!")
                                        st.success("อัปเดตอีเมลกู้คืนรหัสผ่านเรียบร้อยแล้ว!")
                                        st.rerun()

        # ---------- แถวที่ 2 (กลาง): โลโก้ขนาดใหญ่ + ชื่อร้าน + คำอธิบาย (ซ้าย) และ ช่องค้นหา (ขวา) อยู่แถวเดียวกัน ----------
        with st.container(key="adm_row_main"):
            r2_logo, r2_search = st.columns([1.1, 1.0])
            with r2_logo:
                st.markdown(f"""
                <div class="adm-hdr-logo">
                    {hdr_logo_img}
                    <div class="adm-hdr-logo-text">
                        <div class="adm-hdr-name">ฟ้าใสตำนัว</div>
                        <div class="adm-hdr-tag">ระบบจัดการเคาน์เตอร์ & จอครัว</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with r2_search:
                search_admin_kw = st.text_input(
                    "ค้นหาข้อมูลหลังร้าน",
                    placeholder="ค้นหาโต๊ะ, รหัสบิล, เมนู, ลูกค้า...",
                    key="admin_header_search",
                    label_visibility="collapsed"
                ).strip()

        # ---------- แถวที่ 3 (ล่าง): วันเดือนปี เวลา (ชิดซ้าย) | ป้ายโต๊ะว่าง/จำนวนโต๊ะ + ปุ่มออก (ชิดขวา) ----------
        with st.container(key="adm_row_bottom"):
            r3_date, r3_table, r3_logout = st.columns([3.0, 1.2, 0.7])
            with r3_date:
                st.markdown(f"""
                <div class="adm-hdr-date">
                    <span class="adm-hdr-date-full">{thai_date_str}</span>
                    <span class="adm-hdr-date-short">{thai_date_short}</span>
                </div>
                """, unsafe_allow_html=True)
            with r3_table:
                st.markdown(f'<span class="adm-hdr-table">โต๊ะว่าง {available_tables_cnt}/{total_tables_cnt} โต๊ะ</span>', unsafe_allow_html=True)
            with r3_logout:
                with st.container(key="adm_logout_wrap"):
                    if st.button("ออก", key="btn_admin_logout_bottom", use_container_width=False):
                        st.session_state['admin_logged_in'] = False
                        st.session_state['admin_user_info'] = None
                        st.rerun()


    # กล่องผลการค้นหาข้อมูลหลังร้านแบบรวมศูนย์ (แสดงเด่นชัดใต้ Header เมื่อมีคำค้นหา)
    cur_adm_kw = st.session_state.get('admin_header_search', '').strip()
    if cur_adm_kw:
        render_admin_search_results(cur_adm_kw)

    if u_email == 'owner@fahsaitumnua.com' and not st.session_state.get('dismiss_sec_alert', False):
        col_warn, col_ack = st.columns([5.5, 1.1])
        with col_warn:
            st.warning("**ข้อแนะนำด้านความปลอดภัย:** บัญชีนี้ยังใช้อีเมลตั้งต้นของระบบ กรุณาคลิกที่ **'ตั้งค่าบัญชี'** ที่แถบหัวเว็บด้านบน เพื่อผูก **อีเมลส่วนตัวของเจ้าของร้าน** และเปลี่ยนรหัสผ่าน เพื่อป้องกันไม่ให้บุคคลอื่นสามารถเข้าถึงหรือกู้คืนรหัสผ่านได้ค่ะ")
        with col_ack:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            if st.button("รับทราบ", key="btn_ack_sec_alert", use_container_width=True):
                st.session_state['dismiss_sec_alert'] = True
                st.rerun()

def render_admin_search_results(kw: str):
    """แสดงการ์ดผลการค้นหาข้อมูลหลังร้านแบบรวมศูนย์ ใต้แถบหัวเว็บ"""
    import re
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    kw_clean = kw.strip()
    kw_pat = f"%{kw_clean}%"

    digits = re.findall(r'\d+', kw_clean)
    num_val = int(digits[0]) if digits else None

    # 1. โต๊ะอาหาร (ค้นหาตามหมายเลข หรือชื่อโต๊ะ เช่น '1' หรือ 'โต๊ะที่ 1')
    if num_val is not None:
        c.execute("""
            SELECT t.table_number, t.name,
                   COUNT(CASE WHEN o.status NOT IN ('paid', 'archived') THEN 1 END) as active_orders
            FROM tables t
            LEFT JOIN orders o ON t.table_number = o.table_id
            WHERE t.table_number = ? OR t.name LIKE ?
            GROUP BY t.table_number
            LIMIT 6
        """, (num_val, kw_pat))
    else:
        c.execute("""
            SELECT t.table_number, t.name,
                   COUNT(CASE WHEN o.status NOT IN ('paid', 'archived') THEN 1 END) as active_orders
            FROM tables t
            LEFT JOIN orders o ON t.table_number = o.table_id
            WHERE t.name LIKE ?
            GROUP BY t.table_number
            LIMIT 6
        """, (kw_pat,))
    res_tables = c.fetchall()

    # 2. บิล / ออเดอร์ (ค้นหาตามเลขบิล, โต๊ะ, สถานะ หรือชื่ออาหารที่สั่ง)
    if num_val is not None:
        c.execute("""
            SELECT id, table_id, status, total_price, created_at 
            FROM orders 
            WHERE id = ? OR table_id = ?
            ORDER BY id DESC LIMIT 6
        """, (num_val, num_val))
    else:
        c.execute("""
            SELECT DISTINCT o.id, o.table_id, o.status, o.total_price, o.created_at 
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status LIKE ? OR oi.item_name LIKE ?
            ORDER BY o.id DESC LIMIT 6
        """, (kw_pat, kw_pat))
    res_orders = c.fetchall()

    # 3. เมนูอาหาร (ค้นหาตามชื่อ, หมวดหมู่, คำอธิบาย)
    c.execute("""
        SELECT id, name, category, price, image 
        FROM menu_items 
        WHERE name LIKE ? OR category LIKE ? OR description LIKE ?
        LIMIT 8
    """, (kw_pat, kw_pat, kw_pat))
    res_menus = c.fetchall()

    # 4. สมาชิก / ลูกค้า (ค้นหาตามชื่อ, นามสกุล, เบอร์โทร)
    c.execute("""
        SELECT id, first_name, last_name, phone, points 
        FROM members 
        WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?
        LIMIT 6
    """, (kw_pat, kw_pat, kw_pat))
    res_members = c.fetchall()
    conn.close()

    total_count = len(res_tables) + len(res_orders) + len(res_menus) + len(res_members)

    def clear_admin_search_kw():
        st.session_state['admin_header_search'] = ""

    with st.container(border=True):
        c_ttl, c_cls = st.columns([5, 1.4])
        with c_ttl:
            st.markdown(f"#### ผลการค้นหาข้อมูลหลังร้าน: <span style='color: #ea580c;'>\"{kw_clean}\"</span> (พบ {total_count} รายการ)", unsafe_allow_html=True)
        with c_cls:
            st.button("ปิดผลค้นหา", key="btn_clear_adm_search", type="primary", use_container_width=True, on_click=clear_admin_search_kw)

        if total_count == 0:
            st.info(f"ไม่พบข้อมูลที่ตรงกับคำค้นหา '{kw_clean}' ค่ะ ลองพิมพ์คำอื่น เช่น ชื่อเมนู (ตำ, ยำ, ไก่), หมายเลขโต๊ะ (1, 2) หรือเบอร์โทรศัพท์นะคะ")
            return

        # แสดงโต๊ะอาหารที่พบ
        if res_tables:
            st.markdown("##### โต๊ะอาหาร")
            t_cols = st.columns(min(len(res_tables), 4))
            for idx, (t_num, t_name, act_cnt) in enumerate(res_tables):
                with t_cols[idx % len(t_cols)]:
                    with st.container(border=True):
                        st.markdown(f"**{t_name}**")
                        if act_cnt > 0:
                            st.markdown(f"<span style='color: #ea580c; font-weight: 600; font-size: 13px;'>มีออเดอร์ ({act_cnt} บิล)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: #16a34a; font-weight: 600; font-size: 13px;'>โต๊ะว่าง</span>", unsafe_allow_html=True)

        # แสดงบิล / ออเดอร์ที่พบ
        if res_orders:
            st.markdown("##### บิล / ออเดอร์")
            for o_id, o_tbl, o_stat, o_tot, o_time in res_orders:
                stat_th = {"pending": "รอครัวรับ", "accepted": "กำลังปรุง", "served": "เสิร์ฟแล้ว", "paid": "เช็คบิลแล้ว", "archived": "ปิดบิลแล้ว"}.get(o_stat, o_stat)
                stat_color = "#16a34a" if o_stat in ('paid', 'served') else "#ea580c"
                st.markdown(f"• **บิล #{o_id}** (โต๊ะ {o_tbl}) — ยอดรวม: **฿{int(o_tot):,}** — สถานะ: <span style='color: {stat_color}; font-weight: 600;'>{stat_th}</span> <span style='color: #64748b; font-size: 12px;'>({o_time})</span>", unsafe_allow_html=True)

        # แสดงเมนูอาหารที่พบ
        if res_menus:
            st.markdown("##### รายการอาหาร")
            for m_id, m_name, m_cat, m_price, m_img in res_menus:
                st.markdown(f"• **{m_name}** ({m_cat}) — ราคา: **฿{m_price:,.2f}**")

        # แสดงสมาชิกที่พบ
        if res_members:
            st.markdown("##### สมาชิก / ลูกค้า")
            for mem_id, f_name, l_name, ph, pts in res_members:
                st.markdown(f"• คุณ{f_name} {l_name} — เบอร์โทร: `{ph}` — แต้มสะสม: **{pts:,}** คะแนน")



