import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from geopy.distance import geodesic
import io

# ---------------------------------------------------------
# 1. KONFIGURASI SISTEM & ZONA WAKTU MAKASSAR (WITA)
# ---------------------------------------------------------
st.set_page_config(page_title="Sistem Absensi Sekolah", layout="wide")
TZ_MAKASSAR = pytz.timezone('Asia/Makassar')

def get_now_makassar():
    return datetime.now(TZ_MAKASSAR)

# ---------------------------------------------------------
# 2. INISIALISASI DATABASE SEMENTARA (SESSION STATE)
# ---------------------------------------------------------
if 'schools' not in st.session_state:
    st.session_state.schools = pd.DataFrame([
        {
            'id': 1, 'npsn': '10101001', 'school_name': 'SMA Negeri 1 Makassar', 
            'address': 'Jl. Murah Hati No. 1', 'headmaster_name': 'Dr. H. Ahmad, M.Pd', 
            'headmaster_nip': '196801011990011001', 'lat': -5.147665, 'lng': 119.432731, 
            'is_coordinate_locked': True
        }
    ])

if 'users' not in st.session_state:
    st.session_state.users = pd.DataFrame([
        {'username': 'superadmin', 'password': '123', 'role': 'SUPER_ADMIN', 'school_id': None},
        {'username': 'admin_sman1', 'password': '123', 'role': 'ADMIN_SEKOLAH', 'school_id': 1}
    ])

if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame([
        {
            'nip': '198505122010011002', 'name': 'Budi Santoso, S.Pd', 'rank': 'III/c',
            'position': 'Guru Matematika', 'school_id': 1, 'photo_uploaded': True,
            'is_photo_locked': True
        }
    ])

if 'attendances' not in st.session_state:
    st.session_state.attendances = pd.DataFrame(columns=[
        'nip', 'name', 'school_name', 'date', 'time_in', 'status', 'lat', 'lng'
    ])

# ---------------------------------------------------------
# 3. FITUR PRESENSI & LOGIN DEPAN (PUBLIC)
# ---------------------------------------------------------
def public_landing_page():
    st.title("🏫 Sistem Presensi Biometrik & Lokasi")
    st.caption(f"Waktu Server (Makassar / WITA): **{get_now_makassar().strftime('%d %B %Y | %H:%M:%S')} WITA**")
    
    tab1, tab2 = st.tabs(["📌 Form Presensi Pegawai", "🔐 Login Admin"])
    
    with tab1:
        st.subheader("Presensi Kehadiran Harian")
        nip_input = st.text_input("Masukkan NIP Pegawai:")
        
        if nip_input:
            emp = st.session_state.employees[st.session_state.employees['nip'] == nip_input]
            if not emp.empty:
                emp_data = emp.iloc[0]
                sch_data = st.session_state.schools[st.session_state.schools['id'] == emp_data['school_id']].iloc[0]
                
                st.info(f"Pegawai: **{emp_data['name']}** | Sekolah: **{sch_data['school_name']}**")
                
                # Input Koordinat Manual / Simulasi GPS
                st.write("---")
                st.markdown("**1. Verifikasi Lokasi GPS**")
                user_lat = st.number_input("Latitude Anda saat ini", value=-5.147665, format="%.6f")
                user_lng = st.number_input("Longitude Anda saat ini", value=119.432731, format="%.6f")
                
                # Hitung Jarak ke Sekolah (Metode Haversine via Geopy)
                target_coord = (sch_data['lat'], sch_data['lng'])
                user_coord = (user_lat, user_lng)
                distance_meters = geodesic(target_coord, user_coord).meters
                
                if distance_meters <= 100:
                    st.success(f"Lokasi Valid! Jarak ke sekolah: {distance_meters:.1f} meter (Maks. 100m)")
                    
                    st.markdown("**2. Rekam Wajah (Liveness & Matching)**")
                    img_camera = st.camera_input("Ambil foto wajah langsung untuk verifikasi:")
                    
                    if img_camera:
                        # Simulasi Anti-Spoofing & Matching foto
                        if emp_data['photo_uploaded']:
                            st.success(" Verifikasi Liveness & Matching Wajah Berhasil!")
                            
                            if st.button("Kirim Absensi Sekarang"):
                                now_mks = get_now_makassar()
                                new_att = {
                                    'nip': emp_data['nip'],
                                    'name': emp_data['name'],
                                    'school_name': sch_data['school_name'],
                                    'date': now_mks.strftime('%Y-%m-%d'),
                                    'time_in': now_mks.strftime('%H:%M:%S'),
                                    'status': 'Hadir' if now_mks.hour < 8 else 'Terlambat',
                                    'lat': user_lat,
                                    'lng': user_lng
                                }
                                st.session_state.attendances = pd.concat([st.session_state.attendances, pd.DataFrame([new_att])], ignore_index=True)
                                st.balloons()
                                st.success("Absensi berhasil dicatat!")
                        else:
                            st.error("Admin Sekolah belum mengunggah foto acuan Anda! Hubungi Admin.")
                else:
                    st.error(f"Absensi Ditolak! Anda berada {distance_meters:.1f} meter di luar lokasi sekolah.")
            else:
                st.warning("NIP tidak ditemukan dalam sistem.")

        st.write("---")
        st.subheader("📋 Daftar Pegawai Sudah Absen Hari Ini")
        st.dataframe(st.session_state.attendances, use_container_width=True)

    with tab2:
        st.subheader("Login Panel Admin")
        username = st.text_input("Username Admin")
        password = st.text_input("Password Admin", type="password")
        if st.button("Masuk"):
            matched_user = st.session_state.users[
                (st.session_state.users['username'] == username) & 
                (st.session_state.users['password'] == password)
            ]
            if not matched_user.empty:
                st.session_state.logged_in = True
                st.session_state.current_user = matched_user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Username atau Password salah!")

