# ==============================================================================
# ระบบพิมพ์และสร้างใบเสร็จรับเงิน (Receipt & Billing System)
# ==============================================================================
import os
import base64
import sqlite3
import streamlit as st
import streamlit.components.v1 as components
from config import DB_NAME, get_thai_now

# ==============================================================================
def get_payment_qr_base64():
    """ดึงรูปภาพ QR ธนาคาร/พร้อมเพย์ (payment.jpg) จากโฟลเดอร์ static มาแปลงเป็น Base64 สำหรับแสดงในใบเสร็จ HTML"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "static", "img", "payment.jpg"),
        os.path.join(os.path.dirname(__file__), "static", "payment.jpg"),
        os.path.join("static", "img", "payment.jpg"),
        os.path.join("static", "payment.jpg"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return ""


def generate_receipt_html(order_id, table_id, items, total_price, order_time, subtotal=None, discount=0, points_used=0, points_earned=0, member_phone=None, member_name=None, remaining_points=None):
    total_qty = sum(item[1] for item in items)
    if subtotal is None or subtotal <= 0:
        subtotal = total_price + discount
    vat_included = round(total_price * 7 / 107, 2)
    before_vat = round(total_price - vat_included, 2)
    
    # แปลงภาพ QR ธนาคาร (payment.jpg) เป็น Base64 เพื่อฝังลงในใบเสร็จ
    qr_b64 = get_payment_qr_base64()
    if qr_b64:
        qr_payment_html = f"""
        <div class="dashed"></div>
        <div class="text-center" style="margin: 8px 0;">
            <div style="font-size: 13px; font-weight: bold; color: #1e3a8a; margin-bottom: 2px;">
                สแกน QR เพื่อชำระเงิน
            </div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">
                (PromptPay / สแกนผ่านแอปธนาคาร)
            </div>
            <div style="display: flex; justify-content: center; align-items: center; margin: 4px 0;">
                <img src="data:image/jpeg;base64,{qr_b64}" 
                     style="width: 175px; max-width: 90%; height: auto; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.06);" 
                     alt="QR ธนาคารชำระเงิน" />
            </div>
            <div style="font-size: 12px; color: #1e293b; margin-top: 5px;">
                ยอดที่ต้องชำระ: <strong style="color: #c2410c; font-size: 14px;">฿{int(total_price):,}</strong>
            </div>
        </div>
        """
    else:
        qr_payment_html = ""
    
    items_rows_html = ""
    for idx, item in enumerate(items, 1):
        iname = item[0]
        iqty = item[1]
        iprice = item[2]
        line_total = int(iqty * iprice)
        items_rows_html += f"""
        <tr>
            <td style="padding: 4px 0; text-align: left; font-size: 13px;">{idx}. {iname}</td>
            <td style="padding: 4px 0; text-align: center; font-size: 13px;">{iqty}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px;">{int(iprice)}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px; font-weight: bold;">{line_total:,}</td>
        </tr>
        """
        
    # ข้อมูลสมาชิกสะสมแต้มในใบเสร็จ
    member_info_html = ""
    if member_phone:
        pts_used_txt = f"<div>• ใช้คะแนนแลกส่วนลด: <strong>{points_used}</strong> แต้ม (-฿{int(discount):,})</div>" if points_used > 0 else ""
        rem_pts_txt = f"<div>• คะแนนสะสมคงเหลือ: <strong style='color: #ea580c;'>{remaining_points}</strong> แต้ม</div>" if remaining_points is not None else ""
        member_info_html = f"""
        <div class="dashed"></div>
        <div style="font-size: 11.5px; background: #fff7ed; padding: 6px 8px; border-radius: 5px; border: 1px dashed #fdba74; margin-top: 4px;">
            <div style="font-weight: bold; color: #c2410c;">ข้อมูลสมาชิกสะสมแต้ม</div>
            <div>ลูกค้า: <strong>{member_name or 'สมาชิก'}</strong> ({member_phone})</div>
            {pts_used_txt}
            <div>• ได้รับคะแนนบิลนี้: <strong style="color: #16a34a;">+{points_earned}</strong> แต้ม (ทุก 100บ. = 1 แต้ม)</div>
            {rem_pts_txt}
        </div>
        """

    # แถวส่วนลดในตาราง
    discount_row_html = ""
    if discount > 0:
        discount_row_html = f"""
        <tr style="color: #16a34a; font-weight: bold;">
            <td>ส่วนลดจากคะแนน ({points_used} แต้ม):</td>
            <td class="text-right">-฿{int(discount):,}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
    <meta charset="UTF-8">
    <title>ใบเสร็จรับเงินอย่างย่อ #{order_id}</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 3mm;
        }}
        @media print {{
            body {{
                margin: 0 !important;
                padding: 4px !important;
                width: 76mm !important;
                box-shadow: none !important;
                border: none !important;
            }}
            .no-print {{
                display: none !important;
            }}
            img {{
                max-width: 48mm !important;
            }}
        }}
        body {{
            font-family: 'Sarabun', 'Segoe UI', Tahoma, monospace, sans-serif;
            color: #111;
            background: #fff;
            width: 290px;
            margin: 4px auto;
            padding: 14px 10px;
            font-size: 13px;
            line-height: 1.38;
            border: 1px dashed #bbb;
            border-radius: 6px;
            box-sizing: border-box;
        }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .bold {{ font-weight: bold; }}
        .dashed {{
            border-top: 1px dashed #777;
            margin: 8px 0;
        }}
        .double-line {{
            border-top: 2px solid #222;
            margin: 8px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            border-bottom: 1px dashed #777;
            padding: 4px 0;
            font-size: 12px;
        }}
        .btn-print {{
            background: #ea580c;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            transition: background 0.2s;
        }}
        .btn-print:hover {{
            background: #c2410c;
        }}
    </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 12px;">
            <button class="btn-print" onclick="window.print()">สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF</button>
        </div>
        
        <div class="text-center">
            <div style="font-size: 18px; font-weight: bold; color: #c2410c;">ฟ้าใสตำนัว</div>
            <div style="font-size: 11px; color: #444;">(FAHSAI TUM NUA)</div>
            <div style="font-size: 12px; margin-top: 3px; font-weight: bold;">ใบเสร็จรับเงิน / ใบกำกับภาษีอย่างย่อ</div>
            <div style="font-size: 11px; color: #666;">โทร. 093-773-4851 • ยินดีให้บริการ</div>
        </div>
        
        <div class="dashed"></div>
        
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span><strong>โต๊ะที่:</strong> โต๊ะที่ {table_id}</span>
            <span><strong>บิลเลขที่:</strong> #{order_id}</span>
        </div>
        <div style="font-size: 12px; color: #444;">
            <strong>วันที่-เวลา:</strong> {order_time}
        </div>
        
        <div class="dashed"></div>
        
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">รายการอาหาร</th>
                    <th style="text-align: center; width: 32px;">จน.</th>
                    <th style="text-align: right; width: 45px;">ราคา</th>
                    <th style="text-align: right; width: 50px;">รวม</th>
                </tr>
            </thead>
            <tbody>
                {items_rows_html}
            </tbody>
        </table>
        
        <div class="dashed"></div>
        
        <table style="font-size: 12.5px;">
            <tr>
                <td>จำนวนรวม:</td>
                <td class="text-right bold">{total_qty} จาน</td>
            </tr>
            <tr>
                <td>ยอดรวมสินค้า:</td>
                <td class="text-right bold">฿{int(subtotal):,}</td>
            </tr>
            {discount_row_html}
            <tr>
                <td>มูลค่าก่อนภาษี:</td>
                <td class="text-right">฿{before_vat:,.2f}</td>
            </tr>
            <tr>
                <td>ภาษีมูลค่าเพิ่ม (VAT 7% รวมแล้ว):</td>
                <td class="text-right">฿{vat_included:,.2f}</td>
            </tr>
            <tr style="font-size: 15px; font-weight: bold; color: #c2410c;">
                <td style="padding-top: 5px;">ยอดจ่ายจริง (TOTAL):</td>
                <td class="text-right" style="padding-top: 5px;">฿{int(total_price):,}</td>
            </tr>
        </table>
        
        {member_info_html}
        
        {qr_payment_html}
        
        <div class="double-line"></div>
        
        <div class="text-center" style="font-size: 11px; color: #444;">
            <div>ชำระโดย: เงินสด / โอนเงินผ่าน QR ธนาคาร</div>
            <div style="margin-top: 4px; font-weight: bold; color: #111;">ขอบพระคุณที่มาอุดหนุนค่ะ</div>
            <div>โอกาสหน้าเชิญใหม่นะคะ แซ่บนัวทุกจาน!</div>
        </div>
    </body>
    </html>
    """
    return html

def render_receipt_box(oid, conn):
    c = conn.cursor()
    c.execute("""
        SELECT table_id, total_price, created_at, status,
               COALESCE(subtotal, total_price), COALESCE(discount, 0),
               COALESCE(points_used, 0), COALESCE(points_earned, 0),
               member_phone
        FROM orders WHERE id = ?
    """, (oid,))
    row = c.fetchone()
    if not row:
        st.session_state['active_receipt_oid'] = None
        return
    t_id, total, otime, st_code, subtotal, discount, pts_used, pts_earned, m_phone = row
    c.execute("SELECT item_name, quantity, price FROM order_items WHERE order_id = ?", (oid,))
    items = c.fetchall()
    
    m_name = None
    rem_pts = None
    if m_phone:
        c.execute("SELECT first_name, last_name, points FROM members WHERE phone = ?", (m_phone,))
        m_row = c.fetchone()
        if m_row:
            m_name = f"{m_row[0]} {m_row[1]}"
            rem_pts = m_row[2]

    receipt_html = generate_receipt_html(
        oid, t_id, items, total, otime,
        subtotal=subtotal, discount=discount,
        points_used=pts_used, points_earned=pts_earned,
        member_phone=m_phone, member_name=m_name,
        remaining_points=rem_pts
    )
    
    with st.container(border=True):
        st.markdown(f"### ใบเสร็จรับเงินอย่างย่อ — โต๊ะที่ {t_id} (บิล #{oid})")
        st.caption("สามารถกดปุ่ม **สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF** ด้านล่างนี้ หรือดาวน์โหลดไฟล์ได้ทันทีค่ะ")
        
        components.html(receipt_html, height=750, scrolling=True)
        
        # ส่วนแสดง/ผูกข้อมูลสมาชิกที่เคาน์เตอร์คิดเงิน
        if st_code != 'paid':
            if m_phone:
                st.info(f"สมาชิก: **{m_name}** ({m_phone}) | ใช้แลกส่วนลด: **{pts_used}** แต้ม (-฿{int(discount):,}) | ได้รับแต้มบิลนี้: **+{pts_earned}** แต้ม")
            else:
                with st.expander("เพิ่มสมาชิกสะสมแต้มสำหรับบิลนี้ (ที่เคาน์เตอร์)", expanded=False):
                    c_ph_in, c_ph_btn = st.columns([3, 1.2])
                    with c_ph_in:
                        attach_phone = st.text_input("เบอร์โทรศัพท์ลูกค้า:", key=f"attach_ph_input_{oid}", placeholder="เช่น 0937734851")
                    with c_ph_btn:
                        st.write("")
                        attach_btn = st.button("บันทึกเบอร์", key=f"btn_attach_ph_{oid}", use_container_width=True)
                    if attach_btn and attach_phone.strip():
                        cl_ph = attach_phone.strip().replace("-", "").replace(" ", "")
                        c.execute("SELECT id, first_name, last_name, points FROM members WHERE phone = ?", (cl_ph,))
                        m_f = c.fetchone()
                        if m_f:
                            pts_to_earn = int(total // 100)
                            c.execute("UPDATE orders SET member_phone = ?, points_earned = ? WHERE id = ?", (cl_ph, pts_to_earn, oid))
                            conn.commit()
                            st.success(f"ผูกสมาชิก คุณ {m_f[1]} {m_f[2]} (แต้มปัจจุบัน: {m_f[3]}) สำเร็จ!")
                            st.rerun()
                        else:
                            st.warning("ไม่พบเบอร์นี้ในระบบสมาชิกค่ะ สามารถสมัครสมาชิกใหม่ได้ที่แท็บ 'ประวัติลูกค้า' นะคะ")

        rc1, rc2, rc3 = st.columns([1.5, 1.5, 1])
        with rc1:
            st.download_button(
                label="ดาวน์โหลดไฟล์ใบเสร็จ (.html)",
                data=receipt_html,
                file_name=f"receipt_table{t_id}_order{oid}.html",
                mime="text/html",
                use_container_width=True,
                key=f"dl_receipt_file_{oid}"
            )
        with rc2:
            if st_code != 'paid':
                if st.button("ยืนยันรับเงิน (ปิดบิล)", key=f"pay_confirm_btn_{oid}", type="primary", use_container_width=True):
                    c.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (oid,))
                    # อัปเดตคะแนนสะสมของสมาชิก
                    if m_phone:
                        net_pts_change = pts_earned - pts_used
                        c.execute("UPDATE members SET points = MAX(0, points + ?) WHERE phone = ?", (net_pts_change, m_phone))
                    conn.commit()
                    st.session_state['active_receipt_oid'] = None
                    st.toast(f"ปิดบิลโต๊ะ {t_id} เรียบร้อยแล้วค่ะ!")
                    st.rerun()
            else:
                st.info("บิลนี้ชำระเงินเรียบร้อยแล้ว")
        with rc3:
            if st.button("ปิดหน้าต่างใบเสร็จ", key=f"close_receipt_btn_{oid}", use_container_width=True):
                st.session_state['active_receipt_oid'] = None
                st.rerun()


