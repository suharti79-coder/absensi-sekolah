import streamlit as st
import pandas as pd
import datetime
import pytz
import base64
import streamlit.components.v1 as components
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Absensi Biometrik", page_icon="🏫", layout="centered")

# --- DATABASE SEDERHANA (CSV) ---
FILE_ABSENSI = "data_absensi.csv"

def simpan_ke_csv(data_baru):
    df_baru = pd.DataFrame([data_baru])
    if os.path.exists(FILE_ABSENSI):
        df_lama = pd.read_csv(FILE_ABSENSI)
        df_final = pd.concat([df_lama, df_baru], ignore_index=True)
    else:
        df_final = df_baru
    df_final.to_csv(FILE_ABSENSI, index=False)

# --- INISIALISASI DATA SEMENTARA ---
if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame([{
        'nip': '12345', 'name': 'Budi Guru', 'photo_uploaded': False, 'photo_base64': ''
    }])

# --- SIDEBAR (NAVIGASI) ---
st.sidebar.title("Menu Navigasi")
menu = st.sidebar.radio("Pilih Halaman:", ["Formulir Presensi (Pegawai)", "Panel Admin"])

# ==========================================
# HALAMAN 1: FORMULIR PRESENSI (PEGAWAI)
# ==========================================
if menu == "Formulir Presensi (Pegawai)":
    st.title("📸 Formulir Presensi Harian")
    
    # 1. Pilih Pegawai
    pegawai_pilihan = st.selectbox("Pilih Nama Anda:", st.session_state.employees['name'].tolist())
    emp_data = st.session_state.employees[st.session_state.employees['name'] == pegawai_pilihan].iloc[0]
    idx = st.session_state.employees.index[st.session_state.employees['name'] == pegawai_pilihan][0]

    # 2. Kamera & AI Client-Side (Pendekatan Hibrida)
    st.markdown("### Rekam Wajah (Verifikasi AI Lokal)")
    
    if emp_data['photo_uploaded'] and emp_data['photo_base64'] != '':
        img_camera = st.camera_input("Ambil Foto Wajah Anda")
        
        if img_camera:
            bytes_data = img_camera.getvalue()
            cam_base64 = f"data:image/jpeg;base64,{base64.b64encode(bytes_data).decode('utf-8')}"
            
            st.info("Memproses kecocokan wajah di HP/Laptop Anda...")
            
            # INJEKSI JS UNTUK AI
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/dist/face-api.js"></script>
                <style>
                    body {{ text-align: center; font-family: sans-serif; margin: 0; }}
                    #status {{ margin-top: 10px; font-weight: bold; color: #d9534f; }}
                    #kode {{ margin-top: 15px; font-size: 22px; font-weight: bold; color: white; background: #5cb85c; padding: 10px; border-radius: 5px; display: none; }}
                </style>
            </head>
            <body>
                <div id="status">Memuat AI (Tunggu sebentar)...</div>
                <div id="kode">KODE VALIDASI: <b>COCOK100</b></div>
                <img id="refImg" src="{emp_data['photo_base64']}" style="display:none;" />
                <img id="camImg" src="{cam_base64}" style="display:none;" />

                <script>
                    async function runAI() {{
                        const status = document.getElementById('status');
                        try {{
                            const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model';
                            await faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL);
                            await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
                            await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
                            
                            status.innerText = "Menganalisis kecocokan wajah...";
                            
                            const refImg = document.getElementById('refImg');
                            const camImg = document.getElementById('camImg');
                            
                            const refDetect = await faceapi.detectSingleFace(refImg).withFaceLandmarks().withFaceDescriptor();
                            const camDetect = await faceapi.detectSingleFace(camImg).withFaceLandmarks().withFaceDescriptor();
                            
                            if(!refDetect) {{ status.innerText = "Wajah foto acuan Admin tidak terdeteksi."; return; }}
                            if(!camDetect) {{ status.innerText = "Wajah Anda tidak terdeteksi pada foto jepretan."; return; }}
                            
                            const faceMatcher = new faceapi.FaceMatcher(refDetect);
                            const match = faceMatcher.findBestMatch(camDetect.descriptor);
                            
                            if(match.distance <= 0.5) {{ 
                                status.style.display = "none";
                                document.getElementById('kode').style.display = "inline-block";
                            }} else {{
                                status.innerText = "⛔ WAJAH TIDAK COCOK! Jarak: " + match.distance.toFixed(2);
                            }}
                        }} catch (err) {{
                            status.innerText = "Gagal memuat AI.";
                        }}
                    }}
                    setTimeout(runAI, 500);
                </script>
            </body>
            </html>
            """
            components.html(html_code, height=120, scrolling=False)
            
            st.write("---")
            ver_kode = st.text_input("Masukkan KODE VALIDASI (jika wajah cocok):")
            
            if ver_kode == "COCOK100":
                st.success("✅ Verifikasi Wajah Berhasil!")
                if st.button("Kirim Absensi Sekarang"):
                    waktu_sekarang = datetime.datetime.now(pytz.timezone('Asia/Makassar'))
                    data_baru = {
                        'NIP': emp_data['nip'],
                        'Nama': emp_data['name'],
                        'Tanggal': waktu_sekarang.strftime('%Y-%m-%d'),
                        'Jam': waktu_sekarang.strftime('%H:%M:%S'),
                        'Status': 'Hadir'
                    }
                    simpan_ke_csv(data_baru) # Simpan permanen ke file CSV
                    st.balloons()
                    st.success("Data Absensi berhasil disimpan ke Database!")
            elif ver_kode:
                st.error("Kode Salah!")
    else:
        st.warning("Admin belum mengunggah foto acuan biometrik Anda. Hubungi Admin.")

# ==========================================
# HALAMAN 2: PANEL ADMIN (DENGAN AUTENTIKASI)
# ==========================================
elif menu == "Panel Admin":
    st.title("🔐 Panel Admin Sekolah")
    
    # SISTEM LOGIN SEDERHANA
    password = st.text_input("Masukkan Password Admin:", type="password")
    
    if password == "admin123": # Ganti password ini sesuai keinginan
        st.success("Login Berhasil!")
        
        st.markdown("### 1. Upload Foto Acuan Wajah (Database Biometrik)")
        pilihan_guru = st.selectbox("Pilih Pegawai:", st.session_state.employees['name'].tolist())
        idx = st.session_state.employees.index[st.session_state.employees['name'] == pilihan_guru][0]
        
        foto_unggah = st.file_uploader("Upload Pas Foto Jelas", type=['jpg', 'jpeg', 'png'])
        if foto_unggah and st.button("Simpan Foto Acuan"):
            bytes_data = foto_unggah.getvalue()
            base64_str = base64.b64encode(bytes_data).decode('utf-8')
            st.session_state.employees.at[idx, 'photo_uploaded'] = True
            st.session_state.employees.at[idx, 'photo_base64'] = f"data:image/jpeg;base64,{base64_str}"
            st.success("Foto berhasil dikunci ke sistem!")

        st.write("---")
        st.markdown("### 2. Download Database Absensi")
        if os.path.exists(FILE_ABSENSI):
            df_absen = pd.read_csv(FILE_ABSENSI)
            st.dataframe(df_absen) # Tampilkan tabel di layar
            
            # Tombol Download Data
            csv = df_absen.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data Excel (CSV)",
                data=csv,
                file_name="Laporan_Absensi.csv",
                mime="text/csv",
            )
        else:
            st.info("Belum ada data absensi.")
            
    elif password != "":
        st.error("Password Salah!")