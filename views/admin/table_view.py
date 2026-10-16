# ==============================================================================
# จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (Table Management & QR View)
# ==============================================================================
import sqlite3
from urllib.parse import quote
import streamlit as st
from config import DB_NAME, get_current_base_url

def render_table_tab():
    """แสดงแท็บจัดการโต๊ะอาหาร เพิ่ม/ลบโต๊ะ สร้าง QR Code และเคลียร์โต๊ะ"""
    st.subheader("จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR-Code)")
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
    st.markdown("### 1. เพิ่ม / ลบ โต๊ะอาหารในร้าน")
    t_c1, t_c2 = st.columns(2)
    
    with t_c1:
        with st.container(border=True):
            st.markdown("#### เพิ่มโต๊ะใหม่")
            st.caption("เมื่อเพิ่มแล้ว ระบบจะสร้าง QR-Code และลิงก์สั่งอาหารของโต๊ะนั้นให้ทันที")
            next_t_num = (max(existing_nums) + 1) if existing_nums else 1
            new_t_num = st.number_input("หมายเลขโต๊ะที่จะเพิ่ม:", min_value=1, max_value=999, value=next_t_num, step=1, key="add_t_num_input")
            new_t_name = st.text_input("ชื่อเรียกโต๊ะ:", value=f"โต๊ะที่ {new_t_num}", key="add_t_name_input")
            
            if st.button("ยืนยันเพิ่มโต๊ะและสร้าง QR-Code", key="btn_add_new_table", type="primary", use_container_width=True):
                if new_t_num in existing_nums:
                    st.error(f"หมายเลขโต๊ะ {new_t_num} มีอยู่ในระบบแล้วค่ะ")
                else:
                    c_tb.execute("INSERT INTO tables (table_number, name) VALUES (?, ?)", (new_t_num, new_t_name))
                    conn_tb.commit()
                    st.success(f"เพิ่ม '{new_t_name}' สำเร็จ พร้อมเปิดใช้งาน QR-Code เรียบร้อยแล้วค่ะ!")
                    st.rerun()

    with t_c2:
        with st.container(border=True):
            st.markdown("#### ลบโต๊ะอาหาร")
            st.caption("ลบโต๊ะที่ไม่ใช้งานออกจากระบบ")
            if existing_nums:
                table_options = [f"โต๊ะที่ {r[0]} ({r[1]})" for r in table_statuses]
                table_to_del_str = st.selectbox("เลือกโต๊ะที่ต้องการลบ:", table_options, key="select_del_t")
                del_t_num = int(table_to_del_str.split(" ")[1])
                
                if st.button(f"ยืนยันลบโต๊ะที่ {del_t_num}", key="btn_del_table", use_container_width=True):
                    c_tb.execute("DELETE FROM tables WHERE table_number = ?", (del_t_num,))
                    conn_tb.commit()
                    st.warning(f"ลบโต๊ะที่ {del_t_num} ออกจากระบบเรียบร้อยแล้ว")
                    st.rerun()
            else:
                st.info("ปัจจุบันยังไม่มีโต๊ะอาหารในระบบ")
    
    st.write("---")

    # ส่วนที่ 2: รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & เคลียร์สถานะโต๊ะ
    st.markdown("### 2. รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & ล้างสถานะโต๊ะ")
    
    if not table_statuses:
        st.info("**ขณะนี้ยังไม่มีโต๊ะอาหารในร้าน** (ค่าเริ่มต้น 0 โต๊ะ)\n\nสามารถเพิ่มโต๊ะใหม่ได้ที่แบบฟอร์ม **'เพิ่มโต๊ะใหม่'** ด้านบนค่ะ เมื่อเพิ่มแล้ว QR-Code สำหรับติดโต๊ะและระบบสั่งอาหารจะแสดงที่นี่ทันที")
    else:
        total_tbls = len(table_statuses)
        busy_tbls = sum(1 for r in table_statuses if (r[2] > 0 or r[3] > 0))
        free_tbls = total_tbls - busy_tbls
        
        # สรุปภาพรวมของโต๊ะ
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("โต๊ะอาหารทั้งหมด", f"{total_tbls} โต๊ะ")
        col_m2.metric("โต๊ะว่างพร้อมรับลูกค้า", f"{free_tbls} โต๊ะ")
        col_m3.metric("มีลูกค้า / รอเคลียร์", f"{busy_tbls} โต๊ะ")

        # ปุ่มล้างทุกโต๊ะที่เช็คบิลแล้วพร้อมกัน
        total_paid_orders = sum(r[3] for r in table_statuses)
        if total_paid_orders > 0:
            if st.button("ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วพร้อมกันทั้งหมด", type="primary", use_container_width=True):
                c_tb.execute("UPDATE orders SET status = 'archived' WHERE status = 'paid'")
                conn_tb.commit()
                st.toast("ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วเรียบร้อย!")
                st.rerun()
            st.write("")

        st.caption("คำแนะนำ: พิมพ์หรือเปิดภาพ **QR-Code** ด้านล่างนี้ไปติดไว้ที่โต๊ะอาหาร ลูกค้าสแกนเพื่อเปิดเมนูสั่งอาหารได้ทันที")
        
        clr_cols = st.columns(3)
        for idx, (t_no, t_name, act_cnt, paid_cnt) in enumerate(table_statuses):
            with clr_cols[idx % 3]:
                with st.container(border=True):
                    # หัวการ์ดโต๊ะและสถานะแบบสีสันสดใส มีมิติ
                    if act_cnt > 0:
                        hdr_gradient = "linear-gradient(135deg, #f97316 0%, #ea580c 100%)"
                        badge_html = "<span style='background: #fef3c7; color: #9a3412; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'>มีออเดอร์ค้าง</span>"
                        stat_text = f"<span style='color: #ea580c; font-weight: 700;'>มีออเดอร์ค้าง {act_cnt} บิล (กำลังทำ/รอเสิร์ฟ)</span>"
                    elif paid_cnt > 0:
                        hdr_gradient = "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
                        badge_html = "<span style='background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'>เช็คบิลแล้ว</span>"
                        stat_text = f"<span style='color: #2563eb; font-weight: 700;'>เช็คบิลแล้ว {paid_cnt} บิล (รอเคลียร์โต๊ะ)</span>"
                    else:
                        hdr_gradient = "linear-gradient(135deg, #10b981 0%, #059669 100%)"
                        badge_html = "<span style='background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700;'>โต๊ะว่าง</span>"
                        stat_text = "<span style='color: #059669; font-weight: 700;'>โต๊ะว่าง (พร้อมรับลูกค้า)</span>"

                    st.markdown(f"""
                    <div style="background: {hdr_gradient}; padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #ffffff; font-weight: 800; font-size: 1.15rem;">{t_name}</span>
                        {badge_html}
                    </div>
                    <div style="font-size: 0.9rem; margin-bottom: 8px;">สถานะ: {stat_text}</div>
                    """, unsafe_allow_html=True)

                    # ลิงก์สำหรับลูกค้าโต๊ะนี้ (รูปแบบสะอาด: ?table=หมายเลขโต๊ะ)
                    cust_table_url = f"{base_url_for_qr}/?table={t_no}"
                    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={quote(cust_table_url)}&margin=8"
                    
                    # แสดงภาพ QR Code (ลดขนาดลงประมาณ 50% จัดกึ่งกลางการ์ด)
                    col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
                    with col_q2:
                        st.image(qr_image_url, caption=f"QR-Code {t_name}", use_container_width=True)
                    
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
                    if st.button(f"ล้างสถานะโต๊ะ {t_no} (รับลูกค้าใหม่)", key=f"btn_clr_tbl_{t_no}", use_container_width=True, type=btn_type):
                        c_tb.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_no,))
                        conn_tb.commit()
                        st.toast(f"ล้างสถานะ '{t_name}' เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!")
                        st.rerun()

                    # ปุ่มลบโต๊ะ
                    with st.popover(f"ลบ {t_name}"):
                        st.markdown(f"ยืนยันการลบ **{t_name}** ออกจากระบบ?")
                        if st.button(f"ยืนยันลบโต๊ะ {t_no}", key=f"btn_pop_del_{t_no}", type="primary", use_container_width=True):
                            c_tb.execute("DELETE FROM tables WHERE table_number = ?", (t_no,))
                            conn_tb.commit()
                            st.warning(f"ลบ {t_name} เรียบร้อยแล้วค่ะ")
                            st.rerun()

    conn_tb.close()


