import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from css_style import load_css
import bcrypt

def login_form(role_label: str = "Admin"):
    # st.set_page_config(page_title="Login Admin Gait", page_icon="⛨", layout="wide")
    
    # Load CSS dari file terpisah
    st.markdown(load_css(), unsafe_allow_html=True)

    # Tombol kembali
    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    # Konten login
    st.markdown("<h2>Sistem Dashboard Pemeriksaan Gait</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    # st.markdown("<hr class='custom'>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Login - {role_label}")
    username = st.text_input("NIP", placeholder="Masukkan NIP anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")

    # st.markdown("<a class='forgot' href='#'>Lupa kata sandi?</a>", unsafe_allow_html=True)
    # st.markdown("<br>", unsafe_allow_html=True)

    submit = st.button("Login", use_container_width=True)

    st.markdown(
        "<p class='footer'>Dengan masuk, Anda menyetujui kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>",
        unsafe_allow_html=True,
    )

    return username, password, submit


# ======================= HALAMAN ADMIN =======================
class AdminPage:
    def __init__(self):
        self.admin_user = st.secrets["ADMIN_USERNAME"]
        self.admin_pass = st.secrets["ADMIN_PASSWORD"]
        # Koneksi MongoDB
        self.client = MongoClient(st.secrets["MONGO_URI"])
        self.db = self.client['GaitDB']
        self.collection = self.db['gait_data']
        
        # Inisialisasi session state untuk data pasien
        if 'pasien_list_initialized' not in st.session_state:
            st.session_state.pasien_list_initialized = False
            st.session_state.pasien_list = []

    # # ---------- Styling ----------
    # def _inject_css(self):
    #     st.markdown("""
    #     <style>
    #         body { background-color: #f9f9f9; }

    #         /* Sidebar */
    #         section[data-testid="stSidebar"] {
    #             background-color: #560000;
    #         }

    #         .sidebar-title {
    #             color: white;
    #             font-size: 18px;
    #             font-weight: bold;
    #             padding: 10px 20px;
    #         }

    #         .sidebar-subtitle {
    #             color: #ddd;
    #             font-size: 14px;
    #             padding-left: 20px;
    #             margin-bottom: 10px;
    #         }

    #         .filter-box {
    #             background-color: #fff;
    #             padding: 20px;
    #             border-radius: 10px;
    #             box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
    #             margin-bottom: 10px;
    #         }
    
    #         /* Mengubah warna teks di sidebar menjadi putih */
    #         section[data-testid="stSidebar"] div[class*="stRadio"] label {
    #             color: white !important;
    #         }
            
    #         section[data-testid="stSidebar"] div[class*="stRadio"] div[role="radiogroup"] {
    #             color: white !important;
    #         }
            
    #         /* Mengubah warna teks untuk semua elemen di sidebar */
    #         section[data-testid="stSidebar"] * {
    #             color: white !important;
    #         }
            
    #         /* Khusus untuk radio button yang dipilih */
    #         section[data-testid="stSidebar"] div[class*="stRadio"] div[data-testid="stMarkdownContainer"] p {
    #             color: white !important;
    #         }

    #         /* FIX: Button sidebar agar tulisan selalu terlihat */
    #         section[data-testid="stSidebar"] button {
    #             background-color: #6b0000 !important;
    #             color: #ffffff !important;
    #             border-radius: 8px;
    #             height: 42px;
    #             font-weight: 600;
    #             border: none;
    #         }
            
    #         /* Hover */
    #         section[data-testid="stSidebar"] button:hover {
    #             background-color: #8a0000 !important;
    #             color: #ffffff !important;
    #         }
            
    #         /* Tombol aktif (menu terpilih) */
    #         section[data-testid="stSidebar"] button[kind="primary"] {
    #             background-color: #ffffff !important;
    #             color: #560000 !important;
    #             border: 2px solid #560000 !important;
    #         }
    #         section[data-testid="stSidebar"] button * {
    #             color: inherit !important;
    #         }

    #         /* Main content area */
    #         .main .block-container {
    #             padding-top: 2rem;
    #             padding-left: 2rem;
    #             padding-right: 2rem;
    #         }

    #         /* Stats cards */
    #         .stats-card {
    #             background: #ffffff !important;
    #             color: #000000 !important;
    #             padding: 20px;
    #             border-radius: 10px;
    #             text-align: center;
    #             border: 1px solid #ddd;
    #             margin-bottom: 15px;
    #             box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    #         }
    #         .stats-number {
    #             font-size: 2rem;
    #             font-weight: bold;
    #             margin: 10px 0;
    #         }

    #         /* Panel styling */
    #         .panel {
    #             background-color: #fff;
    #             border-radius: 10px;
    #             padding: 20px;
    #             box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    #             margin-bottom: 20px;
    #         }

    #         /* Account card */
    #         .account-card {
    #             background-color: #fff;
    #             border-radius: 10px;
    #             padding: 20px;
    #             box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    #             margin-bottom: 20px;
    #             border-left: 4px solid #560000;
    #         }
    #     </style>
    #     """, unsafe_allow_html=True)

    def _authenticate_admin(self, username, password):
        """Autentikasi admin dari database dengan bcrypt"""
        try:
            client = MongoClient(st.secrets["MONGO_URI"])
            db = client['GaitDB']
            collection = db['users']
            
            # Cari user dengan role admin
            admin = collection.find_one({
                'user_id': username,
                'role': 'admin'
            })
            
            if admin:
                stored_password = admin.get('password')
                # Verifikasi password dengan bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return {
                        'user_id': admin.get('user_id'),
                        'nama_lengkap': admin.get('nama_lengkap'),
                        'role': admin.get('role')
                    }
            return None
            
        except Exception as e:
            # Log error tapi jangan tampilkan ke user agar tidak mengganggu
            print(f"Database authentication error: {e}")
            return None
    
    def _load_pasien_data(self):
        if not st.session_state.pasien_list_initialized:
            try:
                client = MongoClient(st.secrets["MONGO_URI"])
                db = client['GaitDB']
                collection = db['users']
                
                # Ambil semua data pasien (role = 'pasien')
                pasien_data = list(collection.find({'role': 'pasien'}))
                
                # Reset dan isi session state
                st.session_state.pasien_list = []
                for pasien in pasien_data:
                    st.session_state.pasien_list.append({
                        "User ID": pasien.get('user_id', ''),
                        "Nama Lengkap": pasien.get('nama_lengkap', ''),
                        "Tanggal Lahir": pasien.get('tanggal_lahir', ''),
                        "Jenis Kelamin": pasien.get('jenis_kelamin', ''),
                        "Role": pasien.get('role', ''),
                        "Tanggal Dibuat": pasien.get('tanggal_dibuat', '')
                    })
                
                st.session_state.pasien_list_initialized = True
                    
            except Exception as e:
                st.error(f"Error loading patient data: {e}")

    # ---------- Sidebar ----------
    def _sidebar(self):
        admin_data = st.session_state.get('admin_user_data', {})
        admin_name = admin_data.get('nama_lengkap', 'Admin')
        
        st.sidebar.markdown("<p class='sidebar-title'>Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
        st.sidebar.markdown("<p class='sidebar-subtitle'>Menu</p>", unsafe_allow_html=True)
    
        menu_list = ["Home", "Manajemen User", "Baseline Data Gait", "Riwayat Pemeriksaan Pasien", "Logout"]
    
        for menu in menu_list:
            if st.sidebar.button(menu, use_container_width=True, type="primary" 
                                 if st.session_state.menu_admin == menu 
                                 else "secondary"):
                st.session_state.menu_admin = menu
                st.rerun()
    
        return st.session_state.menu_admin

    # ---------- Kartu Admin ----------
    def _account_card(self):
        st.markdown("### Beranda Admin")
        st.info("Selamat datang di Sistem Dashboard Pemeriksaan Gait. Gunakan menu di sidebar untuk mengakses menu yang tersedia.")
        
        # Load data pasien
        self._load_pasien_data()
        
        # Hitung total pasien
        total_pasien = len(st.session_state.pasien_list)
        
        # Hitung total data normal dari collection gait_data
        total_data = self.collection.count_documents({})
        
        try:
            client = MongoClient(st.secrets["MONGO_URI"])
            db = client['GaitDB']
            collection = db['patient_examinations']
            total_exams = collection.count_documents({})
        except:
            total_exams = 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <div>Total Pasien</div>
                <div class="stats-number">{total_pasien}</div>
                <div>Terdaftar</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <div>Baseline Data Gait</div>
                <div class="stats-number">{total_data}</div>
                <div>Dataset</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stats-card">
                <div>Pemeriksaan</div>
                <div class="stats-number">{total_exams}</div>
                <div>Total</div>
            </div>
            """, unsafe_allow_html=True)

    # ---------- Data Pasien & Dokter ----------
    def _panel_data(self):
        # Load data pasien sebelum menampilkan
        self._load_pasien_data()
        
        st.markdown("### Manajemen Data Pengguna")
        
        # Tab untuk jenis user yang berbeda
        tabs = st.tabs(["📋 Semua Pengguna", "➕ Tambah Pengguna Baru"])

        # Data dari collection users yang difilter berdasarkan role
        all_users = self._get_all_users()
        pasien_data = [user for user in all_users if user.get('Role') == 'pasien']
        terapis_data = [user for user in all_users if user.get('Role') == 'dokter']
        admin_data = [user for user in all_users if user.get('Role') == 'admin']

        with tabs[0]:
            # st.subheader("Daftar Semua Pengguna")
            
            # Tampilkan statistik
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Pengguna", len(all_users))
            with col2:
                st.metric("Pasien", len(pasien_data))
            with col3:
                st.metric("Dokter", len(terapis_data))
            with col4:
                st.metric("Admin", len(admin_data))
            
            # Filter berdasarkan role
            filter_role = st.selectbox(
                "Filter berdasarkan Role:",
                ["Semua", "Pasien", "Dokter", "Admin"],
                key="filter_role"
            )
            
            # Filter data berdasarkan pilihan
            if filter_role == "Semua":
                filtered_data = all_users
            elif filter_role == "Pasien":
                filtered_data = pasien_data
            elif filter_role == "Dokter":
                filtered_data = terapis_data
            else:
                filtered_data = admin_data
            
            if filtered_data:
                # Buat dataframe dengan nomor urut
                df_users = pd.DataFrame(filtered_data)
                df_users.insert(0, 'No', range(1, len(df_users) + 1))
                
                # Tampilkan kolom yang sesuai
                display_columns = ['No', 'User ID', 'Nama Lengkap', 'Role', 'Jenis Kelamin', 'Tanggal Lahir', 'Tanggal Dibuat']
                df_display = df_users[display_columns]
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
            else:
                st.info("📝 Belum ada data pengguna terdaftar")

        with tabs[1]:
            # st.subheader("➕ Tambah User Baru")
            
            with st.form("tambah_user_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    role = st.selectbox("Jenis User", ["pasien", "dokter", "admin"])
                    user_id = st.text_input("User ID", placeholder="Masukkan NIK untuk pasien, NIP untuk dokter/admin")
                    nama_lengkap = st.text_input("Nama Lengkap")
                    password = st.text_input("Password", type="password")
                    
                with col2:
                    tanggal_lahir = st.date_input("Tanggal Lahir", min_value=datetime(1900, 1, 1), max_value=datetime.now(), value=datetime(1990, 1, 1))
                    jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
                
                submitted = st.form_submit_button("💾 Tambah User Baru")
                
                if submitted:
                    if not user_id or not nama_lengkap or not password:
                        st.error("Harap isi semua field yang wajib!")
                    else:
                        user_data = {
                            'user_id': user_id,
                            'nama_lengkap': nama_lengkap,
                            'password': password,
                            'role': role,
                            'tanggal_lahir': tanggal_lahir.strftime("%d-%m-%Y"),
                            'jenis_kelamin': jenis_kelamin,
                            'tanggal_dibuat': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        if self._add_new_user(user_data):
                            st.success(f"✅ User {nama_lengkap} berhasil ditambahkan sebagai {role}!")
                            st.balloons()
                            
                            # Reset form
                            st.rerun()

    def _get_all_users(self):
        """Mendapatkan semua data user dari collection users"""
        try:
            client = MongoClient(st.secrets["MONGO_URI"])
            db = client['GaitDB']
            collection = db['users']
            
            all_users = list(collection.find({}, {'password': 0}))
            
            data = []
            for user in all_users:
                user_data = {
                    "User ID": user.get('user_id', ''),
                    "Nama Lengkap": user.get('nama_lengkap', ''),
                    "Role": user.get('role', ''),
                    "Tanggal Lahir": user.get('tanggal_lahir', ''),
                    "Jenis Kelamin": user.get('jenis_kelamin', ''),
                    "Tanggal Dibuat": user.get('tanggal_dibuat', '')
                }
                
                data.append(user_data)
            
            return data
        except Exception as e:
            st.error(f"Error loading users data: {e}")
            return []

    def _add_new_user(self, user_data):
        """Menambahkan user baru ke collection users"""
        try:
            client = MongoClient(st.secrets["MONGO_URI"])
            db = client['GaitDB']
            collection = db['users']
            
            # Cek apakah user_id sudah ada
            existing_user = collection.find_one({'user_id': user_data['user_id']})
            if existing_user:
                st.error(f"User ID '{user_data['user_id']}' sudah terdaftar")
                return False
            
             # Hash password dengan bcrypt
            hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
            
            # Siapkan data untuk disimpan
            new_user = {
                'user_id': user_data['user_id'],
                'nama_lengkap': user_data['nama_lengkap'],
                'password': hashed_password.decode('utf-8'),  # Simpan sebagai string
                'role': user_data['role'],
                'tanggal_lahir': user_data['tanggal_lahir'],
                'jenis_kelamin': user_data['jenis_kelamin'],
                'tanggal_dibuat': user_data['tanggal_dibuat']
            }
            
            result = collection.insert_one(new_user)
            
            # Update session state
            st.session_state.pasien_list_initialized = False
            
            return result.inserted_id is not None
            
        except Exception as e:
            st.error(f"Error menambahkan user: {e}")
            return False
        

    # def _show_delete_user_interface(self):
    #     """Menampilkan interface untuk menghapus user"""
    #     try:
    #         client = MongoClient(st.secrets["MONGO_URI"])
    #         db = client['GaitDB']
    #         collection = db['users']
            
    #         # Ambil semua user untuk dropdown
    #         all_users = list(collection.find({}, {'user_id': 1, 'nama_lengkap': 1, 'role': 1}))
            
    #         if not all_users:
    #             st.warning("Tidak ada user yang dapat dihapus")
    #             return
            
    #         # Buat pilihan untuk dropdown
    #         user_options = {f"{user['user_id']} - {user['nama_lengkap']} ({user['role']})": user['user_id'] 
    #                        for user in all_users}
            
    #         selected_display = st.selectbox(
    #             "Pilih user yang akan dihapus:",
    #             list(user_options.keys()),
    #             key="delete_user_select"
    #         )
            
    #         selected_user_id = user_options[selected_display]
            
    #         if st.button("Konfirmasi Hapus", type="primary"):
    #             # Hapus user dari database
    #             result = collection.delete_one({'user_id': selected_user_id})
                
    #             if result.deleted_count > 0:
    #                 st.success(f"✅ User berhasil dihapus!")
    #                 st.session_state.pasien_list_initialized = False
    #                 st.rerun()
    #             else:
    #                 st.error("❌ Gagal menghapus user")
                    
    #     except Exception as e:
    #         st.error(f"Error: {e}")

    # ---------- Manajemen Data Normal GAIT ----------

    def _manage_normal_data(self):
        st.markdown("### Manajemen Baseline Data Gait")
        
        # Stats Overview
        total_data = self.collection.count_documents({})
        male_count = self.collection.count_documents({"Subject Parameters.Gender": "L"})
        female_count = self.collection.count_documents({"Subject Parameters.Gender": "P"})

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <div>Total Data Gait Normal</div>
                <div class="stats-number">{total_data}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <div>Data Pria</div>
                <div class="stats-number">{male_count}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stats-card">
                <div>Data Wanita</div>
                <div class="stats-number">{female_count}</div>
            </div>
            """, unsafe_allow_html=True)

        # col1, col2, col3 = st.columns(3)
        
        # with col1:
        #     st.metric("Total Data Normal", total_data)
        
        # with col2:
        #     male_count = self.collection.count_documents({"Subject Parameters.Gender": "L"})
        #     st.metric("Data Pria", male_count)
        
        # with col3:
        #     female_count = self.collection.count_documents({"Subject Parameters.Gender": "P"})
        #     st.metric("Data Wanita", female_count)
            
        # with col4:
        #     # Data dengan usia di bawah 30
        #     young_count = self.collection.count_documents({"Subject Parameters.Age": {"$lt": 30}})
        #     st.metric("Usia < 30", young_count)
        
        # st.markdown("---")
        
        # Tampilkan data dalam tabel
        st.subheader("Daftar Baseline Data Gait")
        
        # Ambil semua data dari MongoDB
        data = list(self.collection.find())
        
        if not data:
            st.warning("Data baseline gait tidak ditemukan.")
            return
        
        # Siapkan data untuk dataframe
        table_data = []
        for doc in data:
            subject_params = doc.get('Subject Parameters', {})
            table_data.append({
                '_id': str(doc['_id']),
                'Nama Subject': subject_params.get('Subject Name', 'N/A'),
                'Usia': subject_params.get('Age', 'N/A'),
                'Gender': subject_params.get('Gender', 'N/A'),
                'Tinggi (cm)': round(subject_params.get('Height (mm)', 0) / 10, 1) if subject_params.get('Height (mm)') else 'N/A',
                'Berat (kg)': subject_params.get('Bodymass (kg)', 'N/A'),
                'BMI': round(subject_params.get('BMI', 0), 2) if subject_params.get('BMI') else 'N/A',
                'Klasifikasi BMI': subject_params.get('BMI Classification', 'N/A'),
                'Tanggal Upload': doc.get('upload_date', 'N/A')
            })
        
        df = pd.DataFrame(table_data)
        
        # # Tampilkan dataframe tanpa kolom _id
        display_df = df.drop('_id', axis=1)
        st.dataframe(display_df, use_container_width=True)
        
        # Fitur Edit dan Delete
        st.markdown("---")
        st.subheader("Kelola Data")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Edit Data")
            
            # Buat pilihan untuk selectbox dengan format: "Nama (Usia, Gender)"
            edit_options = []
            for doc in data:
                subject_params = doc.get('Subject Parameters', {})
                name = subject_params.get('Subject Name', 'N/A')
                age = subject_params.get('Age', 'N/A')
                gender = subject_params.get('Gender', 'N/A')
                display_text = f"{name} ({age} tahun, {gender})"
                edit_options.append((str(doc['_id']), display_text))
            
            if edit_options:
                # Tambahkan opsi default di awal
                options_with_default = [("", "Pilih Data untuk Diedit")] + edit_options
                
                selected_option = st.selectbox(
                    "Pilih data untuk diedit:",
                    options=[opt[0] for opt in options_with_default],
                    format_func=lambda x: next((display for id, display in options_with_default if id == x), 'Pilih Data untuk Diedit')
                )
                
                # Hanya tampilkan form edit jika user memilih data (bukan opsi default)
                if selected_option and selected_option != "":
                    selected_doc = next((doc for doc in data if str(doc['_id']) == selected_option), None)
                    if selected_doc:
                        with st.form("edit_form"):
                            subject_params = selected_doc.get('Subject Parameters', {})
                            new_name = st.text_input("Nama Subjek", value=subject_params.get('Subject Name', ''))
                            new_age = st.number_input("Usia", min_value=0, max_value=120, value=subject_params.get('Age', 0))
                            new_gender = st.selectbox("Jenis Kelamin", ["L", "P"], index=0 if subject_params.get('Gender') == 'L' else 1)
                            new_height = st.number_input("Tinggi (mm)", min_value=0, value=subject_params.get('Height (mm)', 0))
                            new_weight = st.number_input("Berat (kg)", min_value=0.0, value=subject_params.get('Bodymass (kg)', 0.0))
                            
                            if st.form_submit_button("💾 Update Data"):
                                update_data = {
                                    "Subject Parameters.Subject Name": new_name,
                                    "Subject Parameters.Age": new_age,
                                    "Subject Parameters.Gender": new_gender,
                                    "Subject Parameters.Height (mm)": new_height,
                                    "Subject Parameters.Bodymass (kg)": new_weight
                                }
                                # Hitung ulang BMI
                                height_m = new_height / 1000
                                new_bmi = new_weight / (height_m ** 2) if height_m > 0 else 0
                                bmi_class = (
                                    "Kurus Berat" if new_bmi < 17.0 else
                                    "Kurus Ringan" if 17.0 <= new_bmi <= 18.4 else
                                    "Normal" if 18.5 <= new_bmi <= 25.0 else
                                    "Gemuk Ringan" if 25.1 <= new_bmi <= 27.0 else
                                    "Gemuk Berat"
                                )
                                update_data["Subject Parameters.BMI"] = round(new_bmi, 2)
                                update_data["Subject Parameters.BMI Classification"] = bmi_class
                                
                                self.collection.update_one({'_id': selected_doc['_id']}, {'$set': update_data})
                                st.success("✅ Data berhasil diupdate!")
                                st.rerun()
                else:
                    st.info("Pilih data diatas untuk mengedit")
            else:
                st.info("Tidak ada data yang dapat diedit")
        
        with col2:
            st.markdown("#### Hapus Data")
            
            # Buat pilihan untuk delete dengan format yang sama
            delete_options = []
            for doc in data:
                subject_params = doc.get('Subject Parameters', {})
                name = subject_params.get('Subject Name', 'N/A')
                age = subject_params.get('Age', 'N/A')
                gender = subject_params.get('Gender', 'N/A')
                display_text = f"{name} ({age} tahun, {gender})"
                delete_options.append((str(doc['_id']), display_text))
            
            if delete_options:
                # Tambahkan opsi default di awal
                delete_options_with_default = [("", "Pilih Data untuk Dihapus")] + delete_options
                
                selected_delete_option = st.selectbox(
                    "Pilih data untuk dihapus:",
                    options=[opt[0] for opt in delete_options_with_default],
                    key="delete_select",
                    format_func=lambda x: next((display for id, display in delete_options_with_default if id == x), 'Pilih Data untuk Dihapus')
                )
                
                # Hanya tampilkan konfirmasi penghapusan jika user memilih data (bukan opsi default)
                if selected_delete_option and selected_delete_option != "":
                    selected_doc = next((doc for doc in data if str(doc['_id']) == selected_delete_option), None)
                    if selected_doc:
                        subject_params = selected_doc.get('Subject Parameters', {})
                        st.warning(f"⚠️ Anda akan menghapus data: **{subject_params.get('Subject Name', 'N/A')}**")
                        st.write(f"- Usia: {subject_params.get('Age', 'N/A')}")
                        st.write(f"- Gender: {subject_params.get('Gender', 'N/A')}")
                        st.write(f"- Tinggi: {subject_params.get('Height (mm)', 'N/A')} mm")
                        st.write(f"- Berat: {subject_params.get('Bodymass (kg)', 'N/A')} kg")
                        st.write(f"- BMI: {subject_params.get('BMI', 'N/A')} ({subject_params.get('BMI Classification', 'N/A')})")
                        
                        # Konfirmasi penghapusan
                        col_confirm1, col_confirm2 = st.columns(2)
                        with col_confirm1:
                            if st.button("Hapus Permanen", type="secondary", use_container_width=True):
                                self.collection.delete_one({'_id': selected_doc['_id']})
                                st.success("✅ Data berhasil dihapus!")
                                st.rerun()
                        with col_confirm2:
                            if st.button("Batal", use_container_width=True):
                                st.info("Penghapusan dibatalkan")
                else:
                    st.info("Pilih data di atas untuk menghapus")
            else:
                st.info("Tidak ada data yang dapat dihapus")

    # ---------- Riwayat Pemeriksaan Pasien ----------
    def _patient_examination_history(self):
        st.markdown("### Riwayat Pemeriksaan Pasien")
        
        try:
            # Koneksi ke MongoDB
            client = MongoClient(st.secrets["MONGO_URI"])
            db = client['GaitDB']
            collection = db['patient_examinations']
            
            # Ambil semua data pemeriksaan
            examinations = list(collection.find().sort('upload_date', -1))
            
            if not examinations:
                st.info("Belum ada riwayat pemeriksaan pasien.")
                return
            
            # Stats Overview
            total_exams = len(examinations)
            # unique_patients = len(set(exam['patient_info'].get('nik', '') for exam in examinations if exam['patient_info'].get('nik')))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Pemeriksaan", total_exams)
            # with col2:
            #     st.metric("Total Pasien Unik", unique_patients)
            with col2:
                # Hitung pemeriksaan bulan ini
                current_month = datetime.now().strftime("%Y-%m")
                monthly_exams = len([exam for exam in examinations 
                                if exam.get('upload_date', '').startswith(current_month)])
                st.metric("Pemeriksaan Bulan Ini", monthly_exams)
            
            # Siapkan data untuk tabel
            table_data = []
            for exam in examinations:
                pasien_id = exam.get('pasien_id', 'N/A')
                nama_pasien = exam.get('nama_pasien', 'N/A')
                dokter_id = exam.get('dokter_id', 'N/A')
                dokter_nama = exam.get('dokter_nama', 'N/A')
                tanggal_pemeriksaan = exam.get('tanggal_pemeriksaan', 'N/A')
                upload_date = exam.get('upload_date', 'N/A')
                
                # Data antropometri (jika ada)
                tinggi_badan = exam.get('tinggi_badan', 'N/A')
                berat_badan = exam.get('berat_badan', 'N/A')
                bmi = exam.get('bmi', 'N/A')
                bmi_class = exam.get('bmi_classification', 'N/A')
                
                # Info file (jika ada)
                file_info = exam.get('file_info', {})
                file_name = file_info.get('file_name', 'N/A') if isinstance(file_info, dict) else 'N/A'
                
                table_data.append({
                    'Tanggal Pemeriksaan': tanggal_pemeriksaan,
                    'NIK Pasien': pasien_id,
                    'Nama Pasien': nama_pasien,
                    'Tinggi (cm)': f"{tinggi_badan:.1f}" if isinstance(tinggi_badan, (int, float)) else tinggi_badan,
                    'Berat (kg)': f"{berat_badan:.1f}" if isinstance(berat_badan, (int, float)) else berat_badan,
                    'Klasifikasi BMI': bmi_class,
                    'Dokter': dokter_nama,
                    'File Name': file_name,
                    'Tanggal Upload': upload_date
                })
            
            df = pd.DataFrame(table_data)
            
            # Filter options
            st.markdown("### Filter Data")
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_nik = st.text_input("Filter berdasarkan NIK Pasien:")
            with col2:
                filter_nama = st.text_input("Filter berdasarkan Nama Pasien:")
            with col3:
                filter_dokter = st.text_input("Filter berdasarkan Nama Dokter:")
            
            # Apply filters
            filtered_df = df.copy()
            if filter_nik:
                filtered_df = filtered_df[filtered_df['NIK Pasien'].str.contains(filter_nik, case=False, na=False)]
            if filter_nama:
                filtered_df = filtered_df[filtered_df['Nama Pasien'].str.contains(filter_nama, case=False, na=False)]
            if filter_dokter:
                filtered_df = filtered_df[filtered_df['Dokter'].astype(str).str.contains(filter_dokter, case=False, na=False)]
            
            # Tampilkan tabel
            if not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True)
            
                # Tampilkan jumlah data
                st.markdown(f"**Menampilkan {len(filtered_df)} dari {len(df)} data pemeriksaan**")
                
            # Tombol download
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download Riwayat sebagai CSV",
                    data=csv,
                    file_name=f"riwayat_pemeriksaan_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv")
            else:
                st.info("Tidak ada data yang sesuai dengan filter.")
            
        except Exception as e:
            st.error(f"Error mengambil data riwayat pemeriksaan: {e}")

    # ---------- Halaman Utama ----------
    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)
        # self._inject_css()
    
        if "menu_admin" not in st.session_state:
            st.session_state.menu_admin = "Home"
    
        if 'admin_logged_in' not in st.session_state:
            st.session_state.admin_logged_in = False


        # Login Page
        if not st.session_state.admin_logged_in:
            username, password, submit = login_form("Admin")
            if submit:
                admin_data = self._authenticate_admin(username, password)
                if admin_data:
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_user_data = admin_data
                    st.rerun()
                # Fallback ke super admin dari secrets  
                elif username == self.admin_user and password == self.admin_pass:
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_user_data = {'user_id': self.admin_user,
                                                        'nama_lengkap': 'Super Admin',
                                                        'role': 'admin'}
                    st.rerun()
                else:
                    st.error("Username atau password salah!")
            return

        # Setelah login
        menu = self._sidebar()
        if menu == "Home":
            self._account_card()
            # st.success("🎉 Selamat datang di Dashboard Admin GAIT Clinic!")
            # st.info("Gunakan menu di sidebar untuk mengelola data pengguna dan data normal GAIT.")
            
        elif menu == "Manajemen User":
            self._panel_data()
            
        elif menu == "Baseline Data Gait":
            self._manage_normal_data()
            
        elif menu == "Riwayat Pemeriksaan Pasien":
            self._patient_examination_history()
            
        elif menu == "Logout":
            st.session_state.admin_logged_in = False
            st.session_state.pasien_list_initialized = False  # Reset flag saat logout
            if 'admin_user_data' in st.session_state:
                del st.session_state.admin_user_data
            st.rerun()
