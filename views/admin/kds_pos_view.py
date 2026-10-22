# ==============================================================================
# จอครัว & เคาน์เตอร์คิดเงิน (KDS & POS Dashboard)
# ==============================================================================
import os
import sqlite3
import streamlit as st
from config import DB_NAME, get_thai_now, get_valid_image_path
from utils.audio import play_order_sound
from utils.receipt import render_receipt_box, render_counter_qr_payment_card

# ==============================================================================
# จอครัว & เคาน์เตอร์คิดเงิน (Fragment ทำงานอัตโนมัติทุก 3 วินาที)
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
        st.toast(f"มีออเดอร์ใหม่ #{cur_max} เข้ามาในครัวแล้วค่ะ!")
        st.warning(f"**มีออเดอร์ใหม่ #{cur_max} เพิ่งส่งเข้ามาในครัว!** กำลังรอให้เตรียมอาหาร")

    # แถบแสดงสถานะอัปเดตสดแบบเรียลไทม์
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown(f"**สถานะระบบ:** :green[**● เชื่อมต่อสด • อัปเดตออเดอร์อัตโนมัติทุก 3 วินาที**] <span style='color: #64748b; font-size: 0.85rem;'>(เวลาปัจจุบัน: {get_thai_now().strftime('%H:%M:%S')})</span>", unsafe_allow_html=True)
    with top_c2:
        if st.button("ทดสอบเสียงกระดิ่ง", key="btn_test_sound", use_container_width=True):
            play_order_sound()
            st.toast("ทดสอบเสียงกระดิ่งเตือนออเดอร์แล้ว")

    c.execute("SELECT COALESCE(SUM(total_price), 0), COUNT(*) FROM orders WHERE status IN ('paid', 'archived')")
    revenue, paid_cnt = c.fetchone()
    c.execute("SELECT COUNT(*), COUNT(DISTINCT table_id) FROM orders WHERE status NOT IN ('paid', 'archived')")
    active_cnt, active_tables = c.fetchone()
    
    # Responsive Metrics
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("ยอดขายรวม", f"฿{int(revenue):,}")
    s2.metric("กำลังปรุง/เสิร์ฟ", f"{active_cnt} บิล")
    s3.metric("นั่งทาน", f"{active_tables} โต๊ะ")
    s4.metric("เช็คบิลแล้ว", f"{paid_cnt} บิล")
    
    st.write("---")
    
    # หากมีการกดเช็คบิล/ดูใบเสร็จ ให้แสดงกล่องใบเสร็จอย่างย่อด้านบนสุด
    active_rec_id = st.session_state.get('active_receipt_oid')
    if active_rec_id:
        render_receipt_box(active_rec_id, conn)
        st.write("---")

    c.execute('''
        SELECT id, table_id, status, total_price, created_at, slip_image, slip_uploaded_at 
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
        st.success("ไม่มีออเดอร์ค้างในครัว ระบบพร้อมรับออเดอร์ใหม่เสมอค่ะ")
    else:
        grid_cols = st.columns(3)
        for idx, (oid, t_id, st_code, total, otime, slip_img, slip_time) in enumerate(orders_to_manage):
            with grid_cols[idx % 3]:
                with st.container(border=True):
                    # หัวการ์ดโต๊ะในจอครัวแบบมีสีสันสดใสไล่เฉด (Vibrant KDS Table Header)
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); padding: 8px 14px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 3px 10px rgba(234, 88, 12, 0.28); display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #ffffff; font-weight: 800; font-size: 1.25rem; letter-spacing: 0.5px;">โต๊ะที่ {t_id}</span>
                        <span style="background: #ffffff; color: #ea580c; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 0.85rem;">บิล #{oid}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    # แสดงป้ายสถานะรวมของบิล
                    st_badge_map = {
                        'pending': ('รอรับออเดอร์', '#fff7ed', '#c2410c', '#fdba74'),
                        'accepted': ('รับออเดอร์แล้ว • กำลังปรุง', '#eff6ff', '#1d4ed8', '#93c5fd'),
                        'cooked': ('ปรุงเสร็จบางส่วน • กำลังเสิร์ฟ', '#f3e8ff', '#7e22ce', '#d8b4fe'),
                        'served': ('เสิร์ฟครบทุกเมนูแล้ว', '#f0fdf4', '#15803d', '#86efac'),
                    }
                    sb_txt, sb_bg, sb_col, sb_bdr = st_badge_map.get(st_code, ('รอดำเนินการ', '#f8fafc', '#475569', '#cbd5e1'))
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: #64748b; font-size: 0.82rem;">เวลาสั่ง: {otime}</span>
                        <span style="background: {sb_bg}; color: {sb_col}; border: 1.5px solid {sb_bdr}; padding: 2px 10px; border-radius: 999px; font-size: 0.82rem; font-weight: 700;">{sb_txt}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    # ปุ่มรับออเดอร์ (แจ้งไปยังหน้าจอลูกค้าทันทีว่าครัวรับออเดอร์และกำลังปรุงอาหาร)
                    if st_code == 'pending':
                        if st.button("รับออเดอร์ (เริ่มปรุงอาหาร)", key=f"btn_accept_ord_{oid}", type="primary", use_container_width=True):
                            c.execute("UPDATE orders SET status = 'accepted' WHERE id = ?", (oid,))
                            c.execute("UPDATE order_items SET status = 'accepted' WHERE order_id = ? AND (status IS NULL OR status = 'pending')", (oid,))
                            conn.commit()
                            st.toast(f"รับออเดอร์ #{oid} (โต๊ะที่ {t_id}) เรียบร้อยแล้ว แจ้งเตือนไปยังหน้าจอลูกค้าแล้วค่ะ!")
                            st.rerun()
                    
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
                    
                    st.markdown("**รายการอาหารในบิล:**")
                    for oi_id, iname, iqty, inote, iprice, istatus, dish_img in items_in_order:
                        with st.container(border=True):
                            it_c1, it_c2 = st.columns([1.1, 2.3])
                            with it_c1:
                                valid_dish_img = get_valid_image_path(dish_img)
                                if valid_dish_img:
                                    st.image(valid_dish_img, use_container_width=True)
                                else:
                                    st.markdown("<div style='font-size: 13px; text-align: center; color: #9a3412; font-weight: 600; line-height: 60px;'>ไม่มีรูป</div>", unsafe_allow_html=True)
                            with it_c2:
                                st.markdown(f"**{iname}** <span style='color: #ea580c; font-weight: bold;'>x{iqty}</span>", unsafe_allow_html=True)
                                st.caption(f"฿{int(iprice * iqty):,}")
                                if inote:
                                    st.caption(f"หมายเหตุ: {inote}")
                                
                                if istatus == 'pending':
                                    st.markdown("<span style='background: #fff7ed; color: #c2410c; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #fdba74;'>รอรับออเดอร์</span>", unsafe_allow_html=True)
                                elif istatus == 'accepted':
                                    st.markdown("<span style='background: #eff6ff; color: #1d4ed8; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #93c5fd;'>กำลังปรุง</span>", unsafe_allow_html=True)
                                elif istatus == 'cooked':
                                    st.markdown("<span style='background: #f3e8ff; color: #7e22ce; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #d8b4fe;'>ปรุงเสร็จแล้ว</span>", unsafe_allow_html=True)
                                elif istatus == 'served':
                                    st.markdown("<span style='background: #f0fdf4; color: #15803d; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #86efac;'>เสิร์ฟแล้ว</span>", unsafe_allow_html=True)
                            
                            # ปุ่มเปลี่ยนสถานะแต่ละเมนู: เสร็จแล้ว / นำเสิร์ฟแล้ว
                            act_c1, act_c2 = st.columns(2)
                            if istatus in ('pending', 'accepted'):
                                with act_c1:
                                    if st.button("เสร็จ", key=f"btn_ck_{oi_id}", use_container_width=True, help="เปลี่ยนสถานะเป็นปรุงเสร็จแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'cooked' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'cooked' WHERE id = ? AND status IN ('pending', 'accepted')", (oid,))
                                        conn.commit()
                                        st.rerun()
                                with act_c2:
                                    if st.button("เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
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
                                    if st.button("เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'served' WHERE id = ?", (oi_id,))
                                        c.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ? AND status != 'served'", (oid,))
                                        if c.fetchone()[0] == 0:
                                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                                        else:
                                            c.execute("UPDATE orders SET status = 'cooked' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                            elif istatus == 'served':
                                with act_c1:
                                    st.write("")
                                with act_c2:
                                    if st.button("ยกเลิก", key=f"btn_un_{oi_id}", use_container_width=True, help="ย้อนกลับเป็นกำลังปรุง"):
                                        c.execute("UPDATE order_items SET status = 'accepted' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'accepted' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                    
                    # ปุ่มทางลัด: เสิร์ฟทุกเมนูพร้อมกัน
                    if not all_items_served:
                        if st.button("เสิร์ฟทุกเมนูทันที", key=f"btn_all_srv_{oid}", use_container_width=True):
                            c.execute("UPDATE order_items SET status = 'served' WHERE order_id = ?", (oid,))
                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                            conn.commit()
                            st.toast(f"เสิร์ฟอาหารโต๊ะ {t_id} ครบทุกเมนูแล้วค่ะ!")
                            st.rerun()

                    st.write("---")
                    st.markdown(f"**ยอดรวม: <span style='color: #ea580c; font-size: 1.15rem; font-weight: bold;'>฿{int(total):,}</span>**", unsafe_allow_html=True)
                    with st.popover(f"แสดง QR โอนเงิน (฿{int(total):,})", use_container_width=True):
                        render_counter_qr_payment_card(t_id, oid, total)
                    
                    # แสดงสถานะสลิปที่ลูกค้าแนบมา
                    if slip_img and os.path.exists(slip_img):
                        st.markdown(f"""
                        <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 8px; padding: 6px 10px; margin: 6px 0;">
                            <span style="color: #15803d; font-weight: bold; font-size: 0.88rem;">ลูกค้าแนบสลิปแล้ว</span>
                            <span style="color: #64748b; font-size: 0.78rem; display: block;">เวลาที่แนบ: {slip_time or '-'}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        with st.popover("ตรวจสอบสลิปโอนเงิน", use_container_width=True):
                            st.markdown(f"##### สลิปโอนเงิน โต๊ะที่ {t_id} (บิล #{oid})")
                            st.caption(f"ยอดที่ต้องชำระ: ฿{int(total):,}")
                            st.image(slip_img, use_container_width=True)

                    # Requirement: เช็คบิลได้เฉพาะเมื่อเสิร์ฟครบทุกเมนูแล้วเท่านั้น
                    if not all_items_served:
                        st.warning(f"เสิร์ฟแล้ว {served_items}/{total_items} เมนู (ปุ่มเช็คบิลจะเปิดเมื่อเสิร์ฟครบ)")
                        st.button(f"เช็คบิลโต๊ะ {t_id} (รอเสิร์ฟครบ)", key=f"btn_bill_{oid}", disabled=True, use_container_width=True)
                    else:
                        st.success(f"เสิร์ฟครบ {served_items}/{total_items} เมนูแล้ว พร้อมเช็คบิลค่ะ!")
                        if st.button(f"เช็คบิล & ออกใบเสร็จอย่างย่อ (โต๊ะ {t_id})", key=f"btn_bill_{oid}", type="primary", use_container_width=True):
                            st.session_state['active_receipt_oid'] = oid
                            st.rerun()

                    # ปุ่มเคลียร์โต๊ะรับลูกค้าใหม่
                    st.write("")
                    if st.button(f"เคลียร์โต๊ะ {t_id}", key=f"adm_clr_{oid}", use_container_width=True, help="ล้างสถานะเพื่อรับลูกค้าใหม่"):
                        c.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_id,))
                        conn.commit()
                        st.toast(f"เคลียร์โต๊ะ {t_id} เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!")
                        st.rerun()

    # Expander: ประวัติบิลที่ชำระแล้ววันนี้
    st.write("---")
    with st.expander("ประวัติบิลที่ชำระแล้ววันนี้ (ดู/พิมพ์ใบเสร็จย้อนหลัง)", expanded=False):
        c.execute("""
            SELECT id, table_id, total_price, created_at, status, slip_image 
            FROM orders 
            WHERE status IN ('paid', 'archived')
            ORDER BY id DESC LIMIT 15
        """)
        past_orders = c.fetchall()
        if not past_orders:
            st.info("ยังไม่มีบิลที่ชำระแล้วในวันนี้ค่ะ")
        else:
            for p_id, p_tid, p_tot, p_time, p_st, p_slip in past_orders:
                st_p_col1, st_p_col2, st_p_col3 = st.columns([2, 1.2, 1.8])
                st_p_col1.markdown(f"**บิล #{p_id}** — โต๊ะที่ {p_tid} (เวลา: {p_time})")
                st_p_col2.markdown(f"**฿{int(p_tot):,}**")
                with st_p_col3:
                    if p_slip and os.path.exists(p_slip):
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("พิมพ์ใบเสร็จ", key=f"btn_reprint_{p_id}", use_container_width=True):
                                st.session_state['active_receipt_oid'] = p_id
                                st.rerun()
                        with b_col2:
                            with st.popover("สลิป", use_container_width=True):
                                st.image(p_slip, caption=f"สลิปบิล #{p_id}", use_container_width=True)
                    else:
                        if st.button("พิมพ์ใบเสร็จ", key=f"btn_reprint_{p_id}", use_container_width=True):
                            st.session_state['active_receipt_oid'] = p_id
                            st.rerun()
                        
    conn.close()


