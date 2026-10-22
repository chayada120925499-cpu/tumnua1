# ==============================================================================
# หน้าจอฝั่งลูกค้าสั่งอาหาร (Customer Ordering View)
# ==============================================================================
import os
import sqlite3
import streamlit as st
from datetime import datetime
from config import DB_NAME, LOGO_PATH, get_thai_now, get_base64_image, render_app_footer, get_valid_image_path

def render_customer_view():
    """แสดงหน้าจอสั่งอาหารสำหรับลูกค้าที่โต๊ะ"""
    logo_path = LOGO_PATH
    params = st.query_params
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
        logo_html = '<div style="text-align: center; font-size: 24px; font-weight: 800; color: #ea580c; margin-bottom: 4px;">ฟ้าใสตำนัว</div>'

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
        st.warning("ขณะนี้ทางร้านยังไม่ได้เปิดโต๊ะอาหารในระบบ")
        st.info("กรุณาติดต่อพนักงานที่เคาน์เตอร์ หรือเปิดโต๊ะในระบบหลังร้านก่อนนะคะ")
        
        col_adm1, col_adm2, col_adm3 = st.columns([1, 2, 1])
        with col_adm2:
            if st.button("ไปที่ระบบจัดการหลังร้าน (Admin)", type="primary", use_container_width=True):
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
    # ข้อมูลสมาชิกที่เข้าสู่ระบบอยู่ (เก็บใน Session State แยกตามโต๊ะ)
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
    # ฟังก์ชันจัดการตะกร้าสินค้า (Cart Callbacks)
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
    # เนื้อหาภายในตะกร้าอาหาร (แสดงเมื่อกดไอคอนตะกร้าที่แถบด้านบน)
    # ==========================================================================
    def render_cart_body():
        st.markdown(f"### ตะกร้าอาหาร ({current_table_name})")
        if total_cart_qty == 0:
            st.info("ยังไม่มีอาหารในตะกร้า เลือกเมนูด้านล่างแล้วกดเพิ่มได้เลยค่ะ")
            return
        for item_name, data in list(st.session_state.cart.items()):
            subtotal = data['price'] * data['qty']
            with st.container():
                st.markdown(f"**{item_name}** • <span style='color: #ea580c; font-weight: 600;'>฿{int(data['price'])} / จาน</span>", unsafe_allow_html=True)

                # แถวปุ่มปรับจำนวน: - | ตัวเลขจำนวน | + | ลบ
                c_minus, c_num, c_plus, c_del = st.columns([1, 1.2, 1, 1.2])
                with c_minus:
                    st.button("-", key=f"cart_dec_{item_name}", on_click=dec_from_cart_item, args=(item_name,), use_container_width=True)
                with c_num:
                    st.markdown(f"<div style='text-align: center; font-size: 1.25rem; font-weight: 700; line-height: 42px; background: #fff7ed; border-radius: 6px; border: 1.5px solid #fdba74; color: #c2410c;'>{data['qty']}</div>", unsafe_allow_html=True)
                with c_plus:
                    st.button("+", key=f"cart_inc_{item_name}", on_click=add_to_cart_item, args=(item_name, data['price']), use_container_width=True)
                with c_del:
                    st.button("ลบ", key=f"cart_rem_{item_name}", on_click=del_from_cart_item, args=(item_name,), use_container_width=True)

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
                st.markdown("##### ใช้คะแนนสะสมแลกส่วนลด")
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
                st.caption(f"คุณมีคะแนนสะสม **{m_pts}** คะแนน (สะสมครบ 10 คะแนนเพื่อแลกส่วนลด 25 บาท)")
        else:
            st.caption("สมัครสมาชิก / เข้าสู่ระบบ ที่แถบด้านบน เพื่อสะสมแต้มและแลกส่วนลดได้ค่ะ")

        net_cart_sum = max(0, total_cart_sum - discount_val)
        points_to_earn = int(net_cart_sum // 100)

        st.write("---")
        st.markdown(f"**ยอดรวมสินค้า:** ฿{int(total_cart_sum):,}")
        if discount_val > 0:
            st.markdown(f"**ส่วนลดจากคะแนน ({points_used_val} แต้ม):** :green[-฿{int(discount_val):,}]")
        st.markdown(f"#### ยอดชำระสุทธิ: <span style='color: #ea580c;'>฿{int(net_cart_sum):,}</span>", unsafe_allow_html=True)

        if current_member:
            st.caption(f"เมื่อชำระบิลนี้ คุณจะได้รับแต้มสะสมเพิ่ม: **+{points_to_earn}** คะแนน (ทุก 100 บาท = 1 คะแนน)")

        if st.button("ยืนยันส่งออเดอร์เข้าครัว", type="primary", use_container_width=True):
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
            st.toast(f"ส่งออเดอร์ #{new_order_id} เข้าครัวเรียบร้อยแล้วค่ะ!")
            st.rerun()

    # ==========================================================================
    # ฟังก์ชันแสดงขั้นตอนการชำระเงินและแนบสลิปแบบเรียบง่าย ไม่ซับซ้อน (2 ขั้นตอนสั้นๆ)
    # ==========================================================================
    def render_slip_payment_block(oid, total, slip_img, slip_time, is_main_card=False):
        p_img = "static/payment.jpg" if os.path.exists("static/payment.jpg") else "static/img/payment.jpg"
        
        c_qr, c_slip = st.columns([1.1, 1.4], gap="medium")
        with c_qr:
            st.markdown("<div style='background: #fff7ed; border: 1.5px solid #fdba74; border-radius: 8px; padding: 6px; text-align: center;'>", unsafe_allow_html=True)
            if os.path.exists(p_img):
                st.image(p_img, use_container_width=True)
            st.markdown(f"<div style='font-weight: 800; color: #c2410c; font-size: 1.15rem; margin-top: 4px;'>ยอดโอน: ฿{int(total):,}</div>", unsafe_allow_html=True)
            st.caption(f"บิล #{oid} • พร้อมเพย์ / สแกนผ่านแอปธนาคาร")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_slip:
            is_re_upload = st.session_state.get(f"change_slip_{oid}", False)
            if slip_img and os.path.exists(slip_img) and not is_re_upload:
                st.markdown(f"""
                <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 8px;">
                    <div style="color: #15803d; font-weight: bold; font-size: 0.95rem;">แนบสลิปเรียบร้อยแล้ว</div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-top: 2px;">เวลา: {slip_time or '-'}</div>
                    <div style="color: #475569; font-size: 0.82rem; margin-top: 4px;">พนักงานกำลังตรวจสอบยอดเงินและเช็คบิลให้ค่ะ</div>
                </div>
                """, unsafe_allow_html=True)
                st.image(slip_img, caption="สลิปที่แนบไว้", width=160)
                if st.button("เปลี่ยนรูปสลิปใหม่", key=f"btn_re_slip_{oid}_{is_main_card}", use_container_width=True):
                    st.session_state[f"change_slip_{oid}"] = True
                    st.rerun()
            else:
                st.markdown("**แนบสลิปโอนเงิน (ทำได้ง่ายใน 2 ขั้นตอน):**")
                st.caption("1. สแกน QR โอนเงินตามยอดด้านซ้าย\n2. แตะเลือกรูปสลิปแล้วกดส่งได้ทันทีค่ะ (รองรับ JPG, JPEG, JFIF, PNG, WEBP)")
                upl_slip = st.file_uploader(
                    "เลือกรูปภาพสลิป",
                    type=["jpg", "jpeg", "jfif", "png", "webp"],
                    key=f"upl_slip_inp_{oid}_{is_main_card}",
                    label_visibility="collapsed"
                )
                if upl_slip is not None:
                    st.image(upl_slip, caption="ตัวอย่างสลิปที่เลือก", width=140)
                    if st.button("ยืนยันส่งสลิป", key=f"btn_sub_slip_{oid}_{is_main_card}", type="primary", use_container_width=True):
                        os.makedirs("static/uploads/slips", exist_ok=True)
                        ts_int = int(datetime.now().timestamp())
                        save_p = f"static/uploads/slips/slip_order_{oid}_{ts_int}.jpg"
                        try:
                            from PIL import Image
                            pil_img = Image.open(upl_slip)
                            if pil_img.mode in ("RGBA", "P"):
                                pil_img = pil_img.convert("RGB")
                            max_w = 800
                            if pil_img.width > max_w:
                                w_ratio = max_w / float(pil_img.width)
                                h_size = int(float(pil_img.height) * float(w_ratio))
                                pil_img = pil_img.resize((max_w, h_size), Image.Resampling.LANCZOS)
                            pil_img.save(save_p, "JPEG", optimize=True, quality=80)
                        except Exception:
                            with open(save_p, "wb") as f_out:
                                f_out.write(upl_slip.getbuffer())
                        
                        time_now_str = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                        conn_up = sqlite3.connect(DB_NAME)
                        c_up = conn_up.cursor()
                        c_up.execute("UPDATE orders SET slip_image = ?, slip_uploaded_at = ? WHERE id = ?", (save_p, time_now_str, oid))
                        conn_up.commit()
                        conn_up.close()
                        
                        if f"change_slip_{oid}" in st.session_state:
                            del st.session_state[f"change_slip_{oid}"]
                        st.toast("แนบสลิปโอนเงินเรียบร้อยแล้วค่ะ!")
                        st.rerun()
                if is_re_upload:
                    if st.button("ยกเลิกการเปลี่ยนสลิป", key=f"btn_cancel_re_slip_{oid}_{is_main_card}", use_container_width=True):
                        del st.session_state[f"change_slip_{oid}"]
                        st.rerun()

    # ==========================================================================
    # เนื้อหาภายในปุ่มแจ้งเตือน (สถานะอาหารของโต๊ะนี้ แสดงแบบละเอียดและอัปเดตสดทุก 3 วินาที)
    # ==========================================================================
    def render_order_status_summary(oid, status, total, otime, order_items_trk):
        st_map = {
            'pending': ('รอร้านรับออเดอร์', '#ea580c', 0.25, 'กำลังส่งออเดอร์เข้าจอครัว...'),
            'accepted': ('ครัวรับออเดอร์แล้ว • กำลังปรุงอาหาร', '#2563eb', 0.50, 'แม่ครัวกำลังตั้งกระทะ ปรุงสดใหม่ค่ะ'),
            'cooked': ('ปรุงเสร็จ กำลังทยอยเสิร์ฟ', '#7e22ce', 0.75, 'อาหารปรุงเสร็จแล้ว พนักงานกำลังยกไปเสิร์ฟค่ะ'),
            'served': ('เสิร์ฟถึงโต๊ะครบแล้ว', '#15803d', 1.0, 'เสิร์ฟครบทุกเมนูแล้ว ทานให้อร่อยนะคะ'),
            'paid': ('เช็คบิลเรียบร้อยแล้ว', '#64748b', 1.0, 'ขอบคุณที่มาอุดหนุนฟ้าใสตำนัวนะคะ')
        }

        total_it = len(order_items_trk)
        served_it = sum(1 for it in order_items_trk if it[3] == 'served')
        cooked_it = sum(1 for it in order_items_trk if it[3] == 'cooked')
        accepted_it = sum(1 for it in order_items_trk if it[3] == 'accepted')

        if status == 'paid':
            prog_val = 1.0
            label, color, _, desc_status = st_map['paid']
        elif status == 'served' or (total_it > 0 and served_it == total_it):
            prog_val = 1.0
            label, color, _, desc_status = st_map['served']
        elif served_it > 0:
            prog_val = 0.5 + 0.4 * (served_it / total_it)
            label, color, _, desc_status = (f'กำลังทยอยเสิร์ฟ ({served_it}/{total_it} เมนู)', '#7e22ce', prog_val, 'พนักงานกำลังยกอาหารมาเสิร์ฟที่โต๊ะค่ะ')
        elif status == 'cooked' or cooked_it > 0:
            prog_val = 0.65
            label, color, _, desc_status = (f'ปรุงเสร็จแล้ว ({cooked_it}/{total_it} เมนู) รอเสิร์ฟ', '#7e22ce', prog_val, 'อาหารปรุงเสร็จแล้ว พนักงานกำลังยกไปเสิร์ฟค่ะ')
        elif status == 'accepted' or accepted_it > 0:
            prog_val = 0.50
            label, color, _, desc_status = st_map['accepted']
        else:
            prog_val = 0.25
            label, color, _, desc_status = st_map['pending']

        c_oh1, c_oh2 = st.columns([2.5, 1])
        with c_oh1:
            st.markdown(f"**ออเดอร์ #{oid}** — <span style='font-size: 0.95rem; font-weight: bold; color: {color};'>{label}</span>", unsafe_allow_html=True)
            st.caption(f"{desc_status} • สั่งเมื่อ {otime}")
        with c_oh2:
            st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 1.05rem; color: #ea580c;'>฿{int(total):,}</div>", unsafe_allow_html=True)

        st.progress(prog_val)

        with st.expander(f"ดูรายการอาหาร & สถานะแต่ละจาน (เสิร์ฟแล้ว {served_it}/{total_it} เมนู)", expanded=(status != 'paid')):
            for iname, iqty, inote, ist in order_items_trk:
                note_text = f" *(โน้ต: {inote})*" if inote else ""
                if ist == 'served':
                    st_badge = "<span style='color: #15803d; font-weight: 700;'>[เสิร์ฟแล้ว]</span>"
                elif ist == 'cooked':
                    st_badge = "<span style='color: #7e22ce; font-weight: 700;'>[ปรุงเสร็จแล้ว • รอเสิร์ฟ]</span>"
                elif ist == 'accepted' or status in ('accepted', 'cooked', 'served'):
                    st_badge = "<span style='color: #2563eb; font-weight: 700;'>[รับออเดอร์แล้ว • กำลังปรุง]</span>"
                else:
                    st_badge = "<span style='color: #ea580c; font-weight: 700;'>[รอร้านรับออเดอร์]</span>"
                st.markdown(f"• **{iname}** x{iqty}{note_text} — {st_badge}", unsafe_allow_html=True)

    @st.fragment(run_every=3)
    def render_live_notif_status_list():
        conn_trk = sqlite3.connect(DB_NAME)
        c_trk = conn_trk.cursor()
        c_trk.execute("""
            SELECT id, status, total_price, created_at, slip_image, slip_uploaded_at 
            FROM orders 
            WHERE table_id = ? AND status != 'archived'
            ORDER BY id DESC LIMIT 5
        """, (current_table_num,))
        cur_orders = c_trk.fetchall()

        if not cur_orders:
            st.info("ยังไม่มีรายการอาหารที่สั่งในขณะนี้ค่ะ สามารถเลือกเมนูแล้วสั่งเข้าครัวได้เลยนะคะ")
            conn_trk.close()
            return

        st.caption(f":green[**● อัปเดตสถานะจากครัวอัตโนมัติทุก 3 วินาที**] (เวลาปัจจุบัน: {get_thai_now().strftime('%H:%M:%S')})")
        for oid, status, total, otime, slip_img, slip_time in cur_orders:
            c_trk.execute("SELECT item_name, quantity, note, COALESCE(status, 'pending') FROM order_items WHERE order_id = ?", (oid,))
            order_items_trk = c_trk.fetchall()
            with st.container(border=True):
                render_order_status_summary(oid, status, total, otime, order_items_trk)
        conn_trk.close()

    def render_notif_body():
        st.markdown(f"### ติดตามสถานะอาหาร ({current_table_name})")
        render_live_notif_status_list()

        conn_pay = sqlite3.connect(DB_NAME)
        c_pay = conn_pay.cursor()
        c_pay.execute("""
            SELECT id, status, total_price, slip_image, slip_uploaded_at 
            FROM orders 
            WHERE table_id = ? AND status NOT IN ('paid', 'archived')
            ORDER BY id DESC LIMIT 5
        """, (current_table_num,))
        unpaid_orders = c_pay.fetchall()
        conn_pay.close()

        for oid, status, total, slip_img, slip_time in unpaid_orders:
            with st.expander(f"สแกน QR ชำระเงิน & แนบสลิป (บิล #{oid} • ฿{int(total):,})", expanded=(status == 'served' or bool(slip_img))):
                render_slip_payment_block(oid, total, slip_img, slip_time, is_main_card=False)

    # ==========================================================================
    # เนื้อหาภายในปุ่มสมัครสมาชิก / เข้าสู่ระบบ
    # ==========================================================================
    def render_member_body():
        if current_member:
            st.markdown(f"### คุณ{current_member['first_name']} {current_member['last_name']}")
            st.markdown(f"เบอร์โทร: **{current_member['phone']}**")
            st.markdown(f"คะแนนสะสม: <span style='color: #ea580c; font-weight: 800; font-size: 1.2rem;'>{current_member['points']:,}</span> คะแนน", unsafe_allow_html=True)
            if current_member['points'] >= 10:
                st.caption(f"ใช้คะแนนแลกส่วนลดได้สูงสุด ฿{(current_member['points'] // 10) * 25:,} (เลือกใช้ได้ในตะกร้าอาหาร)")
            else:
                st.caption(f"สะสมเพิ่มอีก {10 - current_member['points']} คะแนน เพื่อแลกส่วนลด 25 บาท")
            if st.button("ออกจากระบบสมาชิก", key=f"btn_mem_logout_{current_table_num}", use_container_width=True):
                st.session_state[mem_obj_key] = None
                st.session_state[mem_tbl_key] = ""
                st.rerun()
            return

        st.caption("สะสมแต้มทุก 100 บาท = 1 คะแนน • แลก 10 คะแนน = ส่วนลด 25 บาท")
        tab_login, tab_reg = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
        with tab_login:
            with st.form(f"form_mem_login_{current_table_num}"):
                lg_phone = st.text_input("หมายเลขโทรศัพท์:", placeholder="เช่น 0812345678")
                if st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True):
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
                        st.toast(f"ยินดีต้อนรับคุณ{lg_row[1]}! ({lg_row[4]:,} คะแนน)")
                        st.rerun()
        with tab_reg:
            with st.form(f"form_mem_reg_{current_table_num}"):
                rg_fname = st.text_input("ชื่อ:", placeholder="ระบุชื่อจริง")
                rg_lname = st.text_input("นามสกุล:", placeholder="ระบุนามสกุล")
                rg_phone = st.text_input("หมายเลขโทรศัพท์:", placeholder="เช่น 0812345678")
                if st.form_submit_button("ยืนยันสมัครสมาชิก", type="primary", use_container_width=True):
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
                            st.toast(f"สมัครสมาชิกสำเร็จ ยินดีต้อนรับคุณ{rg_fname.strip()} ค่ะ")
                            st.rerun()

    # ==========================================================================
    # แถบเมนูด้านบนของหน้าโต๊ะลูกค้า (Header Bar สไตล์ร้านค้าออนไลน์)
    # ==========================================================================
    # แถวบน : ติดตามเราบน Facebook / Instagram / LINE | แจ้งเตือน | สมัครสมาชิก / เข้าสู่ระบบ
    # แถวกลาง: โลโก้ร้าน | ช่องค้นหาเมนูอาหาร | ตะกร้า (มีตัวเลขจำนวนจานเล็กๆ)
    # แถวล่าง: วัน เดือน ปี (พ.ศ.) | ชื่อโต๊ะ | ปุ่มเปลี่ยนโต๊ะ
    # แก้ไขลิงก์โซเชียลของร้านได้ที่ตัวแปร SOCIAL_LINKS ด้านล่างนี้
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
        padding: 10px 16px 12px 16px;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.30);
        margin-bottom: 12px;
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }
    .st-key-cust_header [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 8px !important;
    }
    .st-key-cust_header [data-testid="stColumn"] {
        min-width: 0 !important;
    }
    .st-key-cust_header [data-testid="stPopover"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
        min-height: 36px !important;
        padding: 4px 8px !important;
        white-space: nowrap !important;
    }
    .st-key-cust_header [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.18) !important;
    }
    .st-key-cust_header [data-testid="stPopover"] button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        white-space: nowrap !important;
    }
    .st-key-cart_wrap [data-testid="stPopover"] button {
        background: rgba(255, 255, 255, 0.16) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 8px !important;
        padding: 4px 10px !important;
    }
    .st-key-cart_wrap [data-testid="stPopover"] button p {
        font-size: 14px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }
    .st-key-cust_header [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #1c1917 !important;
        height: 42px !important;
        font-size: 14px !important;
        border-radius: 6px !important;
    }
    .st-key-cust_header [data-testid="stTextInput"] > div > div {
        border: 2px solid #ffffff !important;
        border-radius: 6px !important;
    }
    .hdr-social {
        color: #ffffff !important;
        font-size: 14px !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 8px !important;
        white-space: nowrap !important;
        margin: 0 !important;
    }
    .hdr-social a {
        display: inline-flex !important;
        align-items: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .hdr-social img, .st-key-cust_header .hdr-social img {
        width: 18px !important; min-width: 18px !important; max-width: 18px !important;
        height: 18px !important; min-height: 18px !important; max-height: 18px !important;
        border-radius: 0 !important; margin: 0 !important; display: inline-block !important; object-fit: contain !important;
    }
    .hdr-logo {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        white-space: nowrap !important;
        margin: 0 !important;
        text-align: left !important;
    }
    .hdr-logo img, .st-key-cust_header .hdr-logo img {
        width: 50px !important; min-width: 50px !important; max-width: 50px !important;
        height: 50px !important; min-height: 50px !important; max-height: 50px !important;
        border-radius: 50% !important; border: 2px solid #ffffff !important; background: #ffffff !important;
        margin: 0 !important; display: inline-block !important; object-fit: cover !important;
    }
    .hdr-logo .hdr-name {
        color: #ffffff !important;
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        line-height: 1.1 !important;
        text-align: left !important;
        white-space: nowrap !important;
    }
    .hdr-logo .hdr-tag {
        color: #ffedd5 !important;
        font-size: 0.78rem !important;
        text-align: left !important;
        white-space: nowrap !important;
    }
    .hdr-date {
        color: #ffffff !important;
        font-size: 0.88rem !important;
        white-space: nowrap !important;
        text-align: left !important;
    }
    .hdr-date-short { display: none !important; }
    .hdr-table {
        display: inline-block !important;
        background: #ffffff !important;
        color: #c2410c !important;
        font-weight: 800 !important;
        padding: 3px 12px !important;
        border-radius: 999px !important;
        font-size: 0.92rem !important;
        white-space: nowrap !important;
    }
    .hdr-badge {
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
    .st-key-cart_wrap, .st-key-notif_wrap { position: relative !important; }
    .st-key-cart_wrap [data-testid="stElementContainer"]:has(.hdr-badge) {
        position: absolute !important; top: -6px; right: 2px; width: auto !important; z-index: 10; pointer-events: none;
    }
    .st-key-notif_wrap [data-testid="stElementContainer"]:has(.hdr-badge) {
        position: absolute !important; top: -6px; right: 2px; width: auto !important; z-index: 10; pointer-events: none;
    }
    .st-key-cust_header [data-testid="stElementContainer"] {
        display: block !important; width: auto !important; margin: 0 !important; text-align: left !important;
    }

    /* สไตล์สำหรับหน้าจอเดสก์ท็อปและแท็บเล็ต (กว้างกว่า 640px) */
    @media (min-width: 641px) {
        .st-key-cust_header [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
        }
    }

    /* สไตล์สำหรับสมาร์ตโฟน (ความกว้างหน้าจอไม่เกิน 640px) */
    @media (max-width: 640px) {
        .st-key-cust_header {
            padding: 8px 10px 10px 10px !important;
            gap: 4px !important;
        }
        .hdr-social .hdr-follow, .hdr-logo .hdr-tag {
            display: none !important;
        }
        .hdr-logo img, .st-key-cust_header .hdr-logo img {
            width: 38px !important; height: 38px !important; min-width: 38px !important; min-height: 38px !important;
        }
        .hdr-logo .hdr-name {
            font-size: 1.15rem !important;
        }
        .st-key-cust_header [data-testid="stPopover"] button {
            padding: 2px 6px !important;
        }
        .st-key-cust_header [data-testid="stPopover"] button p {
            font-size: 12px !important;
        }
        .st-key-cart_wrap [data-testid="stPopover"] button p {
            font-size: 13px !important;
            font-weight: 700 !important;
        }
        .hdr-date-full {
            display: none !important;
        }
        .hdr-date-short {
            display: inline-block !important;
            font-size: 11px !important;
        }
        .hdr-table {
            font-size: 0.82rem !important;
            padding: 2px 8px !important;
        }

        /* แถวบน (โซเชียล, แจ้งเตือน, สมาชิก) */
        .st-key-row_top_header [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            justify-content: space-between !important;
        }
        .st-key-row_top_header [data-testid="stColumn"]:nth-child(1) {
            width: auto !important;
            flex: 0 0 auto !important;
        }
        .st-key-row_top_header [data-testid="stColumn"]:nth-child(2),
        .st-key-row_top_header [data-testid="stColumn"]:nth-child(3) {
            width: auto !important;
            flex: 0 0 auto !important;
        }

        /* แถวกลาง (โลโก้, ช่องค้นหา, ตะกร้า): ป้องกันภาพซ้อนทับกันบนมือถือ */
        .st-key-row_main_header [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            justify-content: space-between !important;
            align-items: center !important;
            gap: 6px 0 !important;
        }
        /* โลโก้: อยู่บรรทัดบน ชิดซ้าย ไม่ให้ตัวหนังสือล้น */
        .st-key-row_main_header [data-testid="stColumn"]:nth-child(1) {
            order: 1 !important;
            width: calc(100% - 95px) !important;
            max-width: calc(100% - 95px) !important;
            flex: 1 1 auto !important;
        }
        /* ตะกร้า: อยู่บรรทัดบน ชิดขวา ไม่ถูกบีบตัวหนังสือแนวตั้ง */
        .st-key-row_main_header [data-testid="stColumn"]:nth-child(3) {
            order: 2 !important;
            width: 85px !important;
            min-width: 85px !important;
            max-width: 85px !important;
            flex: 0 0 85px !important;
            text-align: right !important;
        }
        /* ช่องค้นหา: ตกมาอยู่บรรทัดถัดไป ขยายเต็มความกว้าง 100% ไม่ทับซ้อนกับโลโก้หรือข้อความใดๆ */
        .st-key-row_main_header [data-testid="stColumn"]:nth-child(2) {
            order: 3 !important;
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
            margin-top: 4px !important;
        }

        /* แถวล่าง (วันที่, โต๊ะที่ 1, เปลี่ยนโต๊ะ) */
        .st-key-row_bottom_header [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
        }
        .st-key-row_bottom_header [data-testid="stColumn"]:nth-child(1) {
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }
        .st-key-row_bottom_header [data-testid="stColumn"]:nth-child(2) {
            flex: 0 0 auto !important;
            min-width: 0 !important;
        }
        .st-key-row_bottom_header [data-testid="stColumn"]:nth-child(3) {
            flex: 0 0 auto !important;
            min-width: 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    if logo_b64:
        hdr_logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="โลโก้ฟ้าใสตำนัว" />'
    else:
        hdr_logo_img = '<span style="font-size: 18px; font-weight: 800; color: #ffffff;">ฟ้าใส</span>'

    with st.container(key="cust_header"):
        # ---------- แถวบน: โซเชียล | แจ้งเตือน | สมาชิก ----------
        with st.container(key="row_top_header"):
            r1_social, r1_notif, r1_member = st.columns([1.5, 1, 1.2])
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
                    with st.popover("แจ้งเตือน", use_container_width=True):
                        render_notif_body()
                    if notif_count > 0:
                        st.markdown(f'<span class="hdr-badge">{notif_count if notif_count < 10 else "9+"}</span>', unsafe_allow_html=True)
            with r1_member:
                if current_member:
                    member_label = f"คุณ{current_member['first_name']}"
                else:
                    member_label = "สมาชิก"
                with st.popover(member_label, use_container_width=True):
                    render_member_body()

        # ---------- แถวกลาง: โลโก้ | ช่องค้นหา | ตะกร้า ----------
        with st.container(key="row_main_header"):
            r2_logo, r2_search, r2_cart = st.columns([2.5, 4.5, 1.3])
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
                    placeholder="ค้นหาเมนู เช่น ตำปู, ลาบหมู, คอหมูย่าง",
                    key="cust_search_kw",
                    label_visibility="collapsed"
                ).strip()
            with r2_cart:
                with st.container(key="cart_wrap"):
                    with st.popover("ตะกร้า", use_container_width=True):
                        render_cart_body()
                    if total_cart_qty > 0:
                        st.markdown(f'<span class="hdr-badge">{total_cart_qty if total_cart_qty < 100 else "99+"}</span>', unsafe_allow_html=True)

        # ---------- แถวล่าง: วัน เดือน ปี | ชื่อโต๊ะ | เปลี่ยนโต๊ะ ----------
        with st.container(key="row_bottom_header"):
            r3_date, r3_table, r3_switch = st.columns([2, 1, 1.2])
            with r3_date:
                st.markdown(f"""
                <div class="hdr-date">
                    <span class="hdr-date-full">{thai_date_str}</span>
                    <span class="hdr-date-short">วัน{thai_days[now_th.weekday()]} {now_th.day}/{now_th.month}/{now_th.year + 543}</span>
                </div>
                """, unsafe_allow_html=True)
            with r3_table:
                st.markdown(f'<div style="text-align: right;"><span class="hdr-table">{current_table_name}</span></div>', unsafe_allow_html=True)
            with r3_switch:
                # ปุ่มสลับ / เปลี่ยนโต๊ะอาหาร (สำหรับกรณีทดสอบโต๊ะอื่นๆ หรือลูกค้าเดินเข้าร้านเลือกโต๊ะเอง)
                with st.popover("เปลี่ยนโต๊ะ", use_container_width=True):
                    st.markdown("##### เลือกโต๊ะอาหารที่ท่านนั่ง")
                    st.caption("สามารถเลือกหมายเลขโต๊ะเพื่อสั่งอาหารของโต๊ะนั้นๆ ได้เลยค่ะ")
                    table_select_options = [f"โต๊ะที่ {num} ({table_names_map.get(num, f'โต๊ะที่ {num}')})" for num in valid_tables]
                    curr_idx = valid_tables.index(current_table_num) if current_table_num in valid_tables else 0
                    sel_new_t = st.selectbox("เลือกโต๊ะ:", table_select_options, index=curr_idx, key="sb_switch_table")
                    if st.button("ยืนยันเปลี่ยนโต๊ะ", type="primary", use_container_width=True, key="btn_confirm_switch_t"):
                        chosen_num = int(sel_new_t.split(" ")[1])
                        st.query_params["table"] = chosen_num
                        st.rerun()

    # ==========================================================================
    # แถบแสดงสถานะออเดอร์สดแบบเรียลไทม์ (อัปเดตอัตโนมัติทุก 3 วินาทีเมื่อครัวกดรับออเดอร์ / เสิร์ฟ)
    # ==========================================================================
    @st.fragment(run_every=3)
    def render_live_main_order_tracker():
        conn_lv = sqlite3.connect(DB_NAME)
        c_lv = conn_lv.cursor()
        c_lv.execute("""
            SELECT id, status, total_price, created_at, slip_image, slip_uploaded_at 
            FROM orders 
            WHERE table_id = ? AND status NOT IN ('paid', 'archived')
            ORDER BY id DESC
        """, (current_table_num,))
        live_orders = c_lv.fetchall()

        if not live_orders:
            conn_lv.close()
            return

        with st.container(border=True):
            st.markdown(f"**สถานะออเดอร์ปัจจุบัน ({current_table_name})** • :green[● อัปเดตสดอัตโนมัติ]")
            for oid, status, total, otime, slip_img, slip_time in live_orders:
                c_lv.execute("SELECT item_name, quantity, note, COALESCE(status, 'pending') FROM order_items WHERE order_id = ?", (oid,))
                items_lv = c_lv.fetchall()
                render_order_status_summary(oid, status, total, otime, items_lv)
                if slip_img:
                    st.markdown(f"<div style='color: #15803d; font-size: 0.88rem; font-weight: 700; margin-top: 4px;'>บิล #{oid}: แนบสลิปโอนเงินเรียบร้อยแล้ว (เวลา {slip_time or '-'}) กำลังรอพนักงานตรวจสอบยอดค่ะ</div>", unsafe_allow_html=True)
        conn_lv.close()

    render_live_main_order_tracker()

    # แถบปุ่มสแกนจ่าย / แนบสลิปด่วน (แยกอยู่นอก Fragment 3 วินาที เพื่อไม่ให้รบกวนขณะลูกค้ากำลังเลือกรูปสลิป)
    c.execute("""
        SELECT id, status, total_price, slip_image, slip_uploaded_at 
        FROM orders 
        WHERE table_id = ? AND status NOT IN ('paid', 'archived')
        ORDER BY id DESC LIMIT 1
    """, (current_table_num,))
    cur_active_pay = c.fetchone()
    
    if cur_active_pay:
        cap_id, cap_st, cap_tot, cap_slip, cap_slip_t = cur_active_pay
        with st.container(border=True):
            p_c1, p_c2 = st.columns([2.5, 1.3], gap="small")
            with p_c1:
                if cap_slip:
                    st.markdown(f"**ชำระเงินบิล #{cap_id}** — <span style='color: #15803d; font-weight: bold;'>แนบสลิปเรียบร้อยแล้ว</span> (฿{int(cap_tot):,})", unsafe_allow_html=True)
                    st.caption("พนักงานแคชเชียร์กำลังตรวจยอดเงินและเตรียมเช็คบิลให้ค่ะ")
                else:
                    st.markdown(f"**ชำระเงินบิล #{cap_id}** — ยอดชำระสุทธิ: <span style='color: #ea580c; font-weight: bold; font-size: 1.15rem;'>฿{int(cap_tot):,}</span>", unsafe_allow_html=True)
                    st.caption("สามารถสแกน QR โอนเงินและแนบสลิปได้ทันทีค่ะ")
            with p_c2:
                btn_pay_label = "ดู / เปลี่ยนสลิป" if cap_slip else "สแกนจ่าย / แนบสลิป"
                with st.popover(btn_pay_label, use_container_width=True):
                    render_slip_payment_block(cap_id, cap_tot, cap_slip, cap_slip_t, is_main_card=True)

    # ==========================================================================
    # เลือกหมวดหมู่อาหาร / ผลการค้นหา
    # ==========================================================================
    st.markdown("<p style='text-align: center; font-weight: 600; color: #44403c; margin-bottom: 4px; font-size: 1.05rem;'>เลือกหมวดหมู่อาหาร</p>", unsafe_allow_html=True)
    default_cat = categories[0] if categories else "ทั้งหมด"
    sel_cat = st.pills("เลือกหมวดหมู่อาหาร:", categories + ["ทั้งหมด"], default=default_cat, key="pills_cat_sel", label_visibility="collapsed")
    if not sel_cat:
        sel_cat = default_cat

    # แสดงรายการเมนูอาหาร แถวการ์ดแนวนอน (กดได้ทุกรายการ พร้อม Stepper -/+ บนการ์ดโดยตรง)
    # หากลูกค้าพิมพ์คำค้นหา จะค้นจากทุกหมวดหมู่ (ทั้งชื่อเมนูและคำอธิบาย)
    if search_kw:
        kw_low = search_kw.lower()
        filtered_menus = [m for m in all_menus if kw_low in (m[1] or "").lower() or kw_low in (m[5] or "").lower()]
        st.markdown(f"<div style='color: #57534e; margin-bottom: 8px;'>ผลการค้นหา <b>\"{search_kw}\"</b> พบ <b style='color: #ea580c;'>{len(filtered_menus)}</b> รายการ (ค้นหาจากทุกหมวดหมู่)</div>", unsafe_allow_html=True)
        if not filtered_menus:
            st.warning("ไม่พบเมนูที่ค้นหา ลองพิมพ์คำอื่น หรือเลือกจากหมวดหมู่ด้านบนค่ะ")
    else:
        filtered_menus = all_menus if sel_cat == "ทั้งหมด" else [m for m in all_menus if m[2] == sel_cat]

    # สไตล์ CSS บังคับขนาดการ์ดอาหารทุกแถวและทุกคอลัมน์ให้เท่ากันเป๊ะ แถวสุดท้ายไม่ขยายเกินแถวด้านบน
    st.markdown("""
    <style>
    /* Container แนวนอนหลักและ Wrapper ต้องกว้างเต็ม 100% เสมอ */
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
    </style>
    """, unsafe_allow_html=True)

    # แสดงรายการเมนูอาหารแบบ Responsive Grid ขยายเต็มความกว้างหน้าจอของแต่ละอุปกรณ์
    grid_container = st.container(horizontal=True, wrap=True, gap=10, key="menu_grid_flex")
    with grid_container:
        for m_id, name, cat, price, img, desc in filtered_menus:
            with st.container(border=True, key=f"fcard_{m_id}"):
                st.markdown("<div class='fcard-marker' style='display:none;'></div>", unsafe_allow_html=True)
                # รูปภาพอาหารขนาดกะทัดรัด (จัดวางกึ่งกลาง ขยายความกว้างเต็มการ์ด)
                valid_img = get_valid_image_path(img)
                if valid_img:
                    try:
                        st.image(valid_img, width="stretch")
                    except TypeError:
                        st.image(valid_img, use_container_width=True)
                else:
                    st.markdown("<div class='no-img-box' style='font-size: 13px; color: #9a3412;'>ไม่มีรูปภาพ</div>", unsafe_allow_html=True)
                
                # ชื่ออาหาร & หมวดหมู่ (จัดวางกึ่งกลาง)
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 700; color: #1c1917; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; text-align: center;' title='{name}'>{name}</div>", unsafe_allow_html=True)
                
                # ราคาอาหารแบบ Pill สดใส (จัดวางกึ่งกลาง)
                st.markdown(f"<div style='margin: 2px 0 6px 0; width: 100%; text-align: center;'><span style='color: #ea580c; font-weight: 800; font-size: 1.08rem;'>฿{int(price)}</span> <span style='font-size: 0.72rem; color: #78716c;'>/จาน</span></div>", unsafe_allow_html=True)
                
                # ปุ่ม เพิ่ม / ปรับจำนวน (Stepper) เต็มความกว้างการ์ด
                cur_qty = st.session_state.cart.get(name, {}).get('qty', 0)
                if cur_qty == 0:
                    st.button("เพิ่ม", key=f"btn_add_menu_{m_id}", on_click=add_to_cart_item, args=(name, price), use_container_width=True, type="primary")
                else:
                    c_m, c_q, c_p = st.columns([1, 1.2, 1], gap="small")
                    with c_m:
                        st.button("-", key=f"btn_dec_card_{m_id}", on_click=dec_from_cart_item, args=(name,), use_container_width=True)
                    with c_q:
                        st.markdown(f"<div style='text-align: center; font-weight: 800; line-height: 34px; color: #ffffff; font-size: 0.95rem; background: linear-gradient(135deg, #ea580c, #dc2626); border-radius: 8px; box-shadow: 0 2px 6px rgba(234, 88, 12, 0.30);'>{cur_qty}</div>", unsafe_allow_html=True)
                    with c_p:
                        st.button("+", key=f"btn_inc_card_{m_id}", on_click=add_to_cart_item, args=(name, price), use_container_width=True, type="primary")

    conn.close()

    # Footer ด้านล่างสุด
    render_app_footer()

