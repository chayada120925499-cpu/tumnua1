# ==============================================================================
# จัดการรายการอาหาร (Menu Catalog Management View)
# ==============================================================================
import os
import sqlite3
import streamlit as st
from config import DB_NAME, get_valid_image_path

def render_menu_tab():
    """แสดงแท็บจัดการรายการอาหาร เพิ่ม ลบ ค้นหา แก้ไขราคาต้นทุน"""
    st.subheader("จัดการรายการอาหาร (เพิ่ม / ลบ / ค้นหา)")
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
    with st.expander("เพิ่มรายการอาหารใหม่", expanded=True):
        st.markdown("#### กรอกข้อมูลเมนูใหม่")
        with st.form("form_add_new_menu", clear_on_submit=True):
            col_n1, col_n2 = st.columns([1.5, 1])
            with col_n1:
                new_name = st.text_input("ชื่อเมนูอาหาร *", placeholder="เช่น ตำถาดทะเลเดือด, กุ้งแช่น้ำปลา", key="in_new_menu_name")
                
                cat_select_list = all_cat_options + ["+ เพิ่มหมวดหมู่ใหม่..."]
                sel_cat_choice = st.selectbox("หมวดหมู่อาหาร *", cat_select_list, index=0, key="in_new_menu_cat_sel")
                
                custom_cat_val = ""
                if sel_cat_choice == "+ เพิ่มหมวดหมู่ใหม่...":
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

            btn_add_menu = st.form_submit_button("บันทึกและเพิ่มรายการอาหาร", type="primary", use_container_width=True)
            if btn_add_menu:
                final_name = new_name.strip()
                final_cat = custom_cat_val.strip() if sel_cat_choice == "+ เพิ่มหมวดหมู่ใหม่..." else sel_cat_choice
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
                        st.error(f"มีเมนูชื่อ '{final_name}' อยู่ในระบบแล้ว กรุณาใช้ชื่ออื่นค่ะ")
                    else:
                        try:
                            c_mng.execute(
                                "INSERT INTO menu_items (name, category, price, cost, image, description) VALUES (?, ?, ?, ?, ?, ?)",
                                (final_name, final_cat, new_price, new_cost, final_img, final_desc)
                            )
                            conn_mng.commit()
                            st.success(f"เพิ่มเมนู **'{final_name}'** (หมวด: {final_cat}, ราคา: ฿{new_price:,.2f}) สำเร็จเรียบร้อยแล้วค่ะ!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"เกิดข้อผิดพลาดในการบันทึก: {err}")

    st.write("---")

    # =========================================================
    # 2. รายการเมนูอาหารทั้งหมด & ค้นหา & ลบเมนู
    # =========================================================
    st.markdown("### รายการอาหารทั้งหมดในระบบ & จัดการลบ")
    
    f_c1, f_c2 = st.columns([2, 1.5])
    with f_c1:
        search_menu_kw = st.text_input("ค้นหาตามชื่อเมนู หรือคำอธิบาย:", placeholder="พิมพ์ชื่อเมนูเพื่อค้นหา...", key="in_search_menu_kw").strip()
    with f_c2:
        filter_cat_choice = st.selectbox("กรองตามหมวดหมู่:", ["ทั้งหมด"] + all_cat_options, key="sel_filter_cat_choice")

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
    m_stat1.metric("รายการทั้งหมด", f"{tot_cnt} เมนู")
    m_stat2.metric("ตรงตามตัวกรอง", f"{len(found_menus)} เมนู")
    m_stat3.metric("ราคาเฉลี่ย", f"฿{avg_p:,.1f}")
    m_stat4.metric("ต้นทุนเฉลี่ย", f"฿{avg_c:,.1f}")

    st.caption(f"แสดงผล {len(found_menus)} รายการ (กดที่ปุ่ม 'ลบ' เพื่อลบเมนูที่ไม่ต้องการ)")

    if not found_menus:
        st.warning("ไม่พบรายการอาหารที่ตรงกับเงื่อนไขการค้นหา")
    else:
        for item_id, m_name, m_cat, m_price, m_cost, m_img, m_desc in found_menus:
            with st.container(border=True):
                row_img, row_info, row_price, row_action = st.columns([1.1, 3.2, 1.8, 1.1])
                
                with row_img:
                    valid_m_img = get_valid_image_path(m_img)
                    if valid_m_img:
                        st.image(valid_m_img, use_container_width=True)
                    else:
                        st.markdown("<div style='font-size: 13px; color: #9a3412; font-weight: 600; text-align: center; line-height: 65px; background: #fff7ed; border-radius: 8px;'>ไม่มีรูป</div>", unsafe_allow_html=True)
                
                with row_info:
                    st.markdown(f"**{m_name}** <span style='font-size: 0.8rem; background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 999px; margin-left: 6px; font-weight: 600;'>{m_cat}</span>", unsafe_allow_html=True)
                    if m_desc:
                        st.caption(m_desc)
                    if m_img:
                        st.caption(f"รูปภาพ: `{m_img}`")
                
                with row_price:
                    st.markdown(f"ราคา: <b style='color: #ea580c; font-size: 1.1rem;'>฿{m_price:,.2f}</b>", unsafe_allow_html=True)
                    p_margin = m_price - (m_cost or 0)
                    st.caption(f"ต้นทุน: ฿{m_cost or 0:,.2f} (กำไร: ฿{p_margin:,.2f})")
                
                with row_action:
                    with st.popover("ลบ", use_container_width=True):
                        st.markdown(f"**ยืนยันลบเมนู?**")
                        st.caption(f"ต้องการลบ **'{m_name}'** ออกจากระบบหรือไม่?")
                        if st.button("ยืนยันลบ", key=f"btn_del_menu_{item_id}", type="primary", use_container_width=True):
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


