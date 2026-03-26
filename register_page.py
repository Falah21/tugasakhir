# register_page.py
import streamlit as st
from datetime import date, datetime
from pymongo import MongoClient
from css_style import load_css
import bcrypt

# Optimasi koneksi MongoDB
def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )

class RegisterPage:
    def __init__(self):
        # Inisialisasi session state untuk register
        st.session_state.setdefault("show_register", False)
    
    def _save_registration_to_db(self, data):
        """Menyimpan data registrasi ke database MongoDB collection users"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['users']
            
            # Cek apakah user_id sudah ada
            existing_user = collection.find_one({"user_id": data["user_id"]})
            if existing_user:
                st.error("NIK sudah terdaftar. Silakan gunakan NIK lain.")
                return False
            
            # Simpan data ke database
            result = collection.insert_one(data)
            
            # Update session state untuk pasien
            if "pasien_auth" not in st.session_state:
                st.session_state["pasien_auth"] = {}
            if "pasien_list" not in st.session_state:
                st.session_state["pasien_list"] = []
            
            # st.session_state["pasien_auth"][data["user_id"]] = data["password"]
            st.session_state["pasien_list"].append({
                "User ID": data["user_id"],
                "Nama Lengkap": data["nama_lengkap"],
                "Tanggal Lahir": data["tanggal_lahir"],
                "Jenis Kelamin": data["jenis_kelamin"],
                "Role": "pasien",
                "Tanggal Dibuat": data["tanggal_dibuat"]
            })
            
            return True
            
        except Exception as e:
            st.error(f"Error menyimpan data ke database: {e}")
            return False
    
    def show(self):
        """Menampilkan halaman registrasi"""
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # Header
        st.markdown("<h2>Aplikasi GAIT Clinic</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Form Pendaftaran Pasien Baru</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Form registrasi
        with st.form("register_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                user_id = st.text_input("NIK", max_chars=20, key="reg_nik", 
                                      placeholder="Masukkan NIK anda")
                nama_lengkap = st.text_input("Nama Lengkap", key="reg_nama",
                                           placeholder="Masukkan nama lengkap")
                password = st.text_input("Password", type="password", key="reg_password",
                                       placeholder="Buat password")
                
            with col2:
                tanggal_lahir = st.date_input(
                    "Tanggal Lahir", 
                    min_value=date(1900, 1, 1), 
                    max_value=date.today(),
                    value=date(1990, 1, 1),
                    key="reg_ttl"
                )
                jenis_kelamin = st.selectbox(
                    "Jenis Kelamin", 
                    ["Laki-laki", "Perempuan"], 
                    key="reg_jk"
                )
            
            st.markdown("---")
            
            # Submit button
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                submitted = st.form_submit_button("Daftar Sekarang", use_container_width=True)
            
            if submitted:
                if user_id and nama_lengkap and password:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    registration_data = {
                        "user_id": user_id,
                        "nama_lengkap": nama_lengkap,
                        "password": hashed_password.decode('utf-8'),  # simpan hash
                        "role": "pasien",
                        "tanggal_lahir": tanggal_lahir.strftime("%d-%m-%Y"),
                        "jenis_kelamin": jenis_kelamin,
                        "tanggal_dibuat": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    if self._save_registration_to_db(registration_data):
                        st.success("Pendaftaran berhasil! Silakan login.")
                        st.balloons()
                        # Kembali ke halaman login setelah 2 detik
                        st.session_state.show_register = False
                        st.rerun()
                else:
                    st.warning("⚠ Mohon isi semua kolom wajib.")

        # Tombol kembali ke login
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Kembali ke Halaman Login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
        
        # Footer
        st.markdown("<p class='footer'>Dengan mendaftar, Anda menyetujui Kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>", 
                   unsafe_allow_html=True)
