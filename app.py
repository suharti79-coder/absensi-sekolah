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
st.set_page_config(page_title="Sistem Absensi Sekolah Cabdis Wil IV", page_icon="🏫", layout="centered")

# --- KUSTOMISASI TAMPILAN (CUSTOM CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif !important;
    }

    /* SEMBUNYIKAN ATRIBUT STREAMLIT */
    header {visibility: hidden !important; height: 0px !important;} 
    [data-testid="stToolbar"] {visibility: hidden !important;} 
    [data-testid="stDecoration"] {visibility: hidden !important;} 
    footer {visibility: hidden !important;} 
    #MainMenu {visibility: hidden !important;}

    /* Geser konten utama ke atas menutupi ruang kosong header */
    .block-container { padding-top: 2rem !important; }

    /* Styling Kartu */
    .stForm, div[data-testid="stExpander"] {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
    }

    /* Styling Tombol */
    div.stButton > button {
        background-color: #2563EB !important; 
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #1D4ED8 !important; 
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
    }
    
    /* Styling Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

# --- KONFIGURASI DATABASE CSV ---
FILE_ABSENSI = "data_absensi.csv"
FILE_SEKOLAH = "data_sekolah.csv"
FILE_PEGAWAI = "data_pegawai.csv"
DIR_SURAT = "surat_izin"
if not os.path.exists(DIR_SURAT):
    os.makedirs(DIR_SURAT)

def muat_data(nama_file, data_default, kolom_default=None):
    if os.path.exists(nama_file):
        try:
            return pd.read_csv(nama_file)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(data_default) if data_default else pd.DataFrame(columns=kolom_default)
            df.to_csv(nama_file, index=False)
            return df
    else:
        df = pd.DataFrame(data_default) if data_default else pd.DataFrame(columns=kolom_default)
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
    st.session_state.employees = muat_data(FILE_PEGAWAI, [], kolom_default=['nip', 'name', 'school_name', 'photo_uploaded', 'photo_base64'])

if 'role' not in st.session_state:
    st.session_state.role = None

def logout():
    st.session_state.role = None

# ==========================================
# HALAMAN LOGIN UTAMA
# ==========================================
if st.session_state.role == "Pegawai":
    st.button("⬅️ Kembali ke Halaman Awal", on_click=logout)
    st.title("📍 Presensi GPS & Wajah")
    st.info("Selamat datang! Untuk merekam kehadiran Anda, silakan klik tombol di bawah ini.")
    
    # 1. Tombol Utama Pegawai
    if st.button("📸 Mulai Presensi Wajah & GPS", type="primary", use_container_width=True):
        st.session_state.role = "Pegawai"
        st.rerun()

    st.write("---")
    
    # 2. Menu Lipat Pengelola (Admin & Superadmin)
    st.caption("Akses khusus Pengelola Sistem:")
    col_admin, col_super = st.columns(2)
    
    with col_admin:
        with st.expander("🔑 Login Admin"):
            pwd = st.text_input("Password Admin:", type="password", key="pwd_admin_main")
            if st.button("Masuk Admin", use_container_width=True, key="btn_admin_main"):
                if pwd == "admin123":
                    st.session_state.role = "Admin"
                    st.rerun()
                else: 
                    st.error("Password Salah!")
                    
    with col_super:
        with st.expander("🛠️ Login Superadmin"):
            pwd_super = st.text_input("Password Superadmin:", type="password", key="pwd_super_main")
            if st.button("Masuk Superadmin", use_container_width=True, key="btn_super_main"):
                if pwd_super == "superadmin123":
                    st.session_state.role = "Superadmin"
                    st.rerun()
                else: 
                    st.error("Password Salah!")
                
    st.stop()

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("Informasi Akun")
st.sidebar.success(f"Akses: **{st.session_state.role}**")
st.sidebar.button("🚪 Keluar (Logout)", on_click=logout, key="btn_logout_utama")
st.sidebar.write("---")

waktu_sekarang = datetime.datetime.now(pytz.timezone('Asia/Makassar'))
st.sidebar.markdown("**Waktu Server (WITA):**")
st.sidebar.info(f"🕒 {waktu_sekarang.strftime('%H:%M:%S')} WITA\n\n📅 {waktu_sekarang.strftime('%d-%m-%Y')}")
st.sidebar.caption("Jam ini yang akan terekam di absensi, terlepas dari pengaturan jam di HP Anda.")
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
                                            
                                            const streamLitInput = window.parent.document.querySelector('div[data-testid="stTextInput"] input');
                                            if (streamLitInput) {{
                                                let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                                nativeInputValueSetter.call(streamLitInput, "COCOK100");
                                                streamLitInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                streamLitInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

                                                setTimeout(() => {{
                                                    const buttons = Array.from(window.parent.document.querySelectorAll('button'));
                                                    const submitBtn = buttons.find(btn => btn.innerText.includes('Kirim'));
                                                    if (submitBtn) {{
                                                        submitBtn.click();
                                                    }}
                                                }}, 1000);
                                            }}
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
                        st.markdown("""
                            <style>
                            div[data-testid="stTextInput"] {
                                display: none !important;
                                visibility: hidden !important;
                                height: 0px !important;
                                margin: 0px !important;
                                padding: 0px !important;
                            }
                            </style>
                        """, unsafe_allow_html=True)
                        if ver_kode == "COCOK100":
                            if st.button("Kirim Absensi"):
                                now = datetime.datetime.now(pytz.timezone('Asia/Makassar'))
                                data_absen_baru = pd.DataFrame([{
                                    'NIP': emp_data['nip'], 'Nama': emp_data['name'], 'Sekolah': sch_data['school_name'],
                                    'Tanggal': now.strftime('%Y-%m-%d'), 'Jam': now.strftime('%H:%M:%S'),
                                    'Jarak (m)': round(jarak_meter, 1), 'Status': 'Hadir'
                                }])
                                df_lama = pd.read_csv(FILE_ABSENSI) if os.path.exists(FILE_ABSENSI) else pd.DataFrame()
                                df_final = pd.concat([df_lama, data_absen_baru], ignore_index=True)
                                simpan_data(df_final, FILE_ABSENSI)
                                st.success("Absensi sukses tersimpan ke database!")
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
    col_judul, col_tombol = st.columns([3, 1])
    with col_judul:
        st.title("🔐 Dashboard Admin")
    with col_tombol:
        st.button("🚪 Logout", on_click=logout, use_container_width=True)
    
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
            simpan_data(st.session_state.employees, FILE_PEGAWAI)
            st.success("Foto dikunci dan disimpan secara permanen!")

    st.markdown("### 2. Laporan")
    if os.path.exists(FILE_ABSENSI):
        df = pd.read_csv(FILE_ABSENSI)
        st.dataframe(df)
        st.download_button("📥 Download Laporan", data=df.to_csv(index=False).encode('utf-8'), file_name="Absensi.csv")

# ==========================================
# HAK AKSES 3: SUPERADMIN
# ==========================================
elif st.session_state.role == "Superadmin":
    col_judul, col_tombol = st.columns([3, 1])
    with col_judul:
        st.title("🛠️ Dashboard Superadmin")
    with col_tombol:
        st.button("🚪 Logout", on_click=logout, use_container_width=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏛️ Kelola Sekolah", "👥 Kelola Pegawai", "📝 Input Izin/Dinas", "🚨 Database"])
    
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
            
            if st.form_submit_button("Simpan Sekolah Baru"):
                if new_sch_name:
                    new_sch_df = pd.DataFrame([{'school_name': new_sch_name, 'lat': new_lat, 'lng': new_lng, 'radius_m': new_rad}])
                    st.session_state.schools = pd.concat([st.session_state.schools, new_sch_df], ignore_index=True)
                    simpan_data(st.session_state.schools, FILE_SEKOLAH)
                    st.success(f"Sekolah {new_sch_name} berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("Nama sekolah tidak boleh kosong.")
                    
        st.write("---")
        st.markdown("### ✏️ Edit & Kelola Sekolah Aktif")
        st.info("💡 **Cara Edit:** Klik dua kali sel tabel untuk mengubah angka. **Cara Hapus:** Centang kotak di sisi kiri tabel, lalu tekan tempat sampah. **WAJIB** klik Simpan Perubahan di bawah.")
        
        edited_schools = st.data_editor(
            st.session_state.schools,
            num_rows="dynamic",
            use_container_width=True,
            key="school_editor"
        )
        
        if st.button("💾 Simpan Perubahan Tabel", type="primary"):
            st.session_state.schools = edited_schools
            simpan_data(st.session_state.schools, FILE_SEKOLAH)
            st.success("Perubahan data sekolah berhasil disimpan secara permanen!")
            st.rerun()

    with tab2:
        st.markdown("### 1. Tambah Pegawai (Manual)")
        with st.form("form_tambah_pegawai"):
            new_nip = st.text_input("NIP")
            new_name = st.text_input("Nama Lengkap")
            new_school = st.selectbox("Penempatan Sekolah", st.session_state.schools['school_name'].tolist())
            
            if st.form_submit_button("Tambahkan Manual"):
                if new_nip and new_name:
                    new_emp = pd.DataFrame([{
                        'nip': new_nip, 'name': new_name, 'school_name': new_school, 
                        'photo_uploaded': False, 'photo_base64': ''
                    }])
                    st.session_state.employees = pd.concat([st.session_state.employees, new_emp], ignore_index=True)
                    simpan_data(st.session_state.employees, FILE_PEGAWAI)
                    st.success(f"Pegawai ditambahkan ke {new_school}!")
        
        st.write("---")
        st.markdown("### 2. Tambah Pegawai (Upload Excel/CSV Massal)")
        
        template_df = pd.DataFrame({
            'nip': ['198001012005011001', '198203042008012003'],
            'name': ['Ahmad Guru', 'Siti Pengajar'],
            'school_name': ['Sekolah Default', 'Sekolah Default']
        })
        csv_template = template_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 1. Download Template CSV", data=csv_template, file_name="Template_Data_Pegawai.csv", mime="text/csv")
        
        file_upload = st.file_uploader("2. Upload File Template yang sudah diisi", type=['csv'])
        if file_upload is not None:
            if st.button("Proses Upload"):
                try:
                    df_upload = pd.read_csv(file_upload)
                    if all(col in df_upload.columns for col in ['nip', 'name', 'school_name']):
                        df_upload['photo_uploaded'] = False
                        df_upload['photo_base64'] = ''
                        df_upload['nip'] = df_upload['nip'].astype(str)
                        
                        st.session_state.employees = pd.concat([st.session_state.employees, df_upload], ignore_index=True)
                        st.session_state.employees.drop_duplicates(subset=['nip'], keep='last', inplace=True)
                        simpan_data(st.session_state.employees, FILE_PEGAWAI)
                        
                        st.success(f"Berhasil mengunggah {len(df_upload)} data pegawai!")
                        st.rerun()
                    else:
                        st.error("Format kolom salah! Pastikan file memiliki kolom: nip, name, school_name.")
                except Exception as e:
                    st.error(f"Gagal membaca file: {e}")

        st.write("---")
        st.markdown("### Daftar Pegawai Aktif")
        if not st.session_state.employees.empty:
            st.dataframe(st.session_state.employees[['nip', 'name', 'school_name', 'photo_uploaded']])

    with tab3:
        st.markdown("### 📝 Input Keterangan Absensi (Manual)")
        
        if st.session_state.employees.empty:
            st.warning("Belum ada data pegawai.")
        else:
            with st.form("form_izin"):
                pilihan_pegawai = st.selectbox("Pilih Pegawai:", st.session_state.employees['name'].tolist())
                jenis_absen = st.selectbox("Status Kehadiran:", ["Sakit", "Izin", "Dinas Luar"])
                tanggal_absen = st.date_input("Tanggal Keterangan")
                file_surat = st.file_uploader("Upload Bukti Surat (PDF/JPG/PNG)", type=['pdf', 'jpg', 'jpeg', 'png'])
                
                if st.form_submit_button("Simpan Data Absensi"):
                    if file_surat is not None:
                        emp_data = st.session_state.employees[st.session_state.employees['name'] == pilihan_pegawai].iloc[0]
                        file_ext = file_surat.name.split('.')[-1]
                        file_name = f"{emp_data['nip']}_{jenis_absen}_{tanggal_absen.strftime('%Y%m%d')}.{file_ext}"
                        file_path = os.path.join(DIR_SURAT, file_name)
                        
                        with open(file_path, "wb") as f:
                            f.write(file_surat.getbuffer())
                        
                        data_absen_baru = pd.DataFrame([{
                            'NIP': emp_data['nip'], 
                            'Nama': emp_data['name'], 
                            'Sekolah': emp_data['school_name'],
                            'Tanggal': tanggal_absen.strftime('%Y-%m-%d'), 
                            'Jam': '-',
                            'Jarak (m)': 'Dilampirkan Surat', 
                            'Status': jenis_absen
                        }])
                        
                        df_lama = pd.read_csv(FILE_ABSENSI) if os.path.exists(FILE_ABSENSI) else pd.DataFrame()
                        df_final = pd.concat([df_lama, data_absen_baru], ignore_index=True)
                        simpan_data(df_final, FILE_ABSENSI)
                        
                        st.success(f"Berhasil! Absensi {jenis_absen} untuk {pilihan_pegawai} telah tercatat dan surat telah disimpan.")
                    else:
                        st.error("Harap unggah file bukti surat terlebih dahulu sebelum menyimpan.")
                        
    with tab4:
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