# ==============================================================================
# โมดูลระบบจัดการหลังร้าน (Admin POS & Backoffice Views)
# ==============================================================================
import streamlit as st
from config import render_app_footer
from views.admin.auth_view import check_admin_auth
from views.admin.table_view import render_table_tab
from views.admin.kds_pos_view import render_pos_dashboard
from views.admin.report_view import render_report_tab
from views.admin.member_view import render_member_tab
from views.admin.menu_view import render_menu_tab

def render_admin_view():
    """แสดงหน้าจอระบบจัดการหลังร้าน (5 แท็บหลัก)"""
    # 1. ตรวจสอบสิทธิ์และแสดงฟอร์มล็อกอิน / แถบผู้ใช้
    check_admin_auth()

    # CSS + JS เฉพาะสำหรับ 5 แท็บของหลังร้าน ให้แยกสีเด่นชัด 100% ทุกเบราว์เซอร์ (รวมถึง Google Chrome บน Streamlit Cloud)
    st.markdown("""
    <style>
    /* ให้แถบแท็บเลื่อนแนวนอนได้อย่างลื่นไหลบนทุกขนาดหน้าจอ */
    .st-key-admin_main_tabs [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"],
    div[data-testid="stTabs"] [data-baseweb="tab-list"],
    div[role="tablist"] {
        overflow-x: auto !important;
        scrollbar-width: thin !important;
        padding-bottom: 0px !important;
        gap: 6px !important;
    }

    /* 1. แท็บที่ 1 - จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (สีแดง - Red) */
    .stTabs [data-baseweb="tab"]:nth-of-type(1),
    .stTabs button[role="tab"]:nth-of-type(1),
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1),
    div[data-baseweb="tab-list"] button:nth-of-type(1),
    div[role="tablist"] button:nth-of-type(1) {
        background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%) !important;
        background-color: #fee2e2 !important;
        border: 2px solid #ef4444 !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(1) p,
    .stTabs [data-baseweb="tab"]:nth-of-type(1) span,
    .stTabs button[role="tab"]:nth-of-type(1) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) p,
    div[data-baseweb="tab-list"] button:nth-of-type(1) p,
    div[role="tablist"] button:nth-of-type(1) p {
        color: #991b1b !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(1):hover,
    .stTabs button[role="tab"]:nth-of-type(1):hover,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1):hover,
    div[data-baseweb="tab-list"] button:nth-of-type(1):hover {
        background: linear-gradient(180deg, #fecaca 0%, #fca5a5 100%) !important;
        border-color: #dc2626 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"],
    .stTabs button[role="tab"]:nth-of-type(1)[aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-of-type(1)[aria-selected="true"],
    div[role="tablist"] button:nth-of-type(1)[aria-selected="true"] {
        background: linear-gradient(180deg, #ef4444 0%, #b91c1c 100%) !important;
        background-color: #dc2626 !important;
        border: 2px solid #991b1b !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(220, 38, 38, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"] p,
    .stTabs [data-baseweb="tab"]:nth-of-type(1)[aria-selected="true"] span,
    .stTabs button[role="tab"]:nth-of-type(1)[aria-selected="true"] p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)[aria-selected="true"] p,
    div[data-baseweb="tab-list"] button:nth-of-type(1)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 2. แท็บที่ 2 - จอครัว & เคาน์เตอร์คิดเงิน (สีเขียว - Green) */
    .stTabs [data-baseweb="tab"]:nth-of-type(2),
    .stTabs button[role="tab"]:nth-of-type(2),
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2),
    div[data-baseweb="tab-list"] button:nth-of-type(2),
    div[role="tablist"] button:nth-of-type(2) {
        background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important;
        background-color: #dcfce7 !important;
        border: 2px solid #10b981 !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(2) p,
    .stTabs [data-baseweb="tab"]:nth-of-type(2) span,
    .stTabs button[role="tab"]:nth-of-type(2) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) p,
    div[data-baseweb="tab-list"] button:nth-of-type(2) p,
    div[role="tablist"] button:nth-of-type(2) p {
        color: #065f46 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(2):hover,
    .stTabs button[role="tab"]:nth-of-type(2):hover,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2):hover,
    div[data-baseweb="tab-list"] button:nth-of-type(2):hover {
        background: linear-gradient(180deg, #bbf7d0 0%, #86efac 100%) !important;
        border-color: #059669 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"],
    .stTabs button[role="tab"]:nth-of-type(2)[aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-of-type(2)[aria-selected="true"],
    div[role="tablist"] button:nth-of-type(2)[aria-selected="true"] {
        background: linear-gradient(180deg, #10b981 0%, #047857 100%) !important;
        background-color: #059669 !important;
        border: 2px solid #065f46 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(16, 185, 129, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"] p,
    .stTabs [data-baseweb="tab"]:nth-of-type(2)[aria-selected="true"] span,
    .stTabs button[role="tab"]:nth-of-type(2)[aria-selected="true"] p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"] p,
    div[data-baseweb="tab-list"] button:nth-of-type(2)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 3. แท็บที่ 3 - รายงานยอดขาย (สีม่วง - Purple) */
    .stTabs [data-baseweb="tab"]:nth-of-type(3),
    .stTabs button[role="tab"]:nth-of-type(3),
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3),
    div[data-baseweb="tab-list"] button:nth-of-type(3),
    div[role="tablist"] button:nth-of-type(3) {
        background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important;
        background-color: #f3e8ff !important;
        border: 2px solid #8b5cf6 !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(3) p,
    .stTabs [data-baseweb="tab"]:nth-of-type(3) span,
    .stTabs button[role="tab"]:nth-of-type(3) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) p,
    div[data-baseweb="tab-list"] button:nth-of-type(3) p,
    div[role="tablist"] button:nth-of-type(3) p {
        color: #5b21b6 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(3):hover,
    .stTabs button[role="tab"]:nth-of-type(3):hover,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3):hover,
    div[data-baseweb="tab-list"] button:nth-of-type(3):hover {
        background: linear-gradient(180deg, #e9d5ff 0%, #d8b4fe 100%) !important;
        border-color: #7c3aed !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"],
    .stTabs button[role="tab"]:nth-of-type(3)[aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-of-type(3)[aria-selected="true"],
    div[role="tablist"] button:nth-of-type(3)[aria-selected="true"] {
        background: linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%) !important;
        background-color: #7c3aed !important;
        border: 2px solid #5b21b6 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(124, 58, 237, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"] p,
    .stTabs [data-baseweb="tab"]:nth-of-type(3)[aria-selected="true"] span,
    .stTabs button[role="tab"]:nth-of-type(3)[aria-selected="true"] p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"] p,
    div[data-baseweb="tab-list"] button:nth-of-type(3)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 4. แท็บที่ 4 - ประวัติลูกค้า (สีส้ม - Orange) */
    .stTabs [data-baseweb="tab"]:nth-of-type(4),
    .stTabs button[role="tab"]:nth-of-type(4),
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4),
    div[data-baseweb="tab-list"] button:nth-of-type(4),
    div[role="tablist"] button:nth-of-type(4) {
        background: linear-gradient(180deg, #ffedd5 0%, #fed7aa 100%) !important;
        background-color: #ffedd5 !important;
        border: 2px solid #f97316 !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(4) p,
    .stTabs [data-baseweb="tab"]:nth-of-type(4) span,
    .stTabs button[role="tab"]:nth-of-type(4) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4) p,
    div[data-baseweb="tab-list"] button:nth-of-type(4) p,
    div[role="tablist"] button:nth-of-type(4) p {
        color: #9a3412 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(4):hover,
    .stTabs button[role="tab"]:nth-of-type(4):hover,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4):hover,
    div[data-baseweb="tab-list"] button:nth-of-type(4):hover {
        background: linear-gradient(180deg, #fed7aa 0%, #fdba74 100%) !important;
        border-color: #ea580c !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"],
    .stTabs button[role="tab"]:nth-of-type(4)[aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-of-type(4)[aria-selected="true"],
    div[role="tablist"] button:nth-of-type(4)[aria-selected="true"] {
        background: linear-gradient(180deg, #f97316 0%, #c2410c 100%) !important;
        background-color: #ea580c !important;
        border: 2px solid #9a3412 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(234, 88, 12, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"] p,
    .stTabs [data-baseweb="tab"]:nth-of-type(4)[aria-selected="true"] span,
    .stTabs button[role="tab"]:nth-of-type(4)[aria-selected="true"] p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)[aria-selected="true"] p,
    div[data-baseweb="tab-list"] button:nth-of-type(4)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 5. แท็บที่ 5 - จัดการเมนูอาหาร (สีฟ้า - Sky Blue) */
    .stTabs [data-baseweb="tab"]:nth-of-type(5),
    .stTabs button[role="tab"]:nth-of-type(5),
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5),
    div[data-baseweb="tab-list"] button:nth-of-type(5),
    div[role="tablist"] button:nth-of-type(5) {
        background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important;
        background-color: #e0f2fe !important;
        border: 2px solid #0ea5e9 !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(5) p,
    .stTabs [data-baseweb="tab"]:nth-of-type(5) span,
    .stTabs button[role="tab"]:nth-of-type(5) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) p,
    div[data-baseweb="tab-list"] button:nth-of-type(5) p,
    div[role="tablist"] button:nth-of-type(5) p {
        color: #075985 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(5):hover,
    .stTabs button[role="tab"]:nth-of-type(5):hover,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5):hover,
    div[data-baseweb="tab-list"] button:nth-of-type(5):hover {
        background: linear-gradient(180deg, #bae6fd 0%, #7dd3fc 100%) !important;
        border-color: #0284c7 !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"],
    .stTabs button[role="tab"]:nth-of-type(5)[aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-of-type(5)[aria-selected="true"],
    div[role="tablist"] button:nth-of-type(5)[aria-selected="true"] {
        background: linear-gradient(180deg, #0ea5e9 0%, #0369a1 100%) !important;
        background-color: #0284c7 !important;
        border: 2px solid #075985 !important;
        border-bottom: none !important;
        box-shadow: 0 -4px 12px rgba(2, 132, 199, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"] p,
    .stTabs [data-baseweb="tab"]:nth-of-type(5)[aria-selected="true"] span,
    .stTabs button[role="tab"]:nth-of-type(5)[aria-selected="true"] p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)[aria-selected="true"] p,
    div[data-baseweb="tab-list"] button:nth-of-type(5)[aria-selected="true"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # เสริมด้วย JavaScript ผ่าน st.components.v1.html เพื่อบังคับสีตามข้อความชื่อแท็บโดยตรง (ทำงาน 100% บน Chrome ทุกเวอร์ชัน)
    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function() {
        var tabRules = [
            { match: "จัดการโต๊ะอาหาร", bg: "linear-gradient(180deg, #fee2e2 0%, #fecaca 100%)", border: "#ef4444", text: "#991b1b", activeBg: "linear-gradient(180deg, #ef4444 0%, #b91c1c 100%)", activeBorder: "#991b1b", line: "#dc2626" },
            { match: "จอครัว", bg: "linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%)", border: "#10b981", text: "#065f46", activeBg: "linear-gradient(180deg, #10b981 0%, #047857 100%)", activeBorder: "#065f46", line: "#059669" },
            { match: "รายงานยอดขาย", bg: "linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%)", border: "#8b5cf6", text: "#5b21b6", activeBg: "linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%)", activeBorder: "#5b21b6", line: "#7c3aed" },
            { match: "ประวัติลูกค้า", bg: "linear-gradient(180deg, #ffedd5 0%, #fed7aa 100%)", border: "#f97316", text: "#9a3412", activeBg: "linear-gradient(180deg, #f97316 0%, #c2410c 100%)", activeBorder: "#9a3412", line: "#ea580c" },
            { match: "จัดการเมนูอาหาร", bg: "linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%)", border: "#0ea5e9", text: "#075985", activeBg: "linear-gradient(180deg, #0ea5e9 0%, #0369a1 100%)", activeBorder: "#075985", line: "#0284c7" }
        ];

        function applyAdminTabColors() {
            try {
                var doc = window.parent.document;
                var buttons = doc.querySelectorAll('button[role="tab"], [data-baseweb="tab"]');
                buttons.forEach(function(btn) {
                    var label = (btn.innerText || btn.textContent || "").trim();
                    tabRules.forEach(function(r) {
                        if (label.indexOf(r.match) !== -1) {
                            var isSelected = btn.getAttribute("aria-selected") === "true";
                            btn.style.setProperty("background", isSelected ? r.activeBg : r.bg, "important");
                            btn.style.setProperty("border", "2px solid " + (isSelected ? r.activeBorder : r.border), "important");
                            btn.style.setProperty("border-bottom", "none", "important");
                            btn.style.setProperty("border-top-left-radius", "12px", "important");
                            btn.style.setProperty("border-top-right-radius", "12px", "important");
                            var children = btn.querySelectorAll("p, span, div");
                            children.forEach(function(ch) {
                                ch.style.setProperty("color", isSelected ? "#ffffff" : r.text, "important");
                                ch.style.setProperty("font-weight", "700", "important");
                            });
                            if (isSelected && btn.parentElement) {
                                btn.parentElement.style.setProperty("border-bottom", "3px solid " + r.line, "important");
                            }
                        }
                    });
                });
            } catch (e) {}
        }

        applyAdminTabColors();
        setInterval(applyAdminTabColors, 250);
    })();
    </script>
    """, height=0, width=0)

    # 2. เมนูแท็บ 5 ส่วนหลัก
    with st.container(key="admin_main_tabs"):
        tab_tbl, tab_pos, tab_rep, tab_mem, tab_menu = st.tabs([
            "จัดการโต๊ะอาหาร & เคลียร์โต๊ะ", 
            "จอครัว & เคาน์เตอร์คิดเงิน", 
            "รายงานยอดขาย",
            "ประวัติลูกค้า",
            "จัดการเมนูอาหาร"
        ])

        with tab_tbl:
            render_table_tab()

        with tab_pos:
            render_pos_dashboard()

        with tab_rep:
            render_report_tab()

        with tab_mem:
            render_member_tab()

        with tab_menu:
            render_menu_tab()

    # Footer ล่างสุด
    render_app_footer()