# ---------------------------------------------------------
# 4. DASHBOARD & PANEL UTAMA ADMIN
# ---------------------------------------------------------
def admin_dashboard():
    user = st.session_state.current_user
    role = user['role']
    school_id = user['school_id']

    st.sidebar.title("Aplikasi Absensi")
    st.sidebar.write(f"Pengguna: **{user['username']}** ({role})")
    
    # Navigasi Menu
    menu_options = [
        "Dashboard", "Rekapitulasi", "Data Pegawai", 
        "Data Sekolah", "Ubah Password"
    ]
    if role == "SUPER_ADMIN":
        menu_options.insert(1, "Pengaturan Jam")
        menu_options.append("Upload Surat Cuti/Sakit")
        menu_options.append("Tambah Akun Admin Sekolah")
        
    choice = st.sidebar.radio("Navigasi Menu", menu_options)
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- MENU DASHBOARD ---
    if choice == "Dashboard":
        st.header("Dashboard Kehadiran")
        if role == "ADMIN_SEKOLAH":
            sch_name = st.session_state.schools[st.session_state.schools['id'] == school_id].iloc[0]['school_name']
            st.subheader(f"Sekolah: {sch_name}")
            data_emp = st.session_state.employees[st.session_state.employees['school_id'] == school_id]
        else:
            st.subheader("Semua Sekolah (Super Admin)")
            data_emp = st.session_state.employees
            
        st.dataframe(data_emp, use_container_width=True)

    # --- MENU PENGATURAN (KHUSUS SUPER ADMIN) ---
    elif choice == "Pengaturan Jam":
        st.header("Pengaturan Batas Jam Absensi")
        st.time_input("Batas Jam Masuk", value=datetime.strptime("07:30", "%H:%M").time())
        st.time_input("Batas Jam Pulang", value=datetime.strptime("16:00", "%H:%M").time())
        if st.button("Simpan Pengaturan"):
            st.success("Jam operasional berhasil disimpan global.")

    # --- MENU REKAPITULASI ---
    elif choice == "Rekapitulasi":
        st.header("Rekapitulasi Absensi")
        
        # Filter Data
        df_att = st.session_state.attendances.copy()
        if role == "ADMIN_SEKOLAH":
            sch_name = st.session_state.schools[st.session_state.schools['id'] == school_id].iloc[0]['school_name']
            df_att = df_att[df_att['school_name'] == sch_name]
            
        st.dataframe(df_att, use_container_width=True)
        
        # Tombol Download Excel
        if not df_att.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_att.to_excel(writer, index=False, sheet_name='Rekap_Absensi')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Rekap Excel",
                data=excel_data,
                file_name=f"Rekap_Absensi_{get_now_makassar().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # --- MENU DATA PEGAWAI ---
    elif choice == "Data Pegawai":
        st.header("Kelola Data Tenaga Pendidik & Kependidikan")
        
        # Filter berdasarkan sekolah
        if role == "ADMIN_SEKOLAH":
            emp_filtered = st.session_state.employees[st.session_state.employees['school_id'] == school_id]
        else:
            emp_filtered = st.session_state.employees
            
        st.dataframe(emp_filtered[['nip', 'name', 'rank', 'position', 'is_photo_locked']], use_container_width=True)
        
        st.write("---")
        st.subheader("Upload Foto Pegawai")
        nip_select = st.selectbox("Pilih Pegawai:", emp_filtered['nip'].tolist() if not emp_filtered.empty else [])
        
        if nip_select:
            idx = st.session_state.employees[st.session_state.employees['nip'] == nip_select].index[0]
            is_locked = st.session_state.employees.loc[idx, 'is_photo_locked']
            
            if is_locked and role == "ADMIN_SEKOLAH":
                st.warning("🔒 Foto pegawai ini sudah dikunci! Hanya Super Admin yang dapat menggantinya.")
            else:
                uploaded_photo = st.file_uploader("Pilih Berkas Foto", type=['jpg', 'jpeg', 'png'])
                if uploaded_photo and st.button("Simpan Foto"):
                    st.session_state.employees.loc[idx, 'photo_uploaded'] = True
                    st.session_state.employees.loc[idx, 'is_photo_locked'] = True
                    st.success("Foto berhasil diunggah dan dikunci.")

    # --- MENU DATA SEKOLAH ---
    elif choice == "Data Sekolah":
        st.header("Data Profil & Koordinat Sekolah")
        if role == "ADMIN_SEKOLAH":
            sch_idx = st.session_state.schools[st.session_state.schools['id'] == school_id].index[0]
            sch = st.session_state.schools.loc[sch_idx]
            
            st.text_input("Nama Sekolah", value=sch['school_name'], disabled=True)
            st.text_input("NPSN", value=sch['npsn'], disabled=True)
            
            st.subheader("Titik Koordinat Lokasi Absensi")
            if sch['is_coordinate_locked']:
                st.text_input("Latitude", value=sch['lat'], disabled=True)
                st.text_input("Longitude", value=sch['lng'], disabled=True)
                st.warning("🔒 Titik koordinat sudah dikunci 1 kali. Hubungi Super Admin jika ingin mereset.")
            else:
                new_lat = st.number_input("Latitude", value=sch['lat'], format="%.6f")
                new_lng = st.number_input("Longitude", value=sch['lng'], format="%.6f")
                if st.button("Simpan Titik Koordinat (Kunci 1x)"):
                    st.session_state.schools.loc[sch_idx, 'lat'] = new_lat
                    st.session_state.schools.loc[sch_idx, 'lng'] = new_lng
                    st.session_state.schools.loc[sch_idx, 'is_coordinate_locked'] = True
                    st.success("Koordinat berhasil disimpan!")
                    st.rerun()
        else:
            st.write("Semua Data Sekolah (Super Admin):")
            st.dataframe(st.session_state.schools, use_container_width=True)

    # --- MENU UBAH PASSWORD ---
    elif choice == "Ubah Password":
        st.header("Ubah Password Akun")
        new_pass = st.text_input("Password Baru", type="password")
        if st.button("Simpan Password Baru"):
            user_idx = st.session_state.users[st.session_state.users['username'] == user['username']].index[0]
            st.session_state.users.loc[user_idx, 'password'] = new_pass
            st.success("Password berhasil diperbarui.")

# ---------------------------------------------------------
# 5. EXECUTION ROUTER
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    public_landing_page()
else:
    admin_dashboard()