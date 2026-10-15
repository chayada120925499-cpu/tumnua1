# ==============================================================================
# ระบบเสียงแจ้งเตือนออเดอร์ในครัว (Order Chime Sound Synthesizer)
# ==============================================================================
import base64
import wave
import struct
import math
import io
import streamlit as st

@st.cache_data
def get_bell_sound_b64() -> str:
    """
    สังเคราะห์คลื่นเสียงกระดิ่งเตือน (Chime) ความถี่คู่ 784Hz และ 1046.5Hz ขึ้นมาใน RAM
    แล้วบันทึกเป็น WAV ในหน่วยความจำโดยตรง
    """
    sample_rate = 22050
    duration = 0.85
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            decay = math.exp(-4.2 * t)
            v1 = math.sin(2 * math.pi * 784.0 * t)
            v2 = math.sin(2 * math.pi * 1046.5 * t) if t > 0.08 else 0
            sample = int(32767 * 0.45 * (v1 * 0.55 + v2 * 0.45) * decay)
            wav_file.writeframes(struct.pack('<h', sample))
    return base64.b64encode(buf.getvalue()).decode()

def play_order_sound():
    """
    สั่งเล่นเสียงกระดิ่งเตือนในเบราว์เซอร์อัตโนมัติ (Autoplay)
    เมื่อมีออเดอร์ใหม่ที่ลูกค้าเพิ่งสั่งเข้ามาในห้องครัว
    """
    sound_b64 = get_bell_sound_b64()
    audio_html = f'''
    <audio autoplay style="display:none;">
        <source src="data:audio/wav;base64,{sound_b64}" type="audio/wav">
    </audio>
    <script>
    try {{
        const snd = new Audio("data:audio/wav;base64,{sound_b64}");
        snd.play().catch(e => {{ console.log("Audio waiting for gesture:", e); }});
    }} catch(e) {{}}
    </script>
    '''
    st.markdown(audio_html, unsafe_allow_html=True)
