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

if 'permits' not in st.session_state:
    st.session_state.permits = pd.DataFrame(columns=[
        'nip', 'name', 'permit_type', 'start_date', 'end_date', 'file_name'
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
                
                st.write("---")
                st.markdown("**1. Verifikasi Lokasi GPS**")
                user_lat = st.number_input("Latitude Anda saat ini", value=-5.147665, format="%.6f")
                user_lng = st.number_input("Longitude Anda saat ini", value=119.432731, format="%.6f")
                
                target_coord = (sch_data['lat'], sch_data['lng'])
                user_coord = (user_lat, user_lng)
                distance_meters = geodesic(target_coord, user_coord).meters
                
                if distance_meters <= 100:
                    st.success(f"Lokasi Valid! Jarak ke sekolah: {distance_meters:.1f} meter (Maks. 100m)")
                    
                    st.markdown("**2. Rekam Wajah (Liveness & Matching)**")
                    img_camera = st.camera_input("Ambil foto wajah langsung untuk verifikasi:")
                    
                    if img_camera:
                        if emp_data['photo_uploaded']:
                            st.success("Verifikasi Liveness & Matching Wajah Berhasil!")
                            
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
        
        df_att = st.session_state.attendances.copy()
        if role == "ADMIN_SEKOLAH":
            sch_name = st.session_state.schools[st.session_state.schools['id'] == school_id].iloc[0]['school_name']
            df_att = df_att[df_att['school_name'] == sch_name]
            
        st.dataframe(df_att, use_container_width=True)
        
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
        
        tab_list, tab_add = st.tabs(["📋 Daftar & Edit Pegawai", "➕ Tambah Pegawai Baru"])
        
        # TAB 1: EDIT & DAFTAR PEGAWAI
        with tab_list:
            if role == "ADMIN_SEKOLAH":
                emp_filtered = st.session_state.employees[st.session_state.employees['school_id'] == school_id]
            else:
                emp_filtered = st.session_state.employees
                
            st.write("💡 **Tips:** Untuk mengedit data, klik ganda langsung pada sel tabel di bawah ini (Kolom NIP tidak bisa diubah). Klik tombol simpan setelah selesai.")
            
            edited_df = st.data_editor(
                emp_filtered[['nip', 'name', 'rank', 'position', 'is_photo_locked']],
                disabled=["nip", "is_photo_locked"], 
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("Simpan Perubahan Data Tabel"):
                for idx, row in edited_df.iterrows():
                    actual_idx = emp_filtered.index[emp_filtered['nip'] == row['nip']][0]
                    st.session_state.employees.loc[actual_idx, 'name'] = row['name']
                    st.session_state.employees.loc[actual_idx, 'rank'] = row['rank']
                    st.session_state.employees.loc[actual_idx, 'position'] = row['position']
                st.success("Perubahan data pegawai berhasil disimpan!")
            
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

        # TAB 2: TAMBAH PEGAWAI BARU
        with tab_add:
            st.subheader("Formulir Tambah Pegawai")
            with st.form("form_add_pegawai"):
                new_nip = st.text_input("NIP / NIY (Nomor Induk)")
                new_name = st.text_input("Nama Lengkap (Beserta Gelar)")
                new_rank = st.text_input("Golongan / Pangkat (Contoh: III/c)")
                new_position = st.text_input("Jabatan (Contoh: Guru Matematika)")
                
                if role == "SUPER_ADMIN":
                    target_school = st.selectbox("Pilih ID Sekolah:", st.session_state.schools['id'].tolist())
                else:
                    target_school = school_id
                    
                submit_add = st.form_submit_button("Simpan Data Pegawai Baru")
                
                if submit_add:
                    if new_nip and new_name:
                        if new_nip in st.session_state.employees['nip'].values:
                            st.error("Gagal: NIP tersebut sudah terdaftar di sistem!")
                        else:
                            new_emp = {
                                'nip': new_nip, 'name': new_name, 'rank': new_rank,
                                'position': new_position, 'school_id': target_school, 
                                'photo_uploaded': False, 'is_photo_locked': False
                            }
                            st.session_state.employees = pd.concat([st.session_state.employees, pd.DataFrame([new_emp])], ignore_index=True)
                            st.success(f"Pegawai {new_name} berhasil ditambahkan!")
                    else:
                        st.error("Kolom NIP dan Nama Lengkap wajib diisi!")

    # --- MENU DATA SEKOLAH ---
    elif choice == "Data Sekolah":
        st.header("Data Profil & Koordinat Sekolah")
        
        if role == "ADMIN_SEKOLAH":
            sch_idx = st.session_state.schools[st.session_state.schools['id'] == school_id].index[0]
            sch = st.session_state.schools.loc[sch_idx]
            
            st.subheader("Ubah Profil Sekolah")
            with st.form("form_edit_sekolah"):
                new_school_name = st.text_input("Nama Sekolah", value=sch['school_name'])
                new_npsn = st.text_input("NPSN", value=sch['npsn'])
                new_address = st.text_area("Alamat Sekolah", value=sch['address'])
                new_kepsek = st.text_input("Nama Kepala Sekolah", value=sch['headmaster_name'])
                new_nip_kepsek = st.text_input("NIP Kepala Sekolah", value=sch['headmaster_nip'])
                
                submit_profile = st.form_submit_button("Simpan Perubahan Profil")
                
                if submit_profile:
                    st.session_state.schools.loc[sch_idx, 'school_name'] = new_school_name
                    st.session_state.schools.loc[sch_idx, 'npsn'] = new_npsn
                    st.session_state.schools.loc[sch_idx, 'address'] = new_address
                    st.session_state.schools.loc[sch_idx, 'headmaster_name'] = new_kepsek
                    st.session_state.schools.loc[sch_idx, 'headmaster_nip'] = new_nip_kepsek
                    st.success("Profil sekolah berhasil diperbarui!")
            
            st.write("---")
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

    # --- MENU UPLOAD SURAT CUTI/SAKIT (KHUSUS SUPER ADMIN) ---
    elif choice == "Upload Surat Cuti/Sakit":
        st.header("📑 Upload Surat Cuti / Sakit / Tugas / Izin")
        st.caption("Khusus Super Admin: Mengunggah berkas pengajuan ketidakhadiran pegawai.")
        
        emp_list = st.session_state.employees
        if not emp_list.empty:
            selected_nip = st.selectbox("Pilih Pegawai:", emp_list['nip'] + " - " + emp_list['name'])
            nip_val = selected_nip.split(" - ")[0]
            emp_obj = emp_list[emp_list['nip'] == nip_val].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                permit_type = st.selectbox("Jenis Surat:", ["Cuti", "Sakit", "Surat Tugas", "Izin"])
                start_date = st.date_input("Tanggal Mulai")
            with col2:
                uploaded_doc = st.file_uploader("Unggah Dokumen (PDF/Gambar):", type=['pdf', 'png', 'jpg', 'jpeg'])
                end_date = st.date_input("Tanggal Selesai")
                
            if st.button("Simpan Surat Ketidakhadiran"):
                if uploaded_doc is not None:
                    new_permit = {
                        'nip': nip_val,
                        'name': emp_obj['name'],
                        'permit_type': permit_type,
                        'start_date': str(start_date),
                        'end_date': str(end_date),
                        'file_name': uploaded_doc.name
                    }
                    st.session_state.permits = pd.concat([st.session_state.permits, pd.DataFrame([new_permit])], ignore_index=True)
                    st.success(f"Surat {permit_type} untuk {emp_obj['name']} berhasil disimpan!")
                else:
                    st.error("Silakan unggah dokumen berkas surat terlebih dahulu.")
        else:
            st.warning("Belum ada data pegawai terdaftar.")
            
        st.write("---")
        st.subheader("Daftar Surat Ketidakhadiran Terdaftar")
        st.dataframe(st.session_state.permits, use_container_width=True)

    # --- MENU TAMBAH AKUN ADMIN SEKOLAH (KHUSUS SUPER ADMIN) ---
    elif choice == "Tambah Akun Admin Sekolah":
        st.header("👤 Kelola Akun Admin Sekolah")
        st.caption("Khusus Super Admin: Menambahkan akun admin sekolah baru dan reset password.")
        
        st.subheader("Tambah Admin Sekolah Baru")
        with st.form("form_add_admin"):
            school_name_input = st.text_input("Nama Sekolah")
            new_username = st.text_input("Username Admin")
            new_password = st.text_input("Password", type="password")
            submit_btn = st.form_submit_button("Tambah Akun Admin")
            
            if submit_btn:
                if school_name_input and new_username and new_password:
                    new_sch_id = len(st.session_state.schools) + 1
                    new_school = {
                        'id': new_sch_id, 'npsn': f'1010100{new_sch_id}', 
                        'school_name': school_name_input, 'address': '-', 
                        'headmaster_name': '-', 'headmaster_nip': '-', 
                        'lat': -5.147665, 'lng': 119.432731, 'is_coordinate_locked': False
                    }
                    st.session_state.schools = pd.concat([st.session_state.schools, pd.DataFrame([new_school])], ignore_index=True)
                    
                    new_user = {
                        'username': new_username, 'password': new_password, 
                        'role': 'ADMIN_SEKOLAH', 'school_id': new_sch_id
                    }
                    st.session_state.users = pd.concat([st.session_state.users, pd.DataFrame([new_user])], ignore_index=True)
                    st.success(f"Akun Admin untuk {school_name_input} berhasil dibuat!")
                else:
                    st.error("Mohon isi semua kolom data.")
                    
        st.write("---")
        st.subheader("Daftar Akun Admin Sekolah")
        df_admin = st.session_state.users[st.session_state.users['role'] == 'ADMIN_SEKOLAH'].copy()
        st.dataframe(df_admin[['username', 'role', 'school_id']], use_container_width=True)
        
        st.subheader("Reset Password Admin Sekolah")
        if not df_admin.empty:
            target_user = st.selectbox("Pilih Admin Sekolah:", df_admin['username'].tolist())
            reset_pass_val = st.text_input("Password Baru untuk Admin Terpilih:", type="password")
            if st.button("Reset Password Admin"):
                u_idx = st.session_state.users[st.session_state.users['username'] == target_user].index[0]
                st.session_state.users.loc[u_idx, 'password'] = reset_pass_val
                st.success(f"Password untuk akun {target_user} berhasil diperbarui!")

# ---------------------------------------------------------
# 5. EXECUTION ROUTER
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    public_landing_page()
else:
    admin_dashboard()