# ==============================================================================
# รายงานยอดขาย & สถิติผลประกอบการ (Sales Analytics & Reporting View)
# ==============================================================================
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from config import DB_NAME, get_thai_now

def render_report_tab():
    """แสดงแท็บรายงานสรุปยอดขายแบบละเอียดและชัดเจน (ไม่เน้นรูปภาพ)"""
    st.markdown("### รายงานสรุปยอดขาย (Sales & Revenue Report)")
    st.caption("สรุปภาพรวมรายได้ ยอดขายแยกตามหมวดหมู่ และอันดับเมนูขายดีของร้านฟ้าใสตำนัว")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ==========================================================================
    # 1. ตัวกรองช่วงเวลา (Date & Period Filters)
    # ==========================================================================
    with st.container(border=True):
        f_col1, f_col2 = st.columns([2, 1.5])
        with f_col1:
            period_options = ["ทั้งหมด", "วันนี้", "เมื่อวาน", "7 วันล่าสุด", "เดือนนี้", "กำหนดวันเอง"]
            sel_period = st.pills("เลือกช่วงเวลา:", period_options, default="ทั้งหมด", key="report_period_pills")
        with f_col2:
            sort_options = ["ยอดขายรวม (บาท)", "จำนวนจานที่ขายได้ (จาน)"]
            sel_sort = st.pills("จัดอันดับตาม:", sort_options, default="ยอดขายรวม (บาท)", key="report_sort_pills")

        thai_now = get_thai_now()
        today_str = thai_now.strftime('%Y-%m-%d')
        yesterday_str = (thai_now - timedelta(days=1)).strftime('%Y-%m-%d')
        seven_days_ago_str = (thai_now - timedelta(days=6)).strftime('%Y-%m-%d')
        this_month_str = thai_now.strftime('%Y-%m')

        date_condition = ""
        period_label = "ข้อมูลทั้งหมด"

        if sel_period == "วันนี้":
            date_condition = f"AND DATE(o.created_at) = '{today_str}'"
            period_label = f"วันนี้ ({thai_now.strftime('%d/%m/%Y')})"
        elif sel_period == "เมื่อวาน":
            date_condition = f"AND DATE(o.created_at) = '{yesterday_str}'"
            period_label = f"เมื่อวาน ({(thai_now - timedelta(days=1)).strftime('%d/%m/%Y')})"
        elif sel_period == "7 วันล่าสุด":
            date_condition = f"AND DATE(o.created_at) >= '{seven_days_ago_str}' AND DATE(o.created_at) <= '{today_str}'"
            period_label = f"7 วันล่าสุด ({seven_days_ago_str} ถึง {today_str})"
        elif sel_period == "เดือนนี้":
            date_condition = f"AND strftime('%Y-%m', o.created_at) = '{this_month_str}'"
            period_label = f"เดือนนี้ ({thai_now.strftime('%m/%Y')})"
        elif sel_period == "กำหนดวันเอง":
            custom_dates = st.date_input(
                "เลือกช่วงวันที่ต้องการดูรายงาน:",
                value=(thai_now - timedelta(days=7), thai_now),
                key="report_custom_dates"
            )
            if isinstance(custom_dates, (tuple, list)) and len(custom_dates) == 2:
                start_d, end_d = custom_dates
                date_condition = f"AND DATE(o.created_at) >= '{start_d.strftime('%Y-%m-%d')}' AND DATE(o.created_at) <= '{end_d.strftime('%Y-%m-%d')}'"
                period_label = f"วันที่ {start_d.strftime('%d/%m/%Y')} ถึง {end_d.strftime('%d/%m/%Y')}"
            elif isinstance(custom_dates, (tuple, list)) and len(custom_dates) == 1:
                single_d = custom_dates[0]
                date_condition = f"AND DATE(o.created_at) = '{single_d.strftime('%Y-%m-%d')}'"
                period_label = f"วันที่ {single_d.strftime('%d/%m/%Y')}"

    # ==========================================================================
    # 2. ดึงข้อมูลสรุปยอดขายภาพรวม (Executive Summary Metrics)
    # ==========================================================================
    c.execute(f'''
        SELECT 
            COUNT(id) as total_bills,
            COALESCE(SUM(total_price), 0) as total_revenue,
            COALESCE(SUM(subtotal), 0) as total_subtotal,
            COALESCE(SUM(discount), 0) as total_discount
        FROM orders o
        WHERE o.status != 'cancelled' {date_condition}
    ''')
    order_summary = c.fetchone()
    total_bills = order_summary[0] if order_summary else 0
    total_revenue = order_summary[1] if order_summary else 0.0
    total_subtotal = order_summary[2] if order_summary else 0.0
    total_discount = order_summary[3] if order_summary else 0.0

    # ดึงจำนวนจานอาหารทั้งหมดที่ขายได้
    c.execute(f'''
        SELECT COALESCE(SUM(oi.quantity), 0)
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled' {date_condition}
    ''')
    total_items_sold = c.fetchone()[0] or 0

    if total_bills == 0 and total_items_sold == 0:
        st.info(f"ยังไม่มีประวัติยอดขายในช่วงเวลา: **{period_label}** ค่ะ ลองเลือกช่วงเวลาอื่นด้านบนนะคะ")
        conn.close()
        return

    # คำนวณค่าเฉลี่ยต่อบิล
    avg_per_bill = (total_revenue / total_bills) if total_bills > 0 else 0.0

    st.markdown(f"#### สรุปภาพรวมยอดขาย: <span style='color: #ea580c;'>{period_label}</span>", unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("ยอดขายสุทธิรวม", f"฿{int(total_revenue):,}")
    m2.metric("จำนวนบิลที่ขายได้", f"{total_bills:,} บิล")
    m3.metric("จำนวนอาหารที่ขายได้", f"{total_items_sold:,} จาน")
    m4.metric("ยอดขายเฉลี่ยต่อบิล", f"฿{avg_per_bill:,.1f}")
    m5.metric("ส่วนลดสมาชิกทั้งหมด", f"฿{int(total_discount):,}")

    st.write("---")

    # ==========================================================================
    # 3. สรุป 3 อันดับเมนูขายดีสูงสุด (Top 3 Best Sellers - ไม่มีรูปภาพ ชัดเจน)
    # ==========================================================================
    order_sql = "total_sales DESC, total_qty DESC" if "ยอดขายรวม" in sel_sort else "total_qty DESC, total_sales DESC"

    c.execute(f'''
        SELECT 
            oi.item_name,
            COALESCE(mi.category, 'ทั่วไป') as category,
            COALESCE(mi.price, oi.price) as unit_price,
            SUM(oi.quantity) as total_qty,
            SUM(oi.quantity * oi.price) as total_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN menu_items mi ON oi.item_name = mi.name
        WHERE o.status != 'cancelled' {date_condition}
        GROUP BY oi.item_name
        ORDER BY {order_sql}
    ''')
    best_sellers = c.fetchall()

    if best_sellers:
        st.markdown("#### 3 อันดับเมนูทำเงินสูงสุด (Top 3 Highlights)")
        top_cols = st.columns(min(3, len(best_sellers)))
        badges = [
            ("อันดับ 1 (แชมป์ยอดขาย)", "#fffbeb", "#f59e0b", "#b45309"),
            ("อันดับ 2", "#f8fafc", "#64748b", "#334155"),
            ("อันดับ 3", "#fff7ed", "#ea580c", "#c2410c")
        ]

        for idx in range(min(3, len(best_sellers))):
            t_name, t_cat, t_price, t_qty, t_sales = best_sellers[idx]
            b_label, b_bg, b_border, b_text = badges[idx]
            pct_share = (t_sales / total_revenue * 100) if total_revenue > 0 else 0

            with top_cols[idx]:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='background: {b_bg}; border: 1.5px solid {b_border}; border-radius: 8px; padding: 6px 10px; text-align: center; font-weight: 800; color: {b_text}; font-size: 0.95rem; margin-bottom: 8px;'>{b_label}</div>", 
                        unsafe_allow_html=True
                    )
                    st.markdown(f"<div style='font-size: 1.15rem; font-weight: 800; color: #1c1917; margin-bottom: 2px;'>{t_name}</div>", unsafe_allow_html=True)
                    st.caption(f"หมวดหมู่: {t_cat} • ราคา ฿{int(t_price)}/จาน")
                    st.markdown(f"ขายได้: <b style='font-size: 1.15rem; color: #ea580c;'>{t_qty:,} จาน</b>", unsafe_allow_html=True)
                    st.markdown(f"รวมเงิน: <b style='font-size: 1.15rem; color: #15803d;'>฿{int(t_sales):,}</b> <span style='font-size: 0.82rem; color: #78716c;'>({pct_share:.1f}% ของยอดรวม)</span>", unsafe_allow_html=True)

        st.write("---")

    # ==========================================================================
    # 4. สรุปยอดขายแยกตามหมวดหมู่อาหาร (Category Breakdown)
    # ==========================================================================
    st.markdown("#### ยอดขายแยกตามหมวดหมู่อาหาร")
    c.execute(f'''
        SELECT 
            COALESCE(mi.category, 'ทั่วไป') as category,
            COUNT(DISTINCT oi.item_name) as unique_items,
            SUM(oi.quantity) as cat_qty,
            SUM(oi.quantity * oi.price) as cat_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN menu_items mi ON oi.item_name = mi.name
        WHERE o.status != 'cancelled' {date_condition}
        GROUP BY COALESCE(mi.category, 'ทั่วไป')
        ORDER BY cat_sales DESC
    ''')
    cat_summary = c.fetchall()

    if cat_summary:
        cat_data = []
        for cname, citems, cqty, csales in cat_summary:
            cpct = (csales / total_revenue * 100) if total_revenue > 0 else 0
            cat_data.append({
                "หมวดหมู่อาหาร": cname,
                "จำนวนเมนูที่ขายได้": f"{citems} เมนู",
                "จำนวนจานที่ขายได้ (จาน)": f"{cqty:,}",
                "ยอดขายรวม (บาท)": f"฿{int(csales):,}",
                "สัดส่วนยอดขาย": f"{cpct:.1f}%"
            })
        
        df_cat = pd.DataFrame(cat_data)
        st.dataframe(df_cat, use_container_width=True, hide_index=True)

    st.write("---")

    # ==========================================================================
    # 5. ตารางรายงานยอดขายรายเมนูแบบละเอียด (Itemized Menu Sales Table)
    # ==========================================================================
    st.markdown("#### รายงานยอดขายรายเมนูทั้งหมด (Itemized Report)")
    st.caption("ตารางแสดงรายละเอียดเมนูอาหาร จำนวนจานที่ขายได้ ยอดเงินรวม และสัดส่วนยอดขายอย่างชัดเจน")

    # ฟิลเตอร์ค้นหาชื่อเมนู และเลือกหมวดหมู่
    c_s1, c_s2 = st.columns([2, 1.5])
    with c_s1:
        search_menu = st.text_input("ค้นหาเมนูอาหาร:", placeholder="พิมพ์ชื่อเมนูเพื่อค้นหา...", key="report_search_input")
    with c_s2:
        cat_list = ["ทั้งหมด"] + [row[0] for row in cat_summary]
        filter_cat = st.selectbox("กรองตามหมวดหมู่:", cat_list, key="report_cat_select")

    # คัดกรองข้อมูลเมนู
    display_menus = best_sellers
    if filter_cat != "ทั้งหมด":
        display_menus = [m for m in display_menus if m[1] == filter_cat]
    if search_menu:
        kw = search_menu.strip().lower()
        display_menus = [m for m in display_menus if kw in (m[0] or "").lower()]

    if not display_menus:
        st.info("ไม่พบรายการเมนูที่ตรงกับเงื่อนไขการค้นหาค่ะ")
    else:
        table_rows = []
        raw_export_rows = []

        for rank, (iname, icat, iprice, iqty, isales) in enumerate(display_menus, 1):
            pct_sales = (isales / total_revenue * 100) if total_revenue > 0 else 0
            
            # Badge อันดับ
            if rank == 1:
                rank_str = "อันดับ 1"
            elif rank == 2:
                rank_str = "อันดับ 2"
            elif rank == 3:
                rank_str = "อันดับ 3"
            else:
                rank_str = f"#{rank}"

            table_rows.append({
                "อันดับ": rank_str,
                "ชื่อเมนูอาหาร": iname,
                "หมวดหมู่": icat,
                "ราคา/จาน": f"฿{int(iprice):,}",
                "จำนวนที่ขายได้": f"{iqty:,} จาน",
                "ยอดขายรวม (บาท)": f"฿{int(isales):,}",
                "สัดส่วนยอดขาย": f"{pct_sales:.1f}%"
            })

            raw_export_rows.append({
                "อันดับ": rank,
                "ชื่อเมนูอาหาร": iname,
                "หมวดหมู่": icat,
                "ราคาต่อจาน (บาท)": iprice,
                "จำนวนที่ขายได้ (จาน)": iqty,
                "ยอดขายรวม (บาท)": isales,
                "สัดส่วนเปอร์เซ็นต์": round(pct_sales, 2)
            })

        df_items = pd.DataFrame(table_rows)
        st.dataframe(df_items, use_container_width=True, hide_index=True)

        # ปุ่มดาวน์โหลดข้อมูลเป็นไฟล์ CSV (UTF-8-SIG สำหรับเปิดใน Excel ภาษาไทยไม่เพี้ยน)
        df_export = pd.DataFrame(raw_export_rows)
        csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
        file_timestamp = thai_now.strftime('%Y%m%d_%H%M')
        st.download_button(
            label="ดาวน์โหลดรายงานยอดขาย (CSV / Excel)",
            data=csv_data,
            file_name=f"fahsai_sales_report_{file_timestamp}.csv",
            mime="text/csv",
            key="btn_download_sales_csv"
        )

    st.write("---")

    # ==========================================================================
    # 6. สรุปยอดขายรายวัน & ประวัติบิลที่ชำระแล้ว (Daily Sales & Bill Log)
    # ==========================================================================
    st.markdown("#### สรุปยอดขายรายวัน (Daily Breakdown)")
    c.execute(f'''
        SELECT 
            DATE(o.created_at) as sale_date,
            COUNT(DISTINCT o.id) as bill_count,
            COALESCE(SUM(oi.quantity), 0) as dish_count,
            COALESCE(SUM(o.total_price), 0) as daily_revenue
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.status != 'cancelled' {date_condition}
        GROUP BY DATE(o.created_at)
        ORDER BY sale_date DESC
    ''')
    daily_rows = c.fetchall()

    if daily_rows:
        daily_list = []
        for s_date, b_cnt, d_cnt, d_rev in daily_rows:
            daily_list.append({
                "วันที่": s_date,
                "จำนวนบิล (บิล)": f"{b_cnt:,}",
                "จำนวนอาหาร (จาน)": f"{d_cnt:,}",
                "ยอดขายรวม (บาท)": f"฿{int(d_rev):,}",
                "ยอดเฉลี่ยต่อบิล": f"฿{(d_rev/b_cnt if b_cnt > 0 else 0):,.1f}"
            })
        df_daily = pd.DataFrame(daily_list)
        st.dataframe(df_daily, use_container_width=True, hide_index=True)

    # ประวัติบิลที่ชำระเงินแล้ว (คลี่ดูรายละเอียดบิลได้)
    with st.expander("ดูประวัติบิลที่ชำระเงินแล้วทั้งหมด (Recent Paid Orders Log)"):
        c.execute(f'''
            SELECT 
                o.id,
                o.table_id,
                o.status,
                o.total_price,
                COALESCE(o.payment_method, 'promptpay') as pay_method,
                o.created_at,
                COALESCE(o.discount, 0) as discount
            FROM orders o
            WHERE o.status != 'cancelled' {date_condition}
            ORDER BY o.created_at DESC
            LIMIT 50
        ''')
        orders_list = c.fetchall()

        if not orders_list:
            st.info("ไม่มีประวัติบิลในช่วงเวลานี้")
        else:
            bill_table_data = []
            for b_id, b_tbl, b_stat, b_tot, b_pay, b_time, b_disc in orders_list:
                # ดึงรายการอาหารในบิลนี้
                c.execute('SELECT item_name, quantity, price FROM order_items WHERE order_id = ?', (b_id,))
                items_in_bill = c.fetchall()
                items_summary = ", ".join([f"{it[0]} x{it[1]}" for it in items_in_bill])
                
                pay_label = "พร้อมเพย์" if "prompt" in (b_pay or "").lower() else "เงินสด"
                bill_table_data.append({
                    "รหัสบิล": f"#{b_id}",
                    "โต๊ะ": f"โต๊ะ {b_tbl}",
                    "เวลาที่สั่ง/ชำระ": b_time,
                    "วิธีชำระเงิน": pay_label,
                    "รายการอาหาร": items_summary if items_summary else "-",
                    "ส่วนลด": f"฿{int(b_disc):,}" if b_disc > 0 else "-",
                    "ยอดสุทธิ (บาท)": f"฿{int(b_tot):,}"
                })
            df_bills = pd.DataFrame(bill_table_data)
            st.dataframe(df_bills, use_container_width=True, hide_index=True)

    conn.close()
