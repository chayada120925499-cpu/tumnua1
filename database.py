# ==============================================================================
# การจัดการฐานข้อมูล SQLite (Database Setup & Migrations)
# ==============================================================================
import sqlite3
import hashlib
from config import DB_NAME

def get_connection():
    """สร้างและคืนค่าการเชื่อมต่อฐานข้อมูล SQLite"""
    return sqlite3.connect(DB_NAME)

DB_NAME = "restaurant.db"

def init_db():
    """
    ฟังก์ชันสร้างตารางฐานข้อมูลที่จำเป็น (ถ้ายังไม่มี) 
    และบันทึกข้อมูลเมนูอาหารเริ่มต้นของร้านฟ้าใสตำนัว
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. ตารางเมนูอาหาร (menu_items)
    # เก็บชื่ออาหาร หมวดหมู่ ราคา ต้นทุน รูปภาพ และคำอธิบาย
    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,          -- ชื่อเมนูอาหาร (ห้ามซ้ำ)
            category TEXT NOT NULL,             -- หมวดหมู่อาหาร (เช่น ส้มตำ, ย่าง, ต้ม)
            price REAL NOT NULL,                -- ราคาขาย (บาท)
            cost REAL DEFAULT 0,                -- ต้นทุนวัตถุดิบ (บาท)
            image TEXT,                         -- URL รูปภาพอาหาร
            description TEXT                    -- คำอธิบายความอร่อย/จุดเด่น
        )
    ''')

    # 2. ตารางโต๊ะอาหารในร้าน (tables)
    # เก็บหมายเลขโต๊ะ ชื่อโต๊ะ และสถานะ (ว่าง/มีลูกค้า)
    # *หมายเหตุ: ค่าเริ่มต้นไม่มีโต๊ะ โดยเจ้าของร้านสามารถกดเพิ่ม/ลบโต๊ะได้เองตามต้องการ
    c.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY,
            table_number INTEGER NOT NULL UNIQUE, -- หมายเลขโต๊ะ เช่น 1, 2, 3
            name TEXT,                            -- ชื่อเรียกโต๊ะ เช่น "โต๊ะที่ 1", "ซุ้มริมน้ำ 2"
            status TEXT DEFAULT 'available'       -- สถานะโต๊ะ
        )
    ''')

    # 3. ตารางออเดอร์/บิลหลัก (orders)
    # เก็บรหัสบิล โต๊ะที่สั่ง สถานะบิล ยอดเงินรวม และวันเวลาที่สั่ง
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,          -- หมายเลขโต๊ะที่สั่ง
            status TEXT NOT NULL DEFAULT 'pending', -- สถานะบิล: pending -> accepted -> cooked -> served -> paid -> archived
            total_price REAL NOT NULL,          -- ยอดเงินรวมทั้งสิ้นของบิล (บาท)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันและเวลาที่สั่งอาหาร
        )
    ''')

    # 4. ตารางรายการอาหารย่อยในแต่ละบิล (order_items)
    # เก็บว่าในบิลนั้นๆ สั่งอาหารจานใดบ้าง จำนวนกี่จาน ราคา และสถานะการปรุงแต่ละจาน
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,          -- เชื่อมกับ orders.id
            item_name TEXT NOT NULL,            -- ชื่อเมนูอาหารที่สั่ง
            price REAL NOT NULL,                -- ราคาต่อหน่วย ณ ตอนที่สั่ง
            cost REAL DEFAULT 0,                -- ต้นทุนต่อหน่วย
            quantity INTEGER NOT NULL,          -- จำนวนจานที่สั่ง
            note TEXT,                          -- โน้ตเพิ่มเติม เช่น เผ็ดน้อย, ไม่ใส่ชูรส
            status TEXT DEFAULT 'pending'       -- สถานะแต่ละจาน: pending(กำลังปรุง) -> cooked(ปรุงเสร็จ) -> served(เสิร์ฟแล้ว)
        )
    ''')

    # 5. ตารางสมาชิกสะสมแต้ม (members)
    # เก็บข้อมูลสมาชิก: ชื่อ, นามสกุล, หมายเลขโทรศัพท์ และคะแนนสะสม
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,           -- ชื่อสมาชิก
            last_name TEXT NOT NULL,            -- นามสกุล
            phone TEXT NOT NULL UNIQUE,         -- หมายเลขโทรศัพท์ (ห้ามซ้ำ)
            points INTEGER DEFAULT 0,           -- คะแนนสะสม
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันเวลาที่สมัครสมาชิก
        )
    ''')

    # ตรวจสอบและอัปเกรดคอลัมน์ status ในตาราง order_items แบบอัตโนมัติ (Backward Compatibility)
    c.execute("PRAGMA table_info(order_items)")
    existing_cols = [col[1] for col in c.fetchall()]
    if 'status' not in existing_cols:
        c.execute("ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT 'pending'")
    c.execute("UPDATE order_items SET status = 'pending' WHERE status IS NULL")

    # ตรวจสอบและอัปเกรดคอลัมน์ระบบสมาชิกและส่วนลดในตาราง orders แบบอัตโนมัติ
    c.execute("PRAGMA table_info(orders)")
    order_cols = [col[1] for col in c.fetchall()]
    if 'subtotal' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN subtotal REAL DEFAULT 0")
    if 'discount' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN discount REAL DEFAULT 0")
    if 'points_used' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_used INTEGER DEFAULT 0")
    if 'points_earned' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_earned INTEGER DEFAULT 0")
    if 'member_phone' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN member_phone TEXT DEFAULT NULL")
    if 'slip_image' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN slip_image TEXT DEFAULT NULL")
    if 'slip_uploaded_at' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN slip_uploaded_at TEXT DEFAULT NULL")

    # บันทึกชุดเมนูอาหารทั้งหมดของร้าน "ฟ้าใสตำนัว" (10 หมวดหมู่ 131 เมนูแซ่บ)
    fahsai_menu = [
        # --- 1. หมวด "ตำนัว" (16 เมนู) ---
        ("ตำไทย", "ตำนัว", 50, 18, "static/img/menu/menu1.webp", "รสเปรี้ยวหวานกลมกล่อม ถั่วคั่วใหม่ กุ้งแห้งเกรดเอ"),
        ("ตำไทยไข่เค็ม", "ตำนัว", 60, 22, "static/img/menu/menu2.webp", "ตำไทยครบรส ท็อปไข่เค็มเต็มใบ มันนัวเข้ากัน"),
        ("ตำไทยปู", "ตำนัว", 50, 18, "static/img/menu/menu3.webp", "ตำไทยรสเด็ด ใส่ปูดองเค็มสะอาด นัวกลมกล่อม"),
        ("ตำไทยปูปลาร้า", "ตำนัว", 50, 18, "static/img/menu/menu4.webp", "ตำไทยผสมน้ำปลาร้าต้มสุกสูตรเด็ด แซ่บนัวลงตัว"),
        ("ตำปูปลาร้า", "ตำนัว", 50, 18, "static/img/menu/menu5.webp", "เส้นมะละกอกรอบ ปลาร้าต้มสุกนัวเข้มข้น รสอีสานแท้"),
        ("ตำปลาร้า", "ตำนัว", 45, 15, "static/img/menu/menu6.webp", "ปลาร้านัวกลิ่นหอม รสแซ่บจัดจ้าน ซดน้ำส้มตำฟิน"),
        ("ตำปู", "ตำนัว", 45, 15, "static/img/menu/menu7.webp", "ตำปูเค็มสะอาด รสเปรี้ยวเผ็ดเค็มกำลังดี"),
        ("ตำซั่ว", "ตำนัว", 50, 18, "static/img/menu/menu8.webp", "ตำปลาร้าใส่เส้นขนมจีนนุ่มลื่น แคบหมูกรอบ"),
        ("ตำแตง", "ตำนัว", 50, 18, "static/img/menu/menu9.webp", "แตงกวาสดกรอบฉ่ำน้ำ คลุกเคล้าน้ำปลาร้าแซ่บนัว"),
        ("ตำถั่ว", "ตำนัว", 50, 18, "static/img/menu/menu10.webp", "ถั่วฝักยาวกรุบกรอบ ตำพริกแห้งและปลาร้าเข้มข้น"),
        ("ตำมะม่วง", "ตำนัว", 50, 18, "static/img/menu/menu11.webp", "มะม่วงเปรี้ยวกำลังดี ตำใส่น้ำปลาร้า แซ่บจี๊ดถึงใจ"),
        ("ตำข้าวโพด", "ตำนัว", 60, 22, "static/img/menu/menu12.webp", "ข้าวโพดหวานเม็ดเต่ง ตำคลุกน้ำยำรสแซ่บกลมกล่อม"),
        ("ตำข้าวโพดไข่เค็ม", "ตำนัว", 70, 26, "static/img/menu/menu13.webp", "ข้าวโพดหวานมัน ท็อปไข่เค็มชิ้นโต นัวฟิน"),
        ("ตำหมูยอ", "ตำนัว", 60, 24, "static/img/menu/menu14.webp", "หมูยอเนื้อแน่นหอมพริกไทย ตำคลุกน้ำส้มตำนัว"),
        ("ตำหอยดอง", "ตำนัว", 55, 20, "static/img/menu/menu15.webp", "หอยดองสะอาดรสกลมกล่อม ตำพริกสดแซ่บถึงใจ"),
        ("ตำป่า", "ตำนัว", 70, 28, "static/img/menu/menu16.webp", "ตำป่าเครื่องแน่น หน่อไม้ หอย ผักกาดดอง แคบหมู ขนมจีน"),

        # --- 2. หมวด "ตำพรีเมียม" (13 เมนู) ---
        ("ตำถาดฟ้าใสตำนัว", "ตำพรีเมียม", 159, 60, "static/img/menu/menu17.webp", "ตำถาดไซส์ใหญ่ เครื่องแน่น หมูยอ แคบหมู ไข่ต้ม ผักครบ"),
        ("ตำกุ้งสด", "ตำพรีเมียม", 89, 36, "static/img/menu/menu18.webp", "กุ้งสดเนื้อเด้งหวานฉ่ำ เคล้าน้ำปลาร้านัวถึงใจ"),
        ("ตำกุ้งสุก", "ตำพรีเมียม", 89, 36, "static/img/menu/menu19.webp", "กุ้งลวกสุกพอดีเนื้อหวานเด้ง ตำรสเปรี้ยวเผ็ดกลมกล่อม"),
        ("ตำแซลมอน", "ตำพรีเมียม", 149, 65, "static/img/menu/menu20.webp", "แซลมอนสดนำเข้าเกรดซาชิมิ ตำน้ำยำรสเด็ดเข้มข้น"),
        ("ตำหอยแครง", "ตำพรีเมียม", 99, 40, "static/img/menu/menu21.webp", "หอยแครงสดลวกสะดุ้ง เนื้อหวานกรุบ ตำแซ่บนัว"),
        ("ตำหมึกสาย", "ตำพรีเมียม", 99, 40, "static/img/menu/menu22.webp", "หมึกสายลวกกรุบกรอบ เด้งสู้ฟัน คลุกน้ำปลาร้าแซ่บ"),
        ("ตำทะเลรวม", "ตำพรีเมียม", 139, 55, "static/img/menu/menu23.webp", "ยกทะเลมาไว้ในครก กุ้ง หมึก หอยแครง จัดเต็ม"),
        ("ตำหมูกรอบ", "ตำพรีเมียม", 89, 36, "static/img/menu/menu24.webp", "หมูกรอบหนังฟูกรอบนอกนุ่มใน คลุกส้มตำรสเด็ด"),
        ("ตำคอหมูย่าง", "ตำพรีเมียม", 89, 36, "static/img/menu/menu25.webp", "คอหมูย่างเตาถ่านหอมๆ ตำคลุกน้ำส้มตำสุดฟิน"),
        ("ตำไข่เยี่ยวม้า", "ตำพรีเมียม", 65, 25, "static/img/menu/menu26.webp", "ไข่เยี่ยวม้าเนื้อเด้งมันนัว เข้ากันกับส้มตำรสจัด"),
        ("ตำเส้นเล็กหมูยอกากหมู", "ตำพรีเมียม", 79, 30, "static/img/menu/menu27.webp", "เส้นเล็กเหนียวนุ่ม คลุกน้ำปลาร้า หมูยอและกากหมูเจียวใหม่"),
        ("ตำมาม่าปลาร้านัว", "ตำพรีเมียม", 69, 26, "static/img/menu/menu28.webp", "เส้นมาม่าลวกกำลังดี ตำคลุกน้ำปลาร้าเครื่องแน่น"),
        ("ตำด้องแด้ง", "ตำพรีเมียม", 60, 22, "static/img/menu/menu29.webp", "เส้นด้องแด้งหนึบหนับ เอกลักษณ์อีสานแท้ ตำปลาร้านัว"),

        # --- 3. หมวด "ยำแซ่บ" (15 เมนู) ---
        ("ยำวุ้นเส้นหมูสับ", "ยำแซ่บ", 70, 26, "static/img/menu/menu30.webp", "วุ้นเส้นเหนียวนุ่ม ยำใส่หมูสับรวน มะนาวสดพริกขี้หนู"),
        ("ยำวุ้นเส้นโบราณ", "ยำแซ่บ", 75, 28, "static/img/menu/menu31.webp", "ยำวุ้นเส้นทรงเครื่อง ถั่วคั่ว กุ้งแห้ง หมูสับ หอมพริกเผา"),
        ("ยำวุ้นเส้นทะเล", "ยำแซ่บ", 99, 40, "static/img/menu/menu32.webp", "วุ้นเส้นคลุกเคล้ากุ้งและปลาหมึกสด น้ำยำรสจี๊ดจ๊าด"),
        ("ยำมาม่าหมูสับ", "ยำแซ่บ", 70, 26, "static/img/menu/menu33.webp", "มาม่าลวกเหนียวนุ่ม ยำหมูสับและหมูยอ รสแซ่บถึงใจ"),
        ("ยำมาม่ารวมมิตร", "ยำแซ่บ", 99, 40, "static/img/menu/menu34.webp", "มาม่ารวมมิตร กุ้ง หมึก หมูยอ ไส้กรอก ครบเครื่อง"),
        ("ยำหมูยออุบล", "ยำแซ่บ", 70, 26, "static/img/menu/menu35.webp", "หมูยออุบลแท้เนื้อเด้ง หอมพริกไทย ยำน้ำมะนาวสด"),
        ("ยำหมูยอไข่แดงเค็ม", "ยำแซ่บ", 89, 36, "static/img/menu/menu36.webp", "หมูยออุบลจับคู่ไข่แดงเค็มมันหนึบ น้ำยำปลาร้า/ไม่ปลาร้า"),
        ("ยำกุนเชียง", "ยำแซ่บ", 70, 26, "static/img/menu/menu37.webp", "กุนเชียงหมูทอดหอมหวาน ยำตัดรสเปรี้ยวเผ็ดแตงกวากรอบ"),
        ("ยำเล็บมือนาง", "ยำแซ่บ", 75, 28, "static/img/menu/menu38.webp", "เล็บมือนางกรุบกรอบ ยำพริกสดมะนาวแท้ เคี้ยวเพลิน"),
        ("ยำไข่ดาว", "ยำแซ่บ", 60, 22, "static/img/menu/menu39.webp", "ไข่ดาวทอดกรอบไข่แดงเยิ้ม ราดน้ำยำหมูสับรสเด็ด"),
        ("ยำไข่เยี่ยวม้า", "ยำแซ่บ", 70, 26, "static/img/menu/menu40.webp", "ไข่เยี่ยวม้าทรงเครื่อง โรยขิงดอง หอมแดง พริกขี้หนูซอย"),
        ("ยำกุ้งสดน้ำปลาร้า", "ยำแซ่บ", 99, 42, "static/img/menu/menu41.webp", "กุ้งสดเนื้อหวานเด้ง คลุกน้ำยำปลาร้าต้มสุกหอมนัว"),
        ("ยำแซลมอนน้ำปลาร้า", "ยำแซ่บ", 159, 68, "static/img/menu/menu42.webp", "แซลมอนซาชิมิชิ้นหนา คลุกเคล้าน้ำยำปลาร้ารสจัดจ้าน"),
        ("ยำหอยแครง", "ยำแซ่บ", 109, 45, "static/img/menu/menu43.webp", "หอยแครงลวกสุกพอดี ยำใส่ตะไคร้ซอย หอมแดง พริกสด"),
        ("ยำทะเลรวมน้ำยำซีฟู้ด", "ยำแซ่บ", 149, 62, "static/img/menu/menu44.webp", "กุ้ง หมึก หอยแครง ราดน้ำยำซีฟู้ดพริกขี้หนูสวนแท้"),

        # --- 4. หมวด "ลาบ & ก้อย & น้ำตก" (13 เมนู) ---
        ("ลาบหมู", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu45.webp", "หมูสับคลุกข้าวคั่วใหม่ พริกป่น มะนาวสด หอมสะระแหน่"),
        ("ลาบหมูตับหวาน", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu46.webp", "ลาบหมูสับผสมตับหมูลวกสุกกำลังดี นุ่มหวานไม่แข็ง"),
        ("ลาบไก่", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu47.webp", "เนื้อไก่สับนุ่ม คลุกเคล้าเครื่องลาบอีสานแท้หอมข้าวคั่ว"),
        ("ลาบเป็ดอุดร", "ลาบ & ก้อย & น้ำตก", 85, 35, "static/img/menu/menu48.webp", "ลาบเป็ดสูตรอุดรแท้ หอมข่าคั่วสมุนไพร โรยหนังเป็ดทอดกรอบ"),
        ("ลาบเนื้อสุก", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu49.webp", "เนื้อวัวสับรวนสุก คลุกเครื่องลาบพริกป่นข้าวคั่วหอมกรุ่น"),
        ("ลาบปลาดุกย่าง", "ลาบ & ก้อย & น้ำตก", 70, 28, "static/img/menu/menu50.webp", "ปลาดุกย่างเตาถ่านแกะเนื้อสับ คลุกเครื่องลาบสมุนไพร"),
        ("ลาบปลาหมึก", "ลาบ & ก้อย & น้ำตก", 99, 40, "static/img/menu/menu51.webp", "ปลาหมึกสดลวกเด้งกรอบ คลุกเครื่องลาบรสแซ่บจี๊ด"),
        ("ก้อยเนื้อคั่ว", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu52.webp", "ก้อยเนื้อสับคั่วสุกหอมสมุนไพร เลือกขมหรือไม่ขมได้"),
        ("ก้อยเนื้อดิบขม", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu53.webp", "ก้อยเนื้อวัวสดคัดพิเศษ ปรุงรสขมอำพันอีสานแท้"),
        ("น้ำตกคอหมูย่าง", "ลาบ & ก้อย & น้ำตก", 85, 35, "static/img/menu/menu54.webp", "คอหมูย่างฉ่ำๆ คลุกเครื่องน้ำตกอีสานแท้ สุดยอดเมนูขายดี"),
        ("น้ำตกหมู", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu55.webp", "เนื้อหมูย่างนุ่มฉ่ำ คลุกน้ำยำน้ำตกรสแซ่บกลมกล่อม"),
        ("น้ำตกเนื้อ", "ลาบ & ก้อย & น้ำตก", 85, 36, "static/img/menu/menu56.webp", "เนื้อย่างติดมันหั่นชิ้น ปรุงน้ำตกรสแซ่บหอมข้าวคั่ว"),
        ("ตับหวาน", "ลาบ & ก้อย & น้ำตก", 75, 30, "static/img/menu/menu57.webp", "ตับหมูชิ้นหนาลวกสุกกำลังดี เนื้อนุ่มหวานฉ่ำคลุกเครื่องลาบ"),

        # --- 5. หมวด "ย่าง & ทอด" (16 เมนู) ---
        ("ไก่ย่างเขาสวนกวาง (ครึ่งตัว)", "ย่าง & ทอด", 110, 45, "static/img/menu/menu58.webp", "ไก่หมักสมุนไพรสูตรเขาสวนกวาง ย่างหนังกรอบเนื้อนุ่ม"),
        ("ไก่ย่างเขาสวนกวาง (ตัว)", "ย่าง & ทอด", 210, 85, "static/img/menu/menu59.webp", "ไก่ย่างเขาสวนกวางเต็มตัว เสิร์ฟพร้อมน้ำจิ้มแจ่วและน้ำจิ้มหวาน"),
        ("ปีกไก่ย่าง (ไม้ละ)", "ย่าง & ทอด", 25, 10, "static/img/menu/menu60.webp", "ปีกไก่หมักเครื่องเทศเสียบไม้ย่างเตาถ่าน หอมกรุ่น"),
        ("คอหมูย่างนมสด", "ย่าง & ทอด", 89, 36, "static/img/menu/menu61.webp", "คอหมูแท้หมักนมสด ย่างไฟอ่อนนุ่มละลายในปาก จิ้มแจ่วพริกป่น"),
        ("เนื้อย่างติดมัน", "ย่าง & ทอด", 99, 42, "static/img/menu/menu62.webp", "เสือร้องไห้เนื้อติดมันย่างเตาถ่านหอมๆ จิ้มแจ่วขม/เปรี้ยว"),
        ("ไส้ย่าง", "ย่าง & ทอด", 79, 32, "static/img/menu/menu63.webp", "ไส้อ่อนหมูต้มสมุนไพรแล้วย่างเตาถ่าน กรอบนอกนุ่มในไม่ขม"),
        ("ลิ้นหมูย่าง", "ย่าง & ทอด", 79, 32, "static/img/menu/menu64.webp", "ลิ้นหมูย่างกรุบเด้ง หอมกลิ่นเตาถ่าน ทานคู่กระเทียมโทน"),
        ("ปลาดุกย่าง (ตัว)", "ย่าง & ทอด", 50, 20, "static/img/menu/menu65.webp", "ปลาดุกหมักเครื่องเทศย่างสุกเหลืองหอม ทานคู่ส้มตำเข้ากัน"),
        ("ปลานิลเผาเกลือ", "ย่าง & ทอด", 160, 65, "static/img/menu/menu66.webp", "ปลานิลสดตัวโตยัดไส้สมุนไพรพอกเกลือเผา เสิร์ฟพร้อมชุดผักและขนมจีน"),
        ("ไก่ทอดเกลือ", "ย่าง & ทอด", 79, 30, "static/img/menu/menu67.webp", "เนื้อไก่ทอดเกลือกรอบนอกฉ่ำใน เค็มกำลังดี ทานเล่นเพลิน"),
        ("ปีกไก่ทอดน้ำปลา", "ย่าง & ทอด", 79, 30, "static/img/menu/menu68.webp", "ปีกไก่กลางทอดน้ำปลาแท้ หนังกรอบหอมอร่อย"),
        ("เอ็นข้อไก่ทอด", "ย่าง & ทอด", 79, 30, "static/img/menu/menu69.webp", "เอ็นข้อไก่ชุบแป้งบางๆ ทอดกรอบโรยงาขาวและใบมะกรูด"),
        ("หมูสามชั้นทอดน้ำปลา", "ย่าง & ทอด", 85, 34, "static/img/menu/menu70.webp", "สามชั้นคัดสวยทอดน้ำปลากรอบฉ่ำ เสิร์ฟพร้อมน้ำจิ้มแจ่วซีฟู้ด"),
        ("หมูแดดเดียวทอด", "ย่าง & ทอด", 79, 30, "static/img/menu/menu71.webp", "หมูแดดเดียวสูตรทางร้าน ทอดร้อนๆ โรยงาหอม"),
        ("เนื้อแดดเดียวทอด", "ย่าง & ทอด", 89, 38, "static/img/menu/menu72.webp", "เนื้อวัวแดดเดียวทอดไฟกลาง นุ่มไม่เหนียว หอมสมุนไพร"),
        ("แคบหมูกรอบ", "ย่าง & ทอด", 25, 10, "static/img/menu/menu73.webp", "แคบหมูติดมันทอดใหม่ทุกวัน กรอบฟู ทานคู่ส้มตำ"),

        # --- 6. หมวด "ต้มแซ่บ & แกงอีสาน" (15 เมนู) ---
        ("ต้มแซ่บกระดูกอ่อน", "ต้มแซ่บ & แกงอีสาน", 89, 35, "static/img/menu/menu74.webp", "กระดูกอ่อนหมูตุ๋นเปื่อยนุ่ม น้ำซุปต้มแซ่บพริกคั่วหอมข้าวคั่ว"),
        ("ต้มแซ่บเนื้อลาย", "ต้มแซ่บ & แกงอีสาน", 99, 42, "static/img/menu/menu75.webp", "เนื้อน่องลายตุ๋นนุ่มเด้ง ซุปสมุนไพรเปรี้ยวเผ็ดจี๊ดจ๊าด"),
        ("ต้มแซ่บเครื่องในเนื้อ", "ต้มแซ่บ & แกงอีสาน", 99, 42, "static/img/menu/menu76.webp", "เครื่องในวัวต้มสะอาดไร้กลิ่นคาว ปรุงรสแซ่บถึงเครื่อง"),
        ("ต้มโคล้งปลากรอบ", "ต้มแซ่บ & แกงอีสาน", 89, 35, "static/img/menu/menu77.webp", "ปลาเนื้ออ่อนย่างกรอบ ต้มโคล้งน้ำมะขามเปียกหอมพริกแห้งคั่ว"),
        ("ต้มยำกุ้งน้ำข้น", "ต้มแซ่บ & แกงอีสาน", 120, 50, "static/img/menu/menu78.webp", "กุ้งสดตัวโต ต้มยำน้ำข้นมันกุ้งแท้ รสเข้มข้นกลมกล่อม"),
        ("ต้มยำรวมมิตรทะเล", "ต้มแซ่บ & แกงอีสาน", 130, 55, "static/img/menu/menu79.webp", "กุ้ง หมึก หอย ปลา ต้มยำสมุนไพรสด ซดร้อนคล่องคอ"),
        ("แกงอ่อมหมู", "ต้มแซ่บ & แกงอีสาน", 80, 30, "static/img/menu/menu80.webp", "แกงอ่อมหมูใส่ผักชีลาวและผักพื้นบ้าน หอมน้ำปลาร้าและข้าวคั่ว"),
        ("แกงอ่อมไก่บ้าน", "ต้มแซ่บ & แกงอีสาน", 80, 32, "static/img/menu/menu81.webp", "ไก่บ้านเนื้อแน่นคั่วพริกแกงอ่อม ใส่ฟักทองและผักชีลาว"),
        ("แกงอ่อมเนื้อ", "ต้มแซ่บ & แกงอีสาน", 90, 38, "static/img/menu/menu82.webp", "เนื้อวัวหั่นชิ้นแกงอ่อมสมุนไพรอีสานแท้ เข้มข้นถึงใจ"),
        ("แกงเห็ดรวมอีสาน", "ต้มแซ่บ & แกงอีสาน", 75, 28, "static/img/menu/menu83.webp", "เห็ด 3 อย่างต้มน้ำใบย่านางคั้นสด ใส่บวบ ฟักทอง ชะอม และใบแมงลัก"),
        ("แกงหน่อไม้ใบย่านาง", "ต้มแซ่บ & แกงอีสาน", 75, 28, "static/img/menu/menu84.webp", "หน่อไม้สดต้มน้ำใบย่านาง ใส่ข้าวเบือเหนียวข้น หอมชะอม"),
        ("แกงผักหวานไข่มดแดง", "ต้มแซ่บ & แกงอีสาน", 120, 55, "static/img/menu/menu85.webp", "เมนูหากินยาก ผักหวานป่าอ่อนๆ แกงใส่ไข่มดแดงมันตึ๊บ"),
        ("ต้มซุปเปอร์ขาไก่", "ต้มแซ่บ & แกงอีสาน", 80, 30, "static/img/menu/menu86.webp", "ขาไก่ตุ๋นจนเปื่อยร่อน ซุปพริกขี้หนูสวนเปรี้ยวเผ็ดสะใจ"),
        ("ต้มขมเนื้อเปื่อย", "ต้มแซ่บ & แกงอีสาน", 90, 38, "static/img/menu/menu87.webp", "เนื้อเปื่อยและเครื่องในต้มขมสูตรอีสานดั้งเดิม หอมใบมะกรูด"),
        ("ต้มจืดเต้าหู้หมูสับ", "ต้มแซ่บ & แกงอีสาน", 65, 24, "static/img/menu/menu88.webp", "ซุปใสกลมกล่อม เต้าหู้ไข่ หมูสับปั้นก้อน และผักกาดขาว ช่วยแก้เผ็ด"),

        # --- 7. หมวด "อาหารจานเดียว" (14 เมนู) ---
        ("ผัดกะเพราหมูสับราดข้าว", "อาหารจานเดียว", 55, 20, "static/img/menu/menu89.webp", "กะเพราหมูสับผัดพริกแห้งไร้ถั่วฝักยาว หอมกลิ่นกระทะ"),
        ("ผัดกะเพราหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu90.webp", "หมูกรอบชิ้นโตผัดกะเพราพริกสด รสจัดจ้านถึงเครื่อง"),
        ("ผัดกะเพราเนื้อสับราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu91.webp", "เนื้อโคขุนสับผัดกะเพราใบกะเพราแดงหอมฉุน"),
        ("ผัดกะเพราทะเลรวมราดข้าว", "อาหารจานเดียว", 75, 32, "static/img/menu/menu92.webp", "กุ้งและปลาหมึกสดผัดกะเพรารสเผ็ดร้อน เสิร์ฟคู่ข้าวหอมมะลิ"),
        ("ข้าวผัดไข่", "อาหารจานเดียว", 45, 16, "static/img/menu/menu93.webp", "ข้าวผัดไข่ร่วนหอมกลิ่นกระทะ เด็กทานได้ผู้ใหญ่ทานดี"),
        ("ข้าวผัดหมู", "อาหารจานเดียว", 55, 20, "static/img/menu/menu94.webp", "ข้าวผัดหมูหมักนุ่ม ผัดไฟแรงเม็ดข้าวร่วนสวย"),
        ("ข้าวผัดกุ้ง", "อาหารจานเดียว", 70, 28, "static/img/menu/menu95.webp", "ข้าวผัดกุ้งสดตัวโต หอมมันกุ้ง บีบมะนาวพริกน้ำปลาเข้ากัน"),
        ("ข้าวผัดโบราณ", "อาหารจานเดียว", 60, 22, "static/img/menu/menu96.webp", "ข้าวผัดซอสดำใส่หมูและคะน้า สีเข้มข้นหอมอร่อยสไตล์โบราณ"),
        ("ข้าวผัดน้ำพริกเผาหมูกรอบ", "อาหารจานเดียว", 70, 28, "static/img/menu/menu97.webp", "ข้าวผัดคลุกน้ำพริกเผาหอมมัน ท็อปด้วยหมูกรอบหนังฟู"),
        ("ผัดคะน้าหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu98.webp", "ยอดคะน้าอ่อนกรอบผัดไฟแดงกับหมูกรอบชิ้นหนา"),
        ("ผัดพริกแกงหมูกรอบราดข้าว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu99.webp", "พริกแกงเผ็ดโขลกเองผัดหมูกรอบ ใส่ใบมะกรูดซอยหอมๆ"),
        ("ข้าวไข่เจียวหมูสับ", "อาหารจานเดียว", 45, 16, "static/img/menu/menu100.webp", "ไข่เจียวหมูสับทอดฟูกรอบ ราดข้าวสวยร้อนๆ พร้อมซอสพริก"),
        ("ข้าวคอหมูย่างน้ำจิ้มแจ่ว", "อาหารจานเดียว", 65, 26, "static/img/menu/menu101.webp", "ข้าวสวยร้อนๆ โปะคอหมูย่างเตาถ่านฉ่ำๆ และน้ำจิ้มแจ่ว"),
        ("ข้าวหน้าเนื้อย่างแจ่ว", "อาหารจานเดียว", 75, 32, "static/img/menu/menu102.webp", "ข้าวหน้าเนื้อย่างติดมันนุ่มๆ เสิร์ฟคู่แจ่วพริกป่นและแตงกวา"),

        # --- 8. หมวด "ของหวาน" (10 เมนู) ---
        ("ลอดช่องสิงคโปร์", "ของหวาน", 35, 12, "static/img/menu/menu103.webp", "เส้นลอดช่องเหนียวหนึบ น้ำกะทิสดหอมขนุนฉีก เย็นชื่นใจ"),
        ("ลอดช่องไทยน้ำกะทิแตงไทย", "ของหวาน", 35, 12, "static/img/menu/menu104.webp", "ลอดช่องใบเตยแท้ น้ำกะทิน้ำตาลโตนดเคี่ยวหอมและแตงไทย"),
        ("ทับทิมกรอบน้ำกะทิ", "ของหวาน", 40, 15, "static/img/menu/menu105.webp", "แห้วกรอบหุ้มแป้งสีทับทิม ราดหัวกะทิสดอบควันเทียน"),
        ("สลิ่มน้ำกะทิอบควันเทียน", "ของหวาน", 35, 12, "static/img/menu/menu106.webp", "เส้นสลิ่ม 3 สีเหนียวนุ่ม น้ำกะทิสดหอมกลิ่นควันเทียน"),
        ("รวมมิตรน้ำกะทิสด", "ของหวาน", 35, 12, "static/img/menu/menu107.webp", "รวมมิตรเครื่องแน่น ลอดช่อง ทับทิมกรอบ ขนุน มันเชื่อม"),
        ("บัวลอยไข่หวาน", "ของหวาน", 40, 15, "static/img/menu/menu108.webp", "บัวลอยแป้งนุ่มสีธรรมชาติในน้ำกะทิอุ่นๆ พร้อมไข่หวานสุกพอดี"),
        ("กล้วยบวชชี", "ของหวาน", 30, 10, "static/img/menu/menu109.webp", "กล้วยน้ำว้าห่ามต้มกะทิสด หอมหวานมันเค็มกลมกล่อม"),
        ("เฉาก๊วยชากังราวนมสด", "ของหวาน", 35, 12, "static/img/menu/menu110.webp", "เฉาก๊วยแท้เนื้อหนึบ ใส่นมสดและโรยน้ำตาลทรายแดง"),
        ("ไอศกรีมกะทิสดโบราณ", "ของหวาน", 35, 12, "static/img/menu/menu111.webp", "ไอศกรีมกะทิสดแท้ โรยถั่วลิสงคั่ว ลูกชิด และข้าวเหนียวมูน"),
        ("ข้าวเหนียวมะม่วงอกร่อง", "ของหวาน", 69, 28, "static/img/menu/menu112.webp", "มะม่วงสุกหวานฉ่ำ เสิร์ฟคู่ข้าวเหนียวมูนกะทิสดและถั่วทอง"),

        # --- 9. หมวด "เครื่องเคียง & ข้าว" (9 เมนู) ---
        ("ข้าวเหนียวนึ่ง", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu113.webp", "ข้าวเหนียวเขี้ยวงูนึ่งใหม่ร้อนๆ นุ่มติดใจไม่แข็ง"),
        ("ข้าวสวยหอมมะลิ", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu114.webp", "ข้าวหอมมะลิแท้ 100% หุงนุ่มหอมกรุ่น"),
        ("ขนมจีน", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu115.webp", "เส้นขนมจีนแป้งหมักสดใหม่ นุ่มลื่น ทานคู่ส้มตำ"),
        ("หมูยอลวกจิ้ม", "เครื่องเคียง & ข้าว", 50, 20, "static/img/menu/menu116.webp", "หมูยออุบลหั่นชิ้นลวกร้อนๆ จิ้มน้ำจิ้มซีฟู้ด"),
        ("ผักบุ้งลวก", "เครื่องเคียง & ข้าว", 15, 5, "static/img/menu/menu117.webp", "ผักบุ้งยอดอ่อนลวกกรอบสีเขียวสด ทานคู่ส้มตำ"),
        ("กะหล่ำปลีสด", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu118.webp", "กะหล่ำปลีสดแช่เย็นกรอบหวาน ช่วยลดความเผ็ด"),
        ("แตงกวาสด", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu119.webp", "แตงกวาสดหั่นชิ้นแช่เย็น กรอบฉ่ำน้ำ"),
        ("ไข่ดาว", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu120.webp", "ไข่ไก่สดทอดดาวกรอบนอกไข่แดงเยิ้ม"),
        ("ไข่ต้ม", "เครื่องเคียง & ข้าว", 10, 4, "static/img/menu/menu121.webp", "ไข่ต้มยางมะตูมมันนัว ทานคู่ส้มตำหรือน้ำตก"),

        # --- 10. หมวด "เครื่องดื่ม" (10 เมนู) ---
        ("น้ำเปล่า", "เครื่องดื่ม", 15, 6, "static/img/menu/menu122.webp", "น้ำดื่มบริสุทธิ์ขวดเย็นชื่นใจ"),
        ("น้ำแข็ง", "เครื่องดื่ม", 10, 3, "static/img/menu/menu123.webp", "น้ำแข็งหลอดสะอาดใส่กระติก/แก้ว"),
        ("น้ำอัดลม", "เครื่องดื่ม", 25, 12, "static/img/menu/menu124.webp", "โคล่า/น้ำอัดลมกระป๋องเย็นซ่าสดชื่น"),
        ("น้ำแดง", "เครื่องดื่ม", 25, 10, "static/img/menu/menu125.webp", "น้ำหวานกลิ่นสละ หอมหวานเย็นชื่นใจ"),
        ("น้ำเขียว", "เครื่องดื่ม", 25, 10, "static/img/menu/menu126.webp", "น้ำหวานกลิ่นครีมโซดา สดชื่นดับกระหาย"),
        ("ชามะนาว", "เครื่องดื่ม", 35, 12, "static/img/menu/menu127.webp", "ชาดำแท้ผสมน้ำมะนาวคั้นสด เปรี้ยวหวานลงตัว"),
        ("ชาเย็น", "เครื่องดื่ม", 35, 12, "static/img/menu/menu128.webp", "ชาไทยแท้สูตรโบราณ หอมมันนมสดแท้ ดับเผ็ด"),
        ("น้ำเก๊กฮวย", "เครื่องดื่ม", 30, 10, "static/img/menu/menu129.webp", "เก๊กฮวยต้มสมุนไพรแท้ หวานน้อยหอมสดชื่น"),
        ("น้ำกระเจี๊ยบ", "เครื่องดื่ม", 30, 10, "static/img/menu/menu130.webp", "กระเจี๊ยบแดงต้มสด เปรี้ยวอมหวานชุ่มคอ"),
        ("น้ำลำไย", "เครื่องดื่ม", 35, 12, "static/img/menu/menu131.webp", "น้ำลำไยเนื้อแน่น หวานหอมกลมกล่อม")
    ]
    
    # ตรวจสอบว่าตารางว่างเปล่า หรือมีการแก้ไขรายการเมนู/รูปภาพในโค้ด database.py หรือไม่
    c.execute("SELECT COUNT(*) FROM menu_items WHERE image LIKE '%unsplash%'")
    has_old_unsplash = (c.fetchone()[0] > 0)
    
    c.execute("SELECT COUNT(*) FROM menu_items")
    is_empty = (c.fetchone()[0] == 0)

    # ตารางเก็บค่า Hash ของชุดเมนูใน database.py เพื่อตรวจจับการแก้ไขโค้ดบน GitHub และอัปเดตฐานข้อมูลอัตโนมัติ
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT
        )
    """)
    current_menu_hash = hashlib.sha256(repr(fahsai_menu).encode('utf-8')).hexdigest()
    c.execute("SELECT meta_value FROM system_meta WHERE meta_key = 'fahsai_menu_hash'")
    saved_hash_row = c.fetchone()
    saved_menu_hash = saved_hash_row[0] if saved_hash_row else None

    if is_empty or has_old_unsplash or (saved_menu_hash != current_menu_hash):
        if is_empty or has_old_unsplash:
            c.execute('DELETE FROM menu_items')
            c.executemany('INSERT OR REPLACE INTO menu_items (name, category, price, cost, image, description) VALUES (?, ?, ?, ?, ?, ?)', fahsai_menu)
        else:
            # ซิงค์ข้อมูลและรูปภาพล่าสุดจาก fahsai_menu ลงในฐานข้อมูลโดยตรง
            for m_name, m_cat, m_price, m_cost, m_img, m_desc in fahsai_menu:
                c.execute("SELECT id FROM menu_items WHERE name = ?", (m_name,))
                row_exist = c.fetchone()
                if row_exist:
                    c.execute("""
                        UPDATE menu_items
                        SET category = ?, price = ?, cost = ?, image = ?, description = ?
                        WHERE id = ?
                    """, (m_cat, m_price, m_cost, m_img, m_desc, row_exist[0]))
                else:
                    c.execute("""
                        INSERT INTO menu_items (name, category, price, cost, image, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (m_name, m_cat, m_price, m_cost, m_img, m_desc))
        c.execute("""
            INSERT OR REPLACE INTO system_meta (meta_key, meta_value)
            VALUES ('fahsai_menu_hash', ?)
        """, (current_menu_hash,))

    # ข้อมูลสมาชิกจำลองเริ่มต้น 10 คน (ถ้ายังไม่มีสมาชิกในระบบ)
    c.execute("SELECT COUNT(*) FROM members")
    if c.fetchone()[0] == 0:
        sample_members = [
            ("สมชาย", "สายกิน", "0812345678", 85, "2026-09-15 11:30:00"),
            ("กานดา", "สุขสมบูรณ์", "0898765432", 64, "2026-09-18 12:45:00"),
            ("ปิยะพงษ์", "รักนัว", "0923456789", 52, "2026-09-20 18:20:00"),
            ("อรทัย", "แซ่บหลาย", "0861122334", 41, "2026-09-25 13:10:00"),
            ("นฤมล", "ทองดี", "0956677889", 35, "2026-10-01 17:50:00"),
            ("ธนกร", "มีทรัพย์", "0845566778", 28, "2026-10-02 12:15:00"),
            ("ชญาดา", "พัฒนาเลิศ", "0937734851", 20, "2026-10-04 11:00:00"),
            ("วรวิทย์", "เจริญผล", "0879988776", 15, "2026-10-05 19:30:00"),
            ("สุภาวรรณ", "ใจดี", "0912233445", 10, "2026-10-07 14:00:00"),
            ("กิตติศักดิ์", "ยอดเยี่ยม", "0834455667", 6, "2026-10-08 16:20:00")
        ]
        c.executemany(
            "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, ?, ?)",
            sample_members
        )

    # 6. ตารางผู้ดูแลระบบ / ผู้ใช้งานหลังร้าน (admin_users)
    # เก็บรหัสผ่านแบบเข้ารหัส Secure Hash (SHA-256 + Salt)
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,     -- ชื่อผู้ใช้งานสำหรับล็อกอิน
            password_hash TEXT NOT NULL,       -- รหัสผ่านที่เข้ารหัสแฮชแล้ว
            salt TEXT NOT NULL,                -- ค่า Salt ป้องกัน Rainbow Table
            full_name TEXT,                    -- ชื่อ-นามสกุลเจ้าหน้าที่
            role TEXT DEFAULT 'admin',         -- บทบาท: admin, manager, cashier
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ตรวจสอบและอัปเกรดคอลัมน์ email ในตาราง admin_users
    c.execute("PRAGMA table_info(admin_users)")
    admin_cols = [col[1] for col in c.fetchall()]
    if 'email' not in admin_cols:
        c.execute("ALTER TABLE admin_users ADD COLUMN email TEXT DEFAULT 'owner@fahsaitumnua.com'")

    # 7. ตารางประวัติและรหัสกู้คืนรหัสผ่าน OTP (password_resets)
    c.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            is_used INTEGER DEFAULT 0
        )
    ''')

    # สร้างบัญชีผู้ดูแลระบบเริ่มต้น (Default Admin) หากยังไม่มี
    def_salt = "fahsai_salt_secure_2026"
    def_hash = hashlib.sha256((def_salt + "adminfahsaitumnua@12").encode('utf-8')).hexdigest()
    old_hash = hashlib.sha256((def_salt + "admin1234").encode('utf-8')).hexdigest()
        
    c.execute("SELECT id, password_hash FROM admin_users WHERE LOWER(username) = 'admin'")
    existing_admin = c.fetchone()
    if not existing_admin:
        c.execute("""
            INSERT INTO admin_users(username, password_hash, salt, full_name, role, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", def_hash, def_salt, "ผู้ดูแลระบบ (Admin)", "admin", "owner@fahsaitumnua.com"))
    else:
        if existing_admin[1] == old_hash:
            c.execute("""
                UPDATE admin_users
                SET password_hash = ?, salt = ?
                WHERE id = ?
            """, (def_hash, def_salt, existing_admin[0]))
        c.execute("UPDATE admin_users SET email = 'owner@fahsaitumnua.com' WHERE email IS NULL OR email = ''")

    # สร้างโต๊ะอาหารเริ่มต้น 10 โต๊ะ (หากยังไม่มีโต๊ะในระบบ)
    c.execute("SELECT COUNT(*) FROM tables")
    if c.fetchone()[0] == 0:
        default_tables = [(i, f"โต๊ะที่ {i}", "available") for i in range(1, 11)]
        c.executemany("INSERT INTO tables (table_number, name, status) VALUES (?, ?, ?)", default_tables)

    conn.commit()
    conn.close()


