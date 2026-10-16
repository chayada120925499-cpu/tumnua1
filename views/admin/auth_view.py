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
        hdr_logo_img = f'<img src="data:image/png;base64,{logo_b64}" class="admin-hdr-logo-img" style="width: 52px; height: 52px; min-width: 52px; max-width: 52px; min-height: 52px; max-height: 52px; border-radius: 50%; object-fit: cover; border: 2.5px solid #ffffff; background: #ffffff; flex-shrink: 0; display: block; margin: 0;" alt="โลโก้ฟ้าใสตำนัว" />'
    else:
        hdr_logo_img = '<span style="font-size: 18px; font-weight: 800; color: #ffffff;">ฟ้าใส</span>'

    st.markdown("""
    <style>
    .st-key-admin_header {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%);
        border-radius: 14px;
        padding: 10px 14px 12px 14px;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.30);
        margin-bottom: 12px;
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }
    .st-key-admin_header [data-testid="stElementContainer"] {
        display: block !important;
        width: 100% !important;
        margin: 0 !important;
        text-align: left !important;
    }
    .st-key-admin_header [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 6px !important;
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stColumn"] {
        min-width: 0 !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button {
        background: rgba(255, 255, 255, 0.16) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.7) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        color: #ffffff !important;
        min-height: 34px !important;
        height: 34px !important;
        padding: 2px 8px !important;
        white-space: nowrap !important;
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.28) !important;
    }
    .st-key-admin_header [data-testid="stPopover"] button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] {
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #1c1917 !important;
        height: 40px !important;
        font-size: 14px !important;
        width: 100% !important;
    }
    .st-key-admin_header [data-testid="stTextInput"] > div > div {
        border: 2px solid #ffffff !important;
        border-radius: 8px !important;
        background: #ffffff !important;
    }
    .admin-hdr-brand {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
        color: #ffffff !important;
        width: 100% !important;
        margin: 2px 0 !important;
    }
    .admin-hdr-brand img.admin-hdr-logo-img {
        width: 52px !important;
        height: 52px !important;
        min-width: 52px !important;
        max-width: 52px !important;
        min-height: 52px !important;
        max-height: 52px !important;
        border-radius: 50% !important;
        border: 2.5px solid #ffffff !important;
        background: #ffffff !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.18) !important;
        object-fit: cover !important;
        flex-shrink: 0 !important;
        display: block !important;
        margin: 0 !important;
    }
    .admin-hdr-name {
        color: #ffffff !important;
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }
    .admin-hdr-tag {
        color: #ffedd5 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }
    .admin-hdr-social {
        color: #ffffff !important;
        font-size: 13px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        white-space: nowrap !important;
    }
    .admin-hdr-social a { display: inline-flex !important; align-items: center !important; }
    .admin-hdr-social img {
        width: 17px !important;
        height: 17px !important;
        min-width: 17px !important;
        max-width: 17px !important;
        border-radius: 0 !important;
        margin: 0 !important;
    }
    .admin-hdr-date { color: #ffffff !important; font-size: 0.86rem !important; white-space: nowrap !important; }
    .admin-hdr-date-short { display: none !important; }
    .admin-hdr-table {
        display: inline-block !important;
        background: #ffffff !important;
        color: #c2410c !important;
        font-weight: 800 !important;
        padding: 4px 10px !important;
        border-radius: 999px !important;
        font-size: 0.84rem !important;
        white-space: nowrap !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
    }
    .admin-hdr-badge {
        display: inline-block !important;
        background: #dc2626 !important;
        color: #ffffff !important;
        border: 1.5px solid #ffffff !important;
        border-radius: 999px !important;
        font-size: 11px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        padding: 2px 6px !important;
    }
    .st-key-admin_notif_wrap { position: relative !important; }
    .st-key-admin_notif_wrap [data-testid="stElementContainer"]:has(.admin-hdr-badge) {
        position: absolute !important;
        top: -6px !important;
        right: 4px !important;
        width: auto !important;
        z-index: 10 !important;
        pointer-events: none !important;
    }
    .admin-hdr-user-box {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        color: #ffffff !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }
    .admin-hdr-user-badge {
        background: rgba(255,255,255,0.22) !important;
        padding: 3px 8px !important;
        border-radius: 999px !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    .st-key-btn_admin_logout_top button {
        height: 34px !important;
        min-height: 34px !important;
        max-height: 34px !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        padding: 0 8px !important;
        background: rgba(255, 255, 255, 0.22) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.75) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        white-space: nowrap !important;
        width: 100% !important;
    }
    .st-key-btn_admin_logout_top button:hover {
        background: #dc2626 !important;
        border-color: #ffffff !important;
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

    /* ==================== Responsive สำหรับหน้าจอมือถือ / iPhone (<= 768px) ==================== */
    @media (max-width: 768px) {
        .st-key-admin_header {
            padding: 8px 10px 10px 10px !important;
            gap: 6px !important;
        }
        /* แถวบน: กำหนดความกว้างคอลัมน์เป็นเปอร์เซ็นต์ชัดเจน ป้องกัน WebKit iPhone บีบปุ่มซ้อนกัน */
        .st-key-adm_row_top [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 4px !important;
        }
        .st-key-adm_row_top [data-testid="stColumn"]:nth-child(1) {
            flex: 0 0 32% !important;
            width: 32% !important;
            max-width: 32% !important;
            min-width: 0 !important;
        }
        .st-key-adm_row_top [data-testid="stColumn"]:nth-child(2) {
            flex: 0 0 40% !important;
            width: 40% !important;
            max-width: 40% !important;
            min-width: 0 !important;
        }
        .st-key-adm_row_top [data-testid="stColumn"]:nth-child(3) {
            flex: 0 0 24% !important;
            width: 24% !important;
            max-width: 24% !important;
            min-width: 0 !important;
        }
        .admin-hdr-user-name-full { display: none !important; }
        .admin-hdr-user-box { font-size: 0.78rem !important; gap: 4px !important; }

        /* แถวโลโก้และชื่อร้าน: ย่อขนาดให้กะทัดรัดบนหน้าจอ iPhone */
        .admin-hdr-brand img.admin-hdr-logo-img {
            width: 44px !important;
            height: 44px !important;
            min-width: 44px !important;
            max-width: 44px !important;
            min-height: 44px !important;
            max-height: 44px !important;
        }
        .admin-hdr-name { font-size: 1.2rem !important; }
        .admin-hdr-tag { font-size: 0.72rem !important; }

        /* แถวล่าง: กำหนดความกว้างคอลัมน์เป็นเปอร์เซ็นต์ชัดเจน ไม่ให้ล้นหรือทับซ้อน */
        .st-key-adm_row_bot [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 4px !important;
        }
        .st-key-adm_row_bot [data-testid="stColumn"]:nth-child(1) {
            flex: 0 0 28% !important;
            width: 28% !important;
            max-width: 28% !important;
            min-width: 0 !important;
        }
        .st-key-adm_row_bot [data-testid="stColumn"]:nth-child(2) {
            flex: 0 0 40% !important;
            width: 40% !important;
            max-width: 40% !important;
            min-width: 0 !important;
        }
        .st-key-adm_row_bot [data-testid="stColumn"]:nth-child(3) {
            flex: 0 0 29% !important;
            width: 29% !important;
            max-width: 29% !important;
            min-width: 0 !important;
        }
        .admin-hdr-date-full, .admin-hdr-social { display: none !important; }
        .admin-hdr-date-short { display: inline-block !important; font-size: 0.74rem !important; font-weight: 600 !important; }
        .admin-hdr-table { font-size: 0.74rem !important; padding: 3px 8px !important; }
        .st-key-admin_header [data-testid="stPopover"] button {
            padding: 2px 6px !important;
            min-height: 30px !important;
            height: 30px !important;
        }
        .st-key-admin_header [data-testid="stPopover"] button p {
            font-size: 11.5px !important;
        }
        .st-key-btn_admin_logout_top button {
            min-height: 30px !important;
            height: 30px !important;
            max-height: 30px !important;
            font-size: 11.5px !important;
            padding: 0 6px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="admin_header"):
        # ---------- แถวที่ 1 (บน): สถานะผู้ดูแล | ออเดอร์ใหม่ | ปุ่มออกจากระบบ ----------
        with st.container(key="adm_row_top"):
            r1_user, r1_notif, r1_logout = st.columns([1.2, 1.3, 0.8])
            with r1_user:
                st.markdown(f"""
                <div class="admin-hdr-user-box">
                    <span style="color: #bbf7d0;">●</span>
                    <b class="admin-hdr-user-name-full">{u_name}</b>
                    <span class="admin-hdr-user-badge">{u_role.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
            with r1_notif:
                with st.container(key="admin_notif_wrap"):
                    with st.popover("ออเดอร์ใหม่", use_container_width=True):
                        st.markdown("##### รายการออเดอร์เข้าใหม่")
                        if not recent_active_orders:
                            st.info("ไม่มีออเดอร์ใหม่ค้างในขณะนี้ค่ะ")
                        else:
                            for ord_id, ord_tbl, ord_stat, ord_tot, ord_time in recent_active_orders:
                                st.markdown(f"**บิล #{ord_id}** • โต๊ะ {ord_tbl} • **฿{int(ord_tot):,}** <span style='color: #ea580c; font-size: 12px;'>({ord_stat})</span>", unsafe_allow_html=True)
                                st.caption(f"เวลาสั่ง: {ord_time}")
                                st.write("---")
                    if new_orders_cnt > 0:
                        st.markdown(f'<span class="admin-hdr-badge">{new_orders_cnt if new_orders_cnt < 10 else "9+"}</span>', unsafe_allow_html=True)
            with r1_logout:
                if st.button("ออก", key="btn_admin_logout_top", use_container_width=True):
                    st.session_state['admin_logged_in'] = False
                    st.session_state['admin_user_info'] = None
                    st.rerun()

        # ---------- แถวที่ 2: โลโก้ + ชื่อร้าน (แยกเป็นแถวอิสระ ไม่ใช้ st.columns เพื่อป้องกันการซ้อนทับบน iPhone 100%) ----------
        st.markdown(f"""
        <div class="admin-hdr-brand">
            {hdr_logo_img}
            <div style="min-width: 0; overflow: hidden;">
                <div class="admin-hdr-name">ฟ้าใสตำนัว</div>
                <div class="admin-hdr-tag">ระบบจัดการหลังร้าน (POS & Kitchen)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ---------- แถวที่ 3: ช่องค้นหาข้อมูลหลังร้าน (แยกเป็นแถวเดี่ยวเต็มความกว้าง 100% ไม่ชนกับโลโก้หรือข้อความ) ----------
        st.text_input(
            "ค้นหาข้อมูลหลังร้าน",
            placeholder="ค้นหาโต๊ะ, รหัสบิล, เมนูอาหาร หรือชื่อลูกค้า...",
            key="admin_header_search",
            label_visibility="collapsed"
        )

        # ---------- แถวที่ 4 (ล่าง): วัน เดือน ปี & โซเชียล | สถานะโต๊ะ | ตั้งค่าบัญชี ----------
        with st.container(key="adm_row_bot"):
            r3_date_social, r3_table_stat, r3_settings = st.columns([1.1, 1.4, 1.1])
            with r3_date_social:
                st.markdown(f"""
                <div class="admin-hdr-date" style="display: flex; align-items: center; gap: 6px; flex-wrap: nowrap;">
                    <span class="admin-hdr-date-full">{thai_date_str}</span>
                    <span class="admin-hdr-date-short">ศ. {now_th.day}/{now_th.month}/{str(now_th.year + 543)[-2:]}</span>
                    <span class="admin-hdr-social">
                        <span style="opacity: 0.5;">|</span>
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
                    <span class="admin-hdr-table">โต๊ะว่าง {available_tables_cnt}/{total_tables_cnt} โต๊ะ</span>
                </div>
                """, unsafe_allow_html=True)
            with r3_settings:
                with st.popover("ตั้งค่าบัญชี", use_container_width=True):
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
                                        st.success("เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!")
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

    if u_email == 'owner@fahsaitumnua.com' and not st.session_state.get('dismiss_sec_alert', False):
        col_warn, col_ack = st.columns([5.5, 1.1])
        with col_warn:
            st.warning("**ข้อแนะนำด้านความปลอดภัย:** บัญชีนี้ยังใช้อีเมลตั้งต้นของระบบ กรุณาคลิกที่ **'ตั้งค่าบัญชี'** ที่แถบหัวเว็บด้านบน เพื่อผูก **อีเมลส่วนตัวของเจ้าของร้าน** และเปลี่ยนรหัสผ่าน เพื่อป้องกันไม่ให้บุคคลอื่นสามารถเข้าถึงหรือกู้คืนรหัสผ่านได้ค่ะ")
        with col_ack:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            if st.button("รับทราบ", key="btn_ack_sec_alert", use_container_width=True):
                st.session_state['dismiss_sec_alert'] = True
                st.rerun()


