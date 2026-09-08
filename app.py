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
st.set_page_config(page_title="Sistem Absensi Terpadu", page_icon="🏫", layout="centered")

# --- KONFIGURASI DATABASE CSV ---
FILE_ABSENSI = "data_absensi.csv"
FILE_SEKOLAH = "data_sekolah.csv"
FILE_PEGAWAI = "data_pegawai.csv"

def muat_data(nama_file, data_default):
    if os.path.exists(nama_file):
        return pd.read_csv(nama_file)
    else:
        df = pd.DataFrame(data_default)
        df.to_csv(nama_file, index=False)
        return df

def simpan_data(df, nama_file):
    df.to_csv(nama_file, index=False)

# --- INISIALISASI DATABASE ---
if 'schools' not in st.session_state:
    st.session_state.schools = muat_data(FILE_SEKOLAH, [
        {'school_name': 'Sekolah Default', 'lat': -5.147665, 'lng': 119.432731, 'radius_m': 100}
    ])

if 'employees' not in st.session_state:
    st.session_state.employees = muat_data(FILE_PEGAWAI, [])

if 'role' not in st.session_state:
    st.session_state.role = None

def logout():
    st.session_state.role = None

# ==========================================
# HALAMAN LOGIN UTAMA
# ==========================================
if st.session_state.role is None:
    st.title("🚪 Portal Absensi Sekolah")
    pilihan_login = st.selectbox("Login Sebagai:", ["Pilih...", "Pegawai", "Admin", "Superadmin"])
    
    if pilihan_login == "Pegawai":
        if st.button("Masuk (Kamera Absensi)"):
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
# HAK AKSES 1: PEGAWAI
# ==========================================
if st.session_state.role == "Pegawai":
    st.title("📍 Presensi GPS & Wajah")
    
    if st.session_state.employees.empty:
        st.warning("Belum ada data pegawai. Hubungi Superadmin.")
    else:
        pegawai_pilihan = st.selectbox("Pilih Nama Anda:", st.session_state.employees['name'].tolist())
        emp_data = st.session_state.employees[st.session_state.employees['name'] == pegawai_pilihan].iloc[0]
        
        try:
            sch_data = st.session_state.schools[st.session_state.schools['school_name'] == emp_data['school_name']].iloc[0]
        except IndexError:
            st.error("Data sekolah untuk pegawai ini tidak ditemukan atau telah dihapus.")
            st.stop()
            
        st.info(f"🏫 Anda ditugaskan di: **{sch_data['school_name']}**")
        st.write("Klik tombol di bawah untuk mendeteksi lokasi Anda saat ini.")
        
        lokasi_user = streamlit_geolocation()
        
        if lokasi_user['latitude'] is not None and lokasi_user['longitude'] is not None:
            user_lat = lokasi_user['latitude']
            user_lng = lokasi_user['longitude']
            
            jarak_meter = geopy.distance.geodesic((user_lat, user_lng), (sch_data['lat'], sch_data['lng'])).meters
            
            if jarak_meter <= sch_data['radius_m']:
                st.success(f"✅ Lokasi Valid! Anda berada {jarak_meter:.0f} meter dari pusat sekolah.")
                st.markdown("### Rekam Wajah")
                
                # Cek tipe data karena format CSV kadang membaca boolean sebagai string
                is_uploaded = str(emp_data['photo_uploaded']).lower() == 'true'
                
                if is_uploaded and pd.notna(emp_data['photo_base64']):
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
                                # Baca absen lama, tambah baru, simpan
                                data_absen_baru = pd.DataFrame([{
                                    'NIP': emp_data['nip'], 'Nama': emp_data['name'], 'Sekolah': sch_data['school_name'],
                                    'Tanggal': now.strftime('%Y-%m-%d'), 'Jam': now.strftime('%H:%M:%S'),
                                    'Jarak (m)': round(jarak_meter, 1), 'Status': 'Hadir'
                                }])
                                df_lama = pd.read_csv(FILE_ABSENSI) if os.path.exists(FILE_ABSENSI) else pd.DataFrame()
                                df_final = pd.concat([df_lama, data_absen_baru], ignore_index=True)
                                simpan_data(df_final, FILE_ABSENSI)
                                st.success("Absensi sukses!")
                else:
                    st.warning("Admin belum mengunggah foto acuan Anda.")
            else:
                st.error(f"⛔ Akses Ditolak! Jarak Anda {jarak_meter:.0f} meter. Anda berada di luar radius {sch_data['radius_m']} meter.")
        else:
            st.warning("Menunggu akses GPS. Mohon izinkan lokasi di browser.")

