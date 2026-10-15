# ==============================================================================
# ประวัติลูกค้า & ระบบสมาชิกสะสมแต้ม (Customer CRM View)
# ==============================================================================
import sqlite3
import streamlit as st
from config import DB_NAME, get_thai_now

def render_member_tab():
    """แสดงแท็บประวัติลูกค้าและระบบสมาชิกสะสมแต้ม"""
    st.subheader("ประวัติลูกค้า & ระบบสมาชิกสะสมแต้ม")
    st.caption("ดูข้อมูลสมาชิก จัดการคะแนนสะสม เรียงลำดับจากคะแนนมากไปน้อย และสมัครสมาชิกใหม่หน้าร้าน")
    
    conn_mem = sqlite3.connect(DB_NAME)
    c_mem = conn_mem.cursor()

    # ฟอร์มสมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)
    with st.expander("สมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)", expanded=False):
        st.markdown("##### กรอกข้อมูลสมาชิกลูกค้า")
        st.caption("ข้อมูลที่ใช้: ชื่อ, นามสกุล และหมายเลขโทรศัพท์")
        mf_c1, mf_c2, mf_c3 = st.columns(3)
        with mf_c1:
            adm_fname = st.text_input("ชื่อ:", key="adm_reg_fname", placeholder="ชื่อจริง")
        with mf_c2:
            adm_lname = st.text_input("นามสกุล:", key="adm_reg_lname", placeholder="นามสกุล")
        with mf_c3:
            adm_phone = st.text_input("หมายเลขโทรศัพท์:", key="adm_reg_phone", placeholder="เช่น 0937734851")
            
        if st.button("บันทึกข้อมูลสมาชิก", key="btn_adm_save_member", type="primary", use_container_width=True):
            cl_adm_ph = adm_phone.strip().replace("-", "").replace(" ", "")
            if not adm_fname.strip() or not adm_lname.strip() or not cl_adm_ph:
                st.error("กรุณากรอกข้อมูล ชื่อ นามสกุล และหมายเลขโทรศัพท์ให้ครบถ้วนค่ะ")
            else:
                c_mem.execute("SELECT id FROM members WHERE phone = ?", (cl_adm_ph,))
                if c_mem.fetchone():
                    st.error(f"หมายเลขโทรศัพท์ {cl_adm_ph} มีอยู่ในระบบสมาชิกแล้วค่ะ")
                else:
                    reg_now = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                    c_mem.execute(
                        "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, 0, ?)",
                        (adm_fname.strip(), adm_lname.strip(), cl_adm_ph, reg_now)
                    )
                    conn_mem.commit()
                    st.success(f"บันทึกสมาชิก 'คุณ {adm_fname} {adm_lname}' เรียบร้อยแล้วค่ะ!")
                    st.rerun()

    st.write("---")

    # ช่องค้นหาลูกค้า
    search_kw = st.text_input("ค้นหาลูกค้า (ชื่อ, นามสกุล หรือ เบอร์โทรศัพท์):", placeholder="พิมพ์คำค้นหา...", key="mem_search_input")
    kw_pattern = f"%{search_kw.strip()}%"

    # ดึงรายชื่อลูกค้า เรียงตามคะแนนสะสมจากมากไปน้อย (ORDER BY points DESC)
    c_mem.execute("""
        SELECT 
            m.id, 
            m.first_name, 
            m.last_name, 
            m.phone, 
            m.points, 
            m.created_at,
            COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN o.id END) as paid_orders,
            COALESCE(SUM(CASE WHEN o.status = 'paid' THEN o.total_price ELSE 0 END), 0) as total_spent
        FROM members m
        LEFT JOIN orders o ON m.phone = o.member_phone
        WHERE (m.first_name LIKE ? OR m.last_name LIKE ? OR m.phone LIKE ?)
        GROUP BY m.id
        ORDER BY m.points DESC, total_spent DESC, m.id ASC
    """, (kw_pattern, kw_pattern, kw_pattern))
    members_list = c_mem.fetchall()

    # สถิติภาพรวมสมาชิก
    c_mem.execute("SELECT COUNT(*), COALESCE(SUM(points), 0) FROM members")
    tot_m_cnt, tot_pts_sum = c_mem.fetchone()

    sm1, sm2, sm3 = st.columns(3)
    sm1.metric("สมาชิกทั้งหมด", f"{tot_m_cnt} คน")
    sm2.metric("คะแนนสะสมรวมทั้งระบบ", f"{tot_pts_sum:,} แต้ม")
    top_member_txt = f"{members_list[0][1]} {members_list[0][2]} ({members_list[0][4]} แต้ม)" if members_list else "-"
    sm3.metric("คะแนนสูงสุด", top_member_txt)

    st.markdown(f"### รายชื่อสมาชิกลูกค้า (เรียงตามคะแนนสะสมมากที่สุด)")
    st.caption("กฎคะแนน: ทุก ๆ 100 บาท (ยอดสุทธิ) ได้รับ 1 คะแนน | 10 คะแนน แลกส่วนลด 25 บาท")

    if not members_list:
        if search_kw:
            st.warning(f"ไม่พบข้อมูลสมาชิกที่ตรงกับคำค้นหา '{search_kw}'")
        else:
            st.info("ขณะนี้ยังไม่มีข้อมูลสมาชิกลูกค้าในระบบ สามารถกด **'สมัครสมาชิกลูกค้าใหม่'** ด้านบนได้เลยค่ะ")
    else:
        for idx, (mid, fname, lname, phone, pts, reg_date, order_cnt, spent) in enumerate(members_list, 1):
            # ตราอันดับคะแนน
            if idx == 1:
                badge = "อันดับ 1"
            elif idx == 2:
                badge = "อันดับ 2"
            elif idx == 3:
                badge = "อันดับ 3"
            else:
                badge = f"#{idx}"

            with st.container(border=True):
                mc1, mc2, mc3, mc4 = st.columns([1.2, 3.5, 2.5, 2.5])
                with mc1:
                    st.markdown(f"<div style='font-size: 1.15rem; font-weight: 700; color: #ea580c; text-align: center; line-height: 40px;'>{badge}</div>", unsafe_allow_html=True)
                with mc2:
                    st.markdown(f"**คุณ{fname} {lname}**")
                    st.caption(f"เบอร์โทร: **{phone}** • สมัครเมื่อ: {reg_date[:10] if reg_date else '-'}")
                with mc3:
                    st.markdown(f"คะแนนสะสม: <span style='font-size: 1.25rem; font-weight: 800; color: #ea580c;'>{pts:,}</span> แต้ม", unsafe_allow_html=True)
                    discount_avail = (pts // 10) * 25
                    st.caption(f"แลกส่วนลดได้สูงสุด: **฿{discount_avail:,}**")
                with mc4:
                    st.markdown(f"มาทาน: **{order_cnt} ครั้ง**")
                    st.caption(f"ยอดซื้อสะสม: **฿{int(spent):,}**")

    conn_mem.close()


