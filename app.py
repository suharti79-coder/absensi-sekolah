import streamlit as st
import pandas as pd
import datetime
import pytz
import base64
import os
import geopy.distance
from streamlit_geolocation import streamlit_geolocation
import streamlit.components.v1 as components

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Absensi GPS & Biometrik", page_icon="🏫", layout="centered")

FILE_ABSENSI = "data_absensi.csv"

def simpan_ke_csv(data_baru):
    df_baru = pd.DataFrame([data_baru])
    if os.path.exists(FILE_ABSENSI):
        df_lama = pd.read_csv(FILE_ABSENSI)
        df_final = pd.concat([df_lama, df_baru], ignore_index=True)
    else:
        df_final = df_baru
    df_final.to_csv(FILE_ABSENSI, index=False)

# --- DATABASE SEKOLAH ---
if 'schools' not in st.session_state:
    st.session_state.schools = pd.DataFrame([
        {'school_name': 'SD Negeri 1 Pusat', 'lat': -5.147665, 'lng': 119.432731, 'radius_m': 100},
        {'school_name': 'SMP Negeri 2 Cabang', 'lat': -5.132159, 'lng': 119.444654, 'radius_m': 150},
        # Tambahkan sekolah ke-3, ke-4, dan seterusnya di bawah ini:
        {'school_name': 'SMA Negeri 3', 'lat': -5.123456, 'lng': 119.555555, 'radius_m': 100},
        {'school_name': 'Kantor Dinas Pendidikan', 'lat': -5.111111, 'lng': 119.666666, 'radius_m': 50}
    ])

# --- DATABASE PEGAWAI ---
if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame([{
        'nip': '12345', 'name': 'Budi Guru', 'school_name': 'SD Negeri 1 Pusat', 
        'photo_uploaded': False, 'photo_base64': ''
    }])

if 'role' not in st.session_state:
    st.session_state.role = None

def logout():
    st.session_state.role = None

# ==========================================
# HALAMAN LOGIN UTAMA
# ==========================================
if st.session_state.role is None:
    st.title("🚪 Portal Absensi Geolocation")
    pilihan_login = st.selectbox("Login Sebagai:", ["Pilih...", "Pegawai", "Admin", "Superadmin"])
    
    if pilihan_login == "Pegawai":
        if st.button("Masuk sebagai Pegawai"):
            st.session_state.role = "Pegawai"
            st.rerun()
    elif pilihan_login == "Admin":
        pwd = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
            if pwd == "admin123":
                st.session_state.role = "Admin"
                st.rerun()
            else: st.error("Password Salah!")
    elif pilihan_login == "Superadmin":
        pwd_super = st.text_input("Password Superadmin:", type="password")
        if st.button("Login"):
            if pwd_super == "superadmin123":
                st.session_state.role = "Superadmin"
                st.rerun()
            else: st.error("Password Salah!")
    st.stop()

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("Informasi Akun")
st.sidebar.success(f"Akses: **{st.session_state.role}**")
st.sidebar.button("🚪 Keluar (Logout)", on_click=logout)
st.sidebar.write("---")

# ==========================================
# HAK AKSES 1: PEGAWAI (GPS & Kamera)
# ==========================================
if st.session_state.role == "Pegawai":
    st.title("📍 Presensi GPS & Wajah")
    
    if st.session_state.employees.empty:
        st.warning("Belum ada data pegawai.")
    else:
        pegawai_pilihan = st.selectbox("Pilih Nama Anda:", st.session_state.employees['name'].tolist())
        emp_data = st.session_state.employees[st.session_state.employees['name'] == pegawai_pilihan].iloc[0]
        
        # Ambil Data Sekolah Pegawai tsb
        sch_data = st.session_state.schools[st.session_state.schools['school_name'] == emp_data['school_name']].iloc[0]
        
        st.info(f"🏫 Anda ditugaskan di: **{sch_data['school_name']}**")
        st.write("Klik tombol di bawah untuk mendeteksi lokasi Anda saat ini.")
        
        # 1. Pengecekan GPS
        lokasi_user = streamlit_geolocation()
        
        if lokasi_user['latitude'] is not None and lokasi_user['longitude'] is not None:
            user_lat = lokasi_user['latitude']
            user_lng = lokasi_user['longitude']
            
            # Hitung Jarak
            jarak_meter = geopy.distance.geodesic(
                (user_lat, user_lng), 
                (sch_data['lat'], sch_data['lng'])
            ).meters
            
            if jarak_meter <= sch_data['radius_m']:
                st.success(f"✅ Lokasi Valid! Anda berada {jarak_meter:.0f} meter dari titik pusat sekolah.")
                
                # 2. Buka Kamera Jika GPS Valid
                st.markdown("### Rekam Wajah")
                if emp_data['photo_uploaded'] and emp_data['photo_base64'] != '':
                    img_camera = st.camera_input("Ambil Foto Wajah Anda")
                    if img_camera:
                        bytes_data = img_camera.getvalue()
                        cam_base64 = f"data:image/jpeg;base64,{base64.b64encode(bytes_data).decode('utf-8')}"
                        
                        html_code = f"""
                        <!DOCTYPE html>
                        <html>
                        <head><script src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/dist/face-api.js"></script></head>
                        <body style="text-align: center; font-family: sans-serif;">
                            <div id="status" style="color:#d9534f; font-weight:bold;">Memuat AI...</div>
                            <div id="kode" style="display:none; color:white; background:#5cb85c; padding:10px; border-radius:5px; font-weight:bold; font-size:20px;">KODE: COCOK100</div>
                            <img id="refImg" src="{emp_data['photo_base64']}" style="display:none;" />
                            <img id="camImg" src="{cam_base64}" style="display:none;" />
                            <script>
                                async function runAI() {{
                                    const status = document.getElementById('status');
                                    try {{
                                        const URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model';
                                        await faceapi.nets.ssdMobilenetv1.loadFromUri(URL);
                                        await faceapi.nets.faceLandmark68Net.loadFromUri(URL);
                                        await faceapi.nets.faceRecognitionNet.loadFromUri(URL);
                                        
                                        const ref = await faceapi.detectSingleFace(document.getElementById('refImg')).withFaceLandmarks().withFaceDescriptor();
                                        const cam = await faceapi.detectSingleFace(document.getElementById('camImg')).withFaceLandmarks().withFaceDescriptor();
                                        
                                        if(!ref || !cam) {{ status.innerText = "Wajah tidak terdeteksi jelas."; return; }}
                                        
                                        const match = new faceapi.FaceMatcher(ref).findBestMatch(cam.descriptor);
                                        if(match.distance <= 0.5) {{ 
                                            status.style.display = "none";
                                            document.getElementById('kode').style.display = "inline-block";
                                        }} else {{ status.innerText = "⛔ WAJAH TIDAK COCOK!"; }}
                                    }} catch(e) {{ status.innerText = "Gagal memuat AI."; }}
                                }}
                                setTimeout(runAI, 500);
                            </script>
                        </body>
                        </html>
                        """
                        components.html(html_code, height=80, scrolling=False)
                        
                        ver_kode = st.text_input("Ketik KODE di atas:")
                        if ver_kode == "COCOK100":
                            if st.button("Kirim Absensi"):
                                now = datetime.datetime.now(pytz.timezone('Asia/Makassar'))
                                simpan_ke_csv({
                                    'NIP': emp_data['nip'], 'Nama': emp_data['name'], 'Sekolah': sch_data['school_name'],
                                    'Tanggal': now.strftime('%Y-%m-%d'), 'Jam': now.strftime('%H:%M:%S'),
                                    'Jarak (m)': round(jarak_meter, 1), 'Status': 'Hadir'
                                })
                                st.success("Absensi sukses!")
                else:
                    st.warning("Admin belum mengunggah foto acuan Anda.")
            else:
                st.error(f"⛔ Akses Ditolak! Jarak Anda {jarak_meter:.0f} meter. Anda berada di luar radius {sch_data['radius_m']} meter dari sekolah.")
        else:
            st.warning("Menunggu akses GPS. Mohon izinkan lokasi di browser Anda.")

# ==========================================
# HAK AKSES 2: ADMIN (Foto & Laporan)
# ==========================================
elif st.session_state.role == "Admin":
    st.title("🔐 Dashboard Admin")
    st.markdown("### 1. Upload Foto Acuan")
    pilihan_guru = st.selectbox("Pilih Pegawai:", st.session_state.employees['name'].tolist())
    idx = st.session_state.employees.index[st.session_state.employees['name'] == pilihan_guru][0]
    
    foto = st.file_uploader("Upload Pas Foto", type=['jpg', 'jpeg', 'png'])
    if foto and st.button("Simpan Foto"):
        base64_str = base64.b64encode(foto.getvalue()).decode('utf-8')
        st.session_state.employees.at[idx, 'photo_uploaded'] = True
        st.session_state.employees.at[idx, 'photo_base64'] = f"data:image/jpeg;base64,{base64_str}"
        st.success("Foto dikunci!")

    st.markdown("### 2. Laporan")
    if os.path.exists(FILE_ABSENSI):
        df = pd.read_csv(FILE_ABSENSI)
        st.dataframe(df)
        st.download_button("📥 Download", data=df.to_csv(index=False).encode('utf-8'), file_name="Absensi.csv")

# ==========================================
# HAK AKSES 3: SUPERADMIN (Tambah Guru & Penempatan Sekolah)
# ==========================================
elif st.session_state.role == "Superadmin":
    st.title("🛠️ Dashboard Superadmin")
    st.markdown("### Tambah Pegawai & Penempatan")
    
    with st.form("form_tambah"):
        new_nip = st.text_input("NIP")
        new_name = st.text_input("Nama Lengkap")
        # Superadmin menempatkan guru di sekolah tertentu
        new_school = st.selectbox("Penempatan Sekolah", st.session_state.schools['school_name'].tolist())
        
        if st.form_submit_button("Tambahkan"):
            if new_nip and new_name:
                new_emp = pd.DataFrame([{
                    'nip': new_nip, 'name': new_name, 'school_name': new_school, 
                    'photo_uploaded': False, 'photo_base64': ''
                }])
                st.session_state.employees = pd.concat([st.session_state.employees, new_emp], ignore_index=True)
                st.success(f"Pegawai ditambahkan ke {new_school}!")
                
    st.dataframe(st.session_state.employees[['nip', 'name', 'school_name', 'photo_uploaded']])