# ==========================================
# HAK AKSES 2: ADMIN
# ==========================================
elif st.session_state.role == "Admin":
    st.title("🔐 Dashboard Admin")
    
    if st.session_state.employees.empty:
         st.warning("Belum ada data pegawai. Minta Superadmin menambah pegawai terlebih dahulu.")
    else:
        st.markdown("### 1. Upload Foto Acuan")
        pilihan_guru = st.selectbox("Pilih Pegawai:", st.session_state.employees['name'].tolist())
        idx = st.session_state.employees.index[st.session_state.employees['name'] == pilihan_guru][0]
        
        foto = st.file_uploader("Upload Pas Foto", type=['jpg', 'jpeg', 'png'])
        if foto and st.button("Simpan Foto"):
            base64_str = base64.b64encode(foto.getvalue()).decode('utf-8')
            st.session_state.employees.at[idx, 'photo_uploaded'] = True
            st.session_state.employees.at[idx, 'photo_base64'] = f"data:image/jpeg;base64,{base64_str}"
            simpan_data(st.session_state.employees, FILE_PEGAWAI) # Simpan permanen ke CSV
            st.success("Foto dikunci dan disimpan secara permanen!")

    st.markdown("### 2. Laporan")
    if os.path.exists(FILE_ABSENSI):
        df = pd.read_csv(FILE_ABSENSI)
        st.dataframe(df)
        st.download_button("📥 Download", data=df.to_csv(index=False).encode('utf-8'), file_name="Absensi.csv")

# ==========================================
# HAK AKSES 3: SUPERADMIN
# ==========================================
elif st.session_state.role == "Superadmin":
    st.title("🛠️ Dashboard Superadmin")
    
    # --- TAB MENU SUPERADMIN ---
    tab1, tab2, tab3 = st.tabs(["🏛️ Kelola Sekolah", "👥 Kelola Pegawai", "🚨 Database"])
    
    # --- TAB 1: KELOLA SEKOLAH ---
    with tab1:
        st.markdown("### Tambah Titik Sekolah Baru")
        st.info("Buka Google Maps, klik kanan pada lokasi sekolah, salin angka koordinatnya.")
        with st.form("form_sekolah"):
            new_sch_name = st.text_input("Nama Sekolah / Area Lokasi")
            col_lat, col_lng = st.columns(2)
            with col_lat:
                new_lat = st.number_input("Latitude (Cth: -5.147665)", format="%.6f")
            with col_lng:
                new_lng = st.number_input("Longitude (Cth: 119.432731)", format="%.6f")
            new_rad = st.number_input("Radius Akses (Meter)", min_value=10, value=100)
            
            if st.form_submit_button("Simpan Sekolah"):
                if new_sch_name:
                    new_sch_df = pd.DataFrame([{'school_name': new_sch_name, 'lat': new_lat, 'lng': new_lng, 'radius_m': new_rad}])
                    st.session_state.schools = pd.concat([st.session_state.schools, new_sch_df], ignore_index=True)
                    simpan_data(st.session_state.schools, FILE_SEKOLAH)
                    st.success(f"Sekolah {new_sch_name} berhasil ditambahkan!")
                else:
                    st.error("Nama sekolah tidak boleh kosong.")
                    
        st.markdown("### Daftar Sekolah Aktif")
        st.dataframe(st.session_state.schools)

    # --- TAB 2: KELOLA PEGAWAI ---
    with tab2:
        st.markdown("### Tambah Pegawai & Penempatan")
        with st.form("form_tambah_pegawai"):
            new_nip = st.text_input("NIP")
            new_name = st.text_input("Nama Lengkap")
            new_school = st.selectbox("Penempatan Sekolah", st.session_state.schools['school_name'].tolist())
            
            if st.form_submit_button("Tambahkan Pegawai"):
                if new_nip and new_name:
                    new_emp = pd.DataFrame([{
                        'nip': new_nip, 'name': new_name, 'school_name': new_school, 
                        'photo_uploaded': False, 'photo_base64': ''
                    }])
                    st.session_state.employees = pd.concat([st.session_state.employees, new_emp], ignore_index=True)
                    simpan_data(st.session_state.employees, FILE_PEGAWAI)
                    st.success(f"Pegawai ditambahkan ke {new_school}!")
                    
        st.markdown("### Daftar Pegawai Aktif")
        if not st.session_state.employees.empty:
            st.dataframe(st.session_state.employees[['nip', 'name', 'school_name', 'photo_uploaded']])

    # --- TAB 3: ZONA BERBAHAYA ---
    with tab3:
        st.markdown("### Reset Data Sistem")
        st.warning("Perhatian! Menghapus data di sini tidak dapat dikembalikan.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Kosongkan Data Absensi"):
                if os.path.exists(FILE_ABSENSI): os.remove(FILE_ABSENSI)
                st.success("Tabel absensi dibersihkan!")
        with col2:
            if st.button("🚨 Reset Semua Pegawai"):
                if os.path.exists(FILE_PEGAWAI): os.remove(FILE_PEGAWAI)
                st.session_state.employees = pd.DataFrame()
                st.success("Data pegawai telah di-reset.")