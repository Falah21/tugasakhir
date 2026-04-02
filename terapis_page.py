import pandas as pd
from pymongo import MongoClient
import math
import matplotlib.pyplot as plt
from PIL import Image
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pymongo import MongoClient
import numpy as np
from pymongo.server_api import ServerApi
import io
from datetime import datetime
import json  # ⬅️ TAMBAH INI
import google.generativeai as genai
from css_style import load_css
import traceback
import bcrypt
from datetime import datetime

# 🧩 Konfigurasi halaman
st.set_page_config(page_title="Dashboard GAIT Terapis", layout="wide")
# st.set_page_config(page_title="Dashboard GAIT Terapis", layout="wide", initial_sidebar_state="expanded")

# ====== KONFIGURASI GEMINI AI ======
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    gemini_model = None
    st.warning("⚠️ API Key Gemini tidak ditemukan. Fitur AI akan dinonaktifkan.")

# ======================= LOGIN FORM =======================

def login_form(role_label: str = "Dokter"):
    # Load CSS dari file terpisah
    st.markdown(load_css(), unsafe_allow_html=True)

    # Tombol kembali
    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    # Konten login
    st.markdown("<h2>Aplikasi GAIT Clinic</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan GAIT</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Login - {role_label}")
    user_id = st.text_input("NIP", placeholder="Masukkan NIP anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")

    # st.markdown("<a class='forgot' href='#'>Lupa kata sandi?</a>", unsafe_allow_html=True)
    # st.markdown("<br>", unsafe_allow_html=True)

    submit = st.button("Login", use_container_width=True)

    st.markdown(
        "<p class='footer'>Dengan masuk, Anda menyetujui kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>",
        unsafe_allow_html=True,
    )

    return user_id, password, submit
# Optimasi koneksi MongoDB
def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )

# Kelas GaitAnalysisData untuk data normal
class GaitAnalysisDataNormal:
    def __init__(self, content, usia, jenis_kelamin):
        try:
            # Membaca file Excel ke dalam DataFrame pandas
            self.df = pd.read_excel(io.BytesIO(content), sheet_name=[0, 1])
            self.suin = self.df[0]  # Lembar pertama untuk data mentah
            self.normkin = self.df[1].iloc[:, :31]  # Lembar kedua untuk kinematika terstandarisasi
        except Exception as e:
            st.error(f"Error reading the Excel file: {e}")
            return

        # Memproses data
        self.cleaned_data = self.clean_data()
        self.normkin_processed = self.process_normkin()
        self.trial_info = self.extract_trial_info()
        self.subject_params = self.extract_subject_params(usia, jenis_kelamin)
        self.body_measurements = self.extract_body_measurements()
        self.norm_kinematics = self.extract_norm_kinematics()

    def clean_data(self):
        cleaned_data = self.suin.dropna(how='all')
        cleaned_data.reset_index(drop=True, inplace=True)
        return cleaned_data

    def process_normkin(self):
        column_namesX = [col for col in self.normkin.columns if col.endswith('X')]
        normkin = self.normkin.loc[:, column_namesX]
        normkin.insert(0, "Percentage of Gait Cycle", self.df[1].iloc[:, 0].tolist())
        return normkin

    def extract_trial_info(self):
        return {
            "Trial Information": {
                "Trial Name": self.cleaned_data.iloc[1, 2]
            }
        }

    def extract_subject_params(self, usia, jenis_kelamin):
        bmi = (self.cleaned_data.iloc[4, 2])/((self.cleaned_data.iloc[5, 2]/1000)**2)
        bmi_class = (
            "Kurus Berat" if bmi < 17.0 else
            "Kurus Ringan" if bmi < 18.5 else
            "Normal" if bmi < 25.1 else
            "Gemuk Ringan" if bmi < 27.1 else
            "Gemuk Berat"
        )
        return {
            "Subject Parameters": {
                "Subject Name": self.cleaned_data.iloc[3, 2],
                "Age": usia,
                "Gender": jenis_kelamin.upper(),
                "Bodymass (kg)": self.cleaned_data.iloc[4, 2],
                "Height (mm)": self.cleaned_data.iloc[5, 2],
                "BMI": bmi,
                "BMI Classification": bmi_class
            }
        }

    def extract_body_measurements(self):
        return {
            "Body Measurements": {
                "Leg Length (mm)": {
                    "Left": self.cleaned_data.iloc[12, 2],
                    "Right": self.cleaned_data.iloc[12, 3]
                },
                "Knee Width (mm)": {
                    "Left": self.cleaned_data.iloc[13, 2],
                    "Right": self.cleaned_data.iloc[13, 3]
                },
                "Ankle Width (mm)": {
                    "Left": self.cleaned_data.iloc[14, 2],
                    "Right": self.cleaned_data.iloc[14, 3]
                }
            }
        }

    def extract_norm_kinematics(self):
        required_cols = [
        "Percentage of Gait Cycle", "LPelvisAngles_X", "RPelvisAngles_X",
        "LHipAngles_X", "RHipAngles_X", "LKneeAngles_X", "RKneeAngles_X",
        "LAnkleAngles_X", "RAnkleAngles_X", "LFootProgressAngles_X", "RFootProgressAngles_X"
    ]

        missing_cols = [col for col in required_cols if col not in self.normkin_processed.columns]
    
        if missing_cols:
            st.error(f"Incomplete kinematic data. Missing columns: {', '.join(missing_cols)}")
            st.stop()
        else:
            return {
                "Norm Kinematics": {
                    "Percentage of Gait Cycle": self.normkin_processed['Percentage of Gait Cycle'].tolist(),
                    "LPelvisAngles_X": self.normkin_processed["LPelvisAngles_X"].tolist(),
                    "RPelvisAngles_X": self.normkin_processed["RPelvisAngles_X"].tolist(),
                    "LHipAngles_X": self.normkin_processed["LHipAngles_X"].tolist(),
                    "RHipAngles_X": self.normkin_processed["RHipAngles_X"].tolist(),
                    "LKneeAngles_X": self.normkin_processed["LKneeAngles_X"].tolist(),
                    "RKneeAngles_X": self.normkin_processed["RKneeAngles_X"].tolist(),
                    "LAnkleAngles_X": self.normkin_processed["LAnkleAngles_X"].tolist(),
                    "RAnkleAngles_X": self.normkin_processed["RAnkleAngles_X"].tolist(),
                    "LFootProgressAngles_X": self.normkin_processed["LFootProgressAngles_X"].tolist(),
                    "RFootProgressAngles_X": self.normkin_processed["RFootProgressAngles_X"].tolist()
                }
            }

    def to_dict(self):
        return {
            **self.trial_info,
            **self.subject_params,
            **self.body_measurements,
            **self.norm_kinematics
        }
    
# Kelas GaitAnalysisData untuk data pasien (yang lama)
class GaitAnalysisData:
    def __init__(self, data):
        self.df = pd.read_excel(data, sheet_name=[0, 1])  # Read the uploaded file
        self.suin = self.df[0]
        self.normkin = self.df[1].iloc[:, :31]

        # Clean and extract necessary data
        self.cleaned_data = self.clean_data()
        self.normkin_processed = self.process_normkin()

        # Extract and store various sections
        self.trial_info = self.extract_trial_info()
        self.subject_params = self.extract_subject_params()
        self.body_measurements = self.extract_body_measurements()
        self.norm_kinematics = self.extract_norm_kinematics()

    def clean_data(self):
        cleaned_data = self.suin.dropna(how='all')
        cleaned_data.reset_index(drop=True, inplace=True)
        return cleaned_data

    def process_normkin(self):
        column_namesX = [col for col in self.normkin.columns if col.endswith('X')]
        normkin = self.normkin.loc[:, column_namesX]
        normkin.insert(0, "Percentage of Gait Cycle", self.df[1].iloc[:, 0].tolist())
        return normkin

    def extract_trial_info(self):
        return {
            "Trial Information": {
                "Trial Name": self.cleaned_data.iloc[1, 2]
            }
        }

    def extract_subject_params(self):
        return {
            "Subject Parameters": {
                "Subject Name": self.cleaned_data.iloc[3, 2],
                "Bodymass (kg)": self.cleaned_data.iloc[4, 2],
                "Height (mm)": self.cleaned_data.iloc[5, 2]
            }
        }

    def extract_body_measurements(self):
        return {
            "Body Measurements": {
                "Leg Length (mm)": {
                    "Left": self.cleaned_data.iloc[12, 2],
                    "Right": self.cleaned_data.iloc[12, 3]
                },
                "Knee Width (mm)": {
                    "Left": self.cleaned_data.iloc[13, 2],
                    "Right": self.cleaned_data.iloc[13, 3]
                },
                "Ankle Width (mm)": {
                    "Left": self.cleaned_data.iloc[14, 2],
                    "Right": self.cleaned_data.iloc[14, 3]
                }
            }
        }

    def extract_norm_kinematics(self):
        return {
            "Norm Kinematics": {
                "Percentage of Gait Cycle": self.normkin_processed['Percentage of Gait Cycle'].values.tolist(),  # Convert to list
                "LPelvisAngles_X": self.normkin_processed["LPelvisAngles_X"].values.tolist(),  # Convert to list
                "RPelvisAngles_X": self.normkin_processed["RPelvisAngles_X"].values.tolist(),  # Convert to list
                "LHipAngles_X": self.normkin_processed["LHipAngles_X"].values.tolist(),  # Convert to list
                "RHipAngles_X": self.normkin_processed["RHipAngles_X"].values.tolist(),  # Convert to list
                "LKneeAngles_X": self.normkin_processed["LKneeAngles_X"].values.tolist(),  # Convert to list
                "RKneeAngles_X": self.normkin_processed["RKneeAngles_X"].values.tolist(),  # Convert to list
                "LAnkleAngles_X": self.normkin_processed["LAnkleAngles_X"].values.tolist(),  # Convert to list
                "RAnkleAngles_X": self.normkin_processed["RAnkleAngles_X"].values.tolist(),  # Convert to list
                "LFootProgressAngles_X": self.normkin_processed["LFootProgressAngles_X"].values.tolist(),  # Convert to list
                "RFootProgressAngles_X": self.normkin_processed["RFootProgressAngles_X"].values.tolist()   # Convert to list
            }
        }

    def to_dict(self):
        # Combine all sections into a single dictionary
        return {
            **self.trial_info,
            **self.subject_params,
            **self.body_measurements,
            **self.norm_kinematics
        }
        
class TerapisPage:
    def __init__(self):
        # Hapus daftar user terapis sementara
        # self.terapis_users = {"terapis1": "1234"}  # DIHAPUS
        pass
    
    # ==================== FUNGSI HELPER UNTUK GAIT PHASE ====================
    def get_gait_phase(self, percentage):
        """Mengembalikan nama fase gait berdasarkan persentase siklus (0-100)"""
        if 0 <= percentage <= 2:
            return "Initial Contact"
        elif 2 < percentage <= 10:
            return "Loading Response"
        elif 10 < percentage <= 30:
            return "Mid-Stance"
        elif 30 < percentage <= 50:
            return "Terminal Stance"
        elif 50 < percentage <= 60:
            return "Pre-Swing"
        elif 60 < percentage <= 73:
            return "Initial Swing"
        elif 73 < percentage <= 87:
            return "Mid-Swing"
        elif 87 < percentage <= 100:
            return "Terminal Swing"
        else:
            return "Unknown"

    def get_phase_indices(self, percentage_list):
        """Mengembalikan dictionary indeks untuk setiap fase"""
        phases = {
            'Initial Contact (0-2%)': (0, 2),
            'Loading Response (2-10%)': (2, 10),
            'Mid-Stance (10-30%)': (10, 30),
            'Terminal Stance (30-50%)': (30, 50),
            'Pre-Swing (50-60%)': (50, 60),
            'Initial Swing (60-73%)': (60, 73),
            'Mid-Swing (73-87%)': (73, 87),
            'Terminal Swing (87-100%)': (87, 100)
        }
        
        phase_indices = {}
        for phase, (start, end) in phases.items():
            # Cari indeks yang sesuai dengan rentang persentase
            indices = [i for i, p in enumerate(percentage_list) if start <= p <= end]
            phase_indices[phase] = indices
        
        return phase_indices

    def calculate_mae_per_phase(self, patient_values, normal_values, phase_indices):
        """Menghitung MAE untuk setiap fase gait"""
        mae_per_phase = {}
        
        for phase, indices in phase_indices.items():
            if indices:  # Pastikan ada indeks
                patient_phase = [patient_values[i] for i in indices]
                normal_phase = [normal_values[i] for i in indices]
                mae = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                mae_per_phase[phase] = mae
        
        return mae_per_phase

    # def display_mae_per_phase(self, mae_phases, joint_name):
    #     """Menampilkan MAE per fase dalam format yang rapi tanpa level keparahan"""
    #     with st.expander(f"Detail MAE per Fase - {joint_name}"):
    #         # Buat dataframe untuk tampilan
    #         phase_data = []
    #         for phase, mae in mae_phases.items():
    #             phase_data.append({
    #                 'Fase Gait': phase,
    #                 'MAE (°)': f"{mae:.2f}"
    #             })
            
    #         df_phases = pd.DataFrame(phase_data)
    #         st.dataframe(df_phases, use_container_width=True, hide_index=True)
            
    #         # Tampilkan fase dengan MAE tertinggi
    #         if mae_phases:
    #             max_phase = max(mae_phases, key=mae_phases.get)
    #             max_mae = mae_phases[max_phase]
    #             st.info(f"**Fase dengan deviasi terbesar:** {max_phase} (MAE = {max_mae:.2f}°)")

    def calculate_bounds_from_normal_data(self, filtered_df):
        """Menghitung upper bound dan lower bound dari data normal"""
        bounds = {}
        
        # Daftar joint yang akan dihitung
        joints = {
            'LPelvisAngles_X': [],
            'RPelvisAngles_X': [],
            'LHipAngles_X': [],
            'RHipAngles_X': [],
            'LKneeAngles_X': [],
            'RKneeAngles_X': [],
            'LAnkleAngles_X': [],
            'RAnkleAngles_X': []
        }
        
        for joint in joints.keys():
            if joint in filtered_df.columns:
                # Ambil semua nilai untuk joint ini
                joint_values = pd.DataFrame(filtered_df[joint].tolist())
                
                # Hitung mean dan std
                mean_values = joint_values.mean(axis=0).values
                std_values = joint_values.std(axis=0).values
                
                # Upper bound = mean + 2*std (95% confidence interval)
                # Lower bound = mean - 2*std
                upper_bound = mean_values + (2 * std_values)
                lower_bound = mean_values - (2 * std_values)
                
                bounds[joint] = {
                    'upper': np.mean(upper_bound),  # Rata-rata upper bound sepanjang gait cycle
                    'lower': np.mean(lower_bound),  # Rata-rata lower bound sepanjang gait cycle
                    'upper_by_cycle': upper_bound.tolist(),
                    'lower_by_cycle': lower_bound.tolist(),
                    'mean_by_cycle': mean_values.tolist()
                }
        
        return bounds
        
    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)
        # inisialisasi session state
        if 'uploaded_patient_data' not in st.session_state:
            st.session_state.uploaded_patient_data = None
        if 'norm_kinematics_df' not in st.session_state:
            st.session_state.norm_kinematics_df = None
        if "terapis_logged_in" not in st.session_state:
            st.session_state.terapis_logged_in = False
        if "terapis_user_id" not in st.session_state:
            st.session_state.terapis_user_id = None
        if "terapis_nama" not in st.session_state:
            st.session_state.terapis_nama = None 
        if "terapis_menu" not in st.session_state:
            st.session_state.terapis_menu = "Dashboard"       

        # jika belum login → tampilkan form login
        if not st.session_state.terapis_logged_in:
            username, password, submit = login_form("Dokter")
            if submit:
                # Cek login dari database
                user_data = self._check_terapis_login(username, password)
                if user_data:
                    st.session_state.terapis_logged_in = True
                    st.session_state.terapis_user_id = user_data['user_id']
                    st.session_state.terapis_nama = user_data['nama_lengkap']
                    st.session_state.terapis_role = user_data['role']
                    st.success(f"Login berhasil! Selamat datang Dr. {user_data['nama_lengkap']}")
                    st.rerun()
                else:
                    st.error("Login gagal! Username atau password salah.")
            return  # hentikan eksekusi di sini sampai login selesai
        
        # ====== Sidebar ======
        dokter_nama = st.session_state.get('terapis_nama', 'Dokter')
        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> Dr. {dokter_nama}</p>", unsafe_allow_html=True)

        st.sidebar.markdown("<p class='sidebar-title'>Menu</p>", unsafe_allow_html=True)
        
        menu_list = ["Dashboard", "Input Baseline Data Gait", "Input Pemeriksaan Pasien", "Riwayat Pemeriksaan", "Logout"]

        for menu in menu_list:
            if st.sidebar.button(
                menu,
                use_container_width=True,
                type="primary" if st.session_state.terapis_menu == menu else "secondary"
            ):
                st.session_state.terapis_menu = menu
                st.rerun()

        # ====== Konten utama ======
        if st.session_state.terapis_menu == "Dashboard":
            self.show_dashboard()
        elif st.session_state.terapis_menu == "Input Baseline Data Gait":
            self.input_data_gait_normal()

        elif st.session_state.terapis_menu == "Input Pemeriksaan Pasien":
            self.input_data_gait_pasien()

        elif st.session_state.terapis_menu == "Riwayat Pemeriksaan":
            self.show_examination_history()

        elif st.session_state.terapis_menu == "Logout":
            st.session_state.terapis_logged_in = False
            st.session_state.terapis_user_id = None
            st.session_state.terapis_nama = None
            st.session_state.terapis_role = None
            st.session_state.terapis_menu = "Dashboard"
            st.session_state.role = None
            st.rerun()

    def _check_terapis_login(self, user_id, password):
        """Cek login dokter dari database"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['users']
            
            # Cari user dengan role terapis
            terapis = collection.find_one({
                'user_id': user_id,
                'role': 'dokter'
            })
            
            if terapis:
                # Ambil password hash dari database
                stored_password = terapis.get('password')
                # Verifikasi password dengan bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return {
                        'user_id': terapis.get('user_id'),
                        'nama_lengkap': terapis.get('nama_lengkap'),
                        'role': terapis.get('role'),
                        'tanggal_lahir': terapis.get('tanggal_lahir', ''),
                        'jenis_kelamin': terapis.get('jenis_kelamin', '')
                }
            return None
            
        except Exception as e:
            st.error(f"Error checking login: {e}")
            return None
    
    def input_data_gait_normal(self):
        st.subheader("Input Baseline Data Gait")
        # st.markdown("### Upload Data Subjek Normal")
        uploaded_file = st.file_uploader("Upload file data subjek gait normal (Format .xlsx)", type=["xlsx"], key="normal_upload")
        
        if uploaded_file is not None:
            col1, col2 = st.columns(2)
            with col1:
                usia = st.number_input("Masukkan Usia:", min_value=0, max_value=120, key="usia_normal")
            with col2:
                jenis_kelamin = st.selectbox("Jenis Kelamin", ["Pilih Jenis Kelamin", "L", "P"], key="gender_normal").strip().upper()
                # st.text_input("Masukkan Jenis Kelamin (L/P):", key="gender_normal").strip().upper()

            if st.button("Proses Data Normal", key="process_normal"):
                if usia == 0 or jenis_kelamin == "":
                    st.warning("Harap masukkan usia dan jenis kelamin sebelum memproses file.")
                elif jenis_kelamin not in ['L', 'P']:
                    st.warning("Jenis kelamin harus 'L' (Laki-laki) atau 'P' (Perempuan).")
                else:
                    try:
                        content = uploaded_file.read()
                        gait_data = GaitAnalysisDataNormal(content, usia, jenis_kelamin)
                        
                        if hasattr(gait_data, 'df'):
                            data_dict = gait_data.to_dict()

                            # Periksa apakah ada data kosong (None atau NaN)
                            def check_missing(data):
                                if isinstance(data, dict):
                                    return any(check_missing(v) for v in data.values())
                                elif isinstance(data, list):
                                    return any(check_missing(v) for v in data)
                                else:
                                    # Cek apakah nilai kosong (NaN atau None)
                                    return pd.isna(data)

                            def check_norm_kinematics(norm_kinematics):
                                for key, value in norm_kinematics.items():
                                    if isinstance(value, list):
                                        for v in value:
                                            if pd.isna(v):
                                                return True  # Ada NaN/None
                                            try:
                                                float(v)  # pastikan bisa dikonversi ke angka
                                            except ValueError:
                                                return True  # Ada teks non-numerik
                                    else:
                                        return True  # Format tidak sesuai, harusnya list
                                return False  # Semua aman

                            norm_kin_data = data_dict.get("Norm Kinematics", {})
                            if check_missing(data_dict) or check_norm_kinematics(norm_kin_data):
                                st.error("Data tidak valid: terdapat nilai kosong atau teks non-numerik.")
                            else:
                                try:
                                    client = get_mongo_client()
                                    db = client['GaitDB']
                                    collection = db['gait_data']
                                    data_dict["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    collection.insert_one(data_dict)
                                    st.success("Data berhasil disimpan ke database!")
                                    
                                    # Tampilkan ringkasan data
                                    st.markdown("### Ringkasan Data yang Disimpan")
                                    st.json({
                                        "Nama Subjek": data_dict["Subject Parameters"]["Subject Name"],
                                        "Usia": data_dict["Subject Parameters"]["Age"],
                                        "Jenis Kelamin": data_dict["Subject Parameters"]["Gender"],
                                        "BMI": f"{data_dict['Subject Parameters']['BMI']:.2f}",
                                        "Klasifikasi BMI": data_dict["Subject Parameters"]["BMI Classification"]
                                    })
                                    
                                except Exception as e:
                                    st.error(f"Error menyimpan data ke database: {e}")
                        else:
                            st.error("Gagal memproses data yang diupload.")
                            
                    except Exception as e:
                        st.error(f"Error dalam memproses file: {e}")        
    def input_data_gait_pasien(self):
        st.subheader("Input Pemeriksaan Pasien")
        
        # Ambil data pasien dari database untuk dropdown
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['users']
            
            # Ambil semua data pasien - gunakan field dengan huruf kecil sesuai admin.py
            pasien_data = list(collection.find(
                {'role': 'pasien'}, 
                {'user_id': 1, 'nama_lengkap': 1}))

            # Buat opsi dropdown
            pasien_options = ["Pilih Data Pasien yang akan diperiksa"] + [
                f"{pasien['user_id']} - {pasien['nama_lengkap']}" 
                for pasien in pasien_data 
                if 'user_id' in pasien and 'nama_lengkap' in pasien
            ]
            
        except Exception as e:
            st.error(f"Error mengambil data pasien: {e}")
            pasien_options = ["Pilih Data Pasien yang akan diperiksa"]
        
        # Dropdown untuk memilih pasien
        selected_pasien = st.selectbox(
            "Pilih Data Pasien yang akan diperiksa",
            options=pasien_options,
            key="pasien_dropdown"
        )
        
        # Jika pasien dipilih, ekstrak NIK dan nama
        pasien_user_id = ""
        nama_pasien = ""
        
        if selected_pasien != "Pilih Data Pasien yang akan diperiksa":
            # Ekstrak user_id dan nama dari string yang dipilih
            try:
                parts = selected_pasien.split(" - ")
                if len(parts) == 2:
                    pasien_user_id = parts[0].strip()
                    nama_pasien = parts[1].strip()
                    # st.success(f"**Pasien Terpilih:** {nama_pasien} (User ID: {pasien_user_id})")
            except Exception as e:
                st.error(f"Error memproses data pasien: {e}")        
        # Input tanggal pemeriksaan
        tanggal = st.date_input("Tanggal Pemeriksaan")

        col1, col2 = st.columns(2)
        with col1:
            tinggi_badan = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.1f")
        
        with col2:
            berat_badan = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.1f")
        
        if tinggi_badan > 0:
            tinggi_m = tinggi_badan / 100  # Convert cm to m
            bmi = berat_badan / (tinggi_m ** 2)
            
            # Klasifikasi BMI
            if bmi < 17.0:
                bmi_class = "Kurus Berat"
            elif bmi < 18.5:
                bmi_class = "Kurus Ringan"
            elif bmi < 25.1:
                bmi_class = "Normal"
            elif bmi < 27.1:
                bmi_class = "Gemuk Ringan"
            else:
                bmi_class = "Gemuk Berat"
            
            st.info(f"**BMI:** {bmi:.2f} ({bmi_class})")

        # Upload file data GAIT pasien
        st.markdown("---")
        st.markdown("### Upload Data Gait Pasien")
        uploaded_file = st.file_uploader("Upload file data gait pasien (Format .xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            # Validasi: pastikan pasien sudah dipilih
            if selected_pasien == "Pilih Data Pasien yang akan diperiksa":
                st.warning("⚠️ Silakan pilih pasien terlebih dahulu sebelum mengupload file.")
                return
            
            # Hanya proses data ketika tombol submit ditekan
            if st.button("Simpan Data Pemeriksaan", key="save_patient", type="primary"):
                try:
                    with st.spinner("Memproses data pasien..."):
                        # Proses file dengan GaitAnalysisData
                        gait_data = GaitAnalysisData(uploaded_file)
                        processed_data = gait_data.to_dict()

                        # Ekstrak data untuk Norm Kinematics (hanya yang diperlukan)
                        norm_kinematics = processed_data["Norm Kinematics"]
                        rows = []
                        
                        for i in range(len(norm_kinematics["Percentage of Gait Cycle"])):
                            row = {
                                "%cycle": norm_kinematics["Percentage of Gait Cycle"][i],
                                "LPelvisAngles_X": norm_kinematics["LPelvisAngles_X"][i],
                                "RPelvisAngles_X": norm_kinematics["RPelvisAngles_X"][i],
                                "LHipAngles_X": norm_kinematics["LHipAngles_X"][i],
                                "RHipAngles_X": norm_kinematics["RHipAngles_X"][i],
                                "LKneeAngles_X": norm_kinematics["LKneeAngles_X"][i],
                                "RKneeAngles_X": norm_kinematics["RKneeAngles_X"][i],
                                "LAnkleAngles_X": norm_kinematics["LAnkleAngles_X"][i],
                                "RAnkleAngles_X": norm_kinematics["RAnkleAngles_X"][i],
                            }
                            rows.append(row)

                        # Simpan ke session state - HANYA DATA YANG DIPERLUKAN
                        st.session_state.norm_kinematics_df = pd.DataFrame(rows)
                        
                        # Simpan data pasien ke MongoDB (tanpa diagnosa)
                        examination_data = {
                            'pasien_id': pasien_user_id,
                            'nama_pasien': nama_pasien,

                            'dokter_id': st.session_state.get('terapis_user_id', 'unknown'),
                            'dokter_nama': st.session_state.get('terapis_nama', 'unknown'),

                            'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d"),
                            'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                            'tinggi_badan': tinggi_badan,
                            'berat_badan': berat_badan,
                            'bmi': bmi,
                            'bmi_classification': bmi_class,
                            
                            'file_info': {
                                'file_name': uploaded_file.name,
                                'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            },
                            'gait_data': processed_data,
                            'norm_kinematics': rows
                        }
                        
                        # Simpan ke MongoDB
                        client = get_mongo_client()
                        db = client['GaitDB']
                        collection = db['patient_examinations']
                        
                        # Cek apakah sudah ada pemeriksaan untuk pasien di tanggal yang sama
                        existing_exam = collection.find_one({
                            'pasien_id': pasien_user_id,
                            'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d")
                        })
                        
                        if existing_exam:
                            st.warning(f"Pasien {nama_pasien} sudah memiliki data pemeriksaan pada tanggal {tanggal.strftime('%d %B %Y')}. Data akan diupdate.")
                            # Update data yang sudah ada
                            collection.update_one(
                                {'_id': existing_exam['_id']},
                                {'$set': examination_data}
                            )
                            st.success(f"Data gait pasien dengan NIK {pasien_user_id} berhasil diupdate!")
                        else:
                            # Insert data baru
                            result = collection.insert_one(examination_data)
                            st.success(f"Data gait pasien dengan NIK {pasien_user_id} berhasil disimpan!")
                                            
                        # st.info(f"File: {uploaded_file.name}")
                        # st.info(f"Pasien: {nama_pasien} (NIK: {pasien_user_id})")
                        # st.info(f"Tanggal Pemeriksaan: {tanggal.strftime('%d %B %Y')}")
                            
                except Exception as e:
                    st.error(f"Error dalam memproses file: {e}")
        else:
            # Reset session state jika tidak ada file yang diupload
            if 'uploaded_patient_data' in st.session_state:
                del st.session_state.uploaded_patient_data
            if 'norm_kinematics_df' in st.session_state:
                del st.session_state.norm_kinematics_df

    def show_examination_history(self):
        st.subheader("Riwayat Pemeriksaan")
        
        try:
            # Koneksi ke MongoDB
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['patient_examinations']
            
            # Ambil data dokter yang sedang login
            dokter_id = st.session_state.get('terapis_user_id', None)
            dokter_nama = st.session_state.get('terapis_nama', None)
            
            if not dokter_id:
                st.error("Data dokter tidak ditemukan. Silakan login kembali.")
                return

            # Ambil data pemeriksaan hanya untuk dokter yang login
            # Gunakan filter berdasarkan dokter_id
            examinations = list(collection.find(
                {'dokter_id': dokter_id}  # Filter hanya untuk dokter yang login
            ).sort('upload_date', -1))
            
            if not examinations:
                st.info(f"Belum ada riwayat pemeriksaan pasien untuk Dr. {dokter_nama}.")
                return
            
            total_exams = len(examinations)
            # unique_patients = len(set(exam.get('pasien_id') for exam in examinations if exam.get('pasien_id')))

            # col1, col2 = st.columns(2)
            # with col1:
            #     st.metric("Total Pemeriksaan", total_exams)
            # # with col2:
            # #     st.metric("Total Pasien Unik", unique_patients)
            # with col2:
            #     # Hitung pemeriksaan bulan ini
            #     current_month = datetime.now().strftime("%Y-%m")
            #     monthly_exams = len([exam for exam in examinations 
            #                     if exam.get('upload_date', '').startswith(current_month)])
            #     st.metric("Pemeriksaan Bulan Ini", monthly_exams)

            # st.markdown("---")

            # Siapkan data untuk tabel
            table_data = []
            for exam in examinations:
                pasien_id = exam.get('pasien_id', 'N/A')
                nama_pasien = exam.get('nama_pasien', 'N/A')
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
                    'File Name': file_name
                })
            
            # Tampilkan dalam tabel
            df = pd.DataFrame(table_data)
            # st.dataframe(df, use_container_width=True)
            
            # Fitur filter
            st.markdown("### Filter Riwayat")
            col1, col2 = st.columns(2)
            
            with col1:
                filter_nik = st.text_input("Filter berdasarkan NIK Pasien:")
            with col2:
                filter_nama = st.text_input("Filter berdasarkan Nama Pasien:")
            # with col3:
            #     filter_tanggal = st.text_input("Filter berdasarkan Tanggal Pemeriksaan (YYYY-MM-DD):")

            
            # Apply filters
            filtered_df = df.copy()
            if filter_nik:
                filtered_df = filtered_df[filtered_df['NIK Pasien'].str.contains(filter_nik, case=False, na=False)]
            if filter_nama:
                filtered_df = filtered_df[filtered_df['Nama Pasien'].str.contains(filter_nama, case=False, na=False)]
            # if filter_tanggal:
            #     filtered_df = filtered_df[filtered_df['Tanggal Pemeriksaan'].astype(str).str.contains(filter_tanggal, case=False, na=False)]
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
            st.error(f"Error mengambil data riwayat: {e}")

    def show_dashboard(self):
        st.markdown("## Dashboard Gait Analysis")

        # CEK LEBIH EFISIEN - hanya cek key existence
        has_patient_data = ('uploaded_patient_data' in st.session_state and 
                           'norm_kinematics_df' in st.session_state and
                           st.session_state.norm_kinematics_df is not None)

        if has_patient_data:
            try:
                # with st.spinner("Memuat data dan membuat visualisasi..."):
                self.process_dashboard_with_patient()
            except Exception as e:
                st.error(f"Error dalam memproses dashboard: {e}")
        else:
            # Tampilkan dashboard tanpa data pasien
            st.warning("ℹ️ Tidak ada data pasien yang diupload. Silakan upload data pasien di menu 'Input Pemeriksan Pasien' untuk melihat analisis perbandingan.")
            # st.markdown("---")
            self.show_normal_dashboard()

    def process_dashboard_with_patient(self):
        """Method terpisah untuk memproses dashboard dengan data pasien"""
        px.defaults.template = 'plotly_dark'
        px.defaults.color_continuous_scale = 'reds'
        
        # Koneksi ke MongoDB - dengan timeout
        client = get_mongo_client()
        db = client['GaitDB']
        collection = db['gait_data']
        
        # Membaca data dari MongoDB dengan limit
        cursor = collection.find().limit(100)  # Batasi data untuk performa
        data = list(cursor)
        
        if len(data) == 0:
            st.error("Database Normal Belum Ada. Silahkan Upload Data Normal pada Menu 'Input Baseline Data Gait'")
            return
        
        # Normalisasi data untuk DataFrame
        df = pd.json_normalize(data)
        df.columns = df.columns.str.replace('Trial Information.', '')
        df.columns = df.columns.str.replace('Subject Parameters.', '')
        df.columns = df.columns.str.replace('Body Measurements.', '')
        df.columns = df.columns.str.replace('Norm Kinematics.', '')

        # ====== FILTER ======
        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### Filter Data")

        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            min_age = df['Age'].min()
            max_age = df['Age'].max()
            age_range = st.slider(
                'Filter by Age Range:',
                min_value=min_age,
                max_value=max_age,
                value=(min_age, max_age)
            )

        with col2:
            bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
            classbmi = st.selectbox(label="BMI Classification", options=bmi_options)

        with col3:
            gender_mapping = {"L": "Pria", "P": "Wanita"}
            df["Gender"] = df["Gender"].map(gender_mapping)
            gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
            gender = st.selectbox(label="Gender", options=gender_options)

        st.markdown("</div>", unsafe_allow_html=True)
        # st.markdown("---")
            
        # Apply filters
        filtered_df = df[(df['Age'] >= age_range[0]) & (df['Age'] <= age_range[1])]
        if classbmi != "All BMI Classification":
            filtered_df = filtered_df[filtered_df['BMI Classification'] == classbmi]
        if gender != "All Gender":
            filtered_df = filtered_df[filtered_df["Gender"] == gender]
            
        if filtered_df.empty:
            st.error(f"Tidak terdapat data dengan jenis kelamin {gender} yang terklasifikasi {classbmi}")
            return
            
        st.markdown(f"**Total Records:** {len(filtered_df)}")

        st.session_state.filtered_normal_df = filtered_df
        # Gunakan data pasien dari session state
        norm_kinematics_df = st.session_state.norm_kinematics_df

        # Buat visualisasi untuk setiap joint
        self.create_visualizations(filtered_df, norm_kinematics_df)

    def create_visualizations(self, filtered_df, norm_kinematics_df):
        """Membuat visualisasi untuk semua joint"""
        # Persentase gait cycle (0-100)
        percentage_cycle = list(range(101))

        # Dapatkan indeks untuk setiap fase
        phase_indices = self.get_phase_indices(percentage_cycle)
        
        # ==================== PELVIS ====================
        # Extract data pelvis dari filtered_df
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())

        # Hitung mean untuk pelvis
        mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
        std_l_pelvis = l_pelvis_angles.std(axis=0) / np.sqrt(l_pelvis_angles.shape[0])
        mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
        std_r_pelvis = r_pelvis_angles.std(axis=0) / np.sqrt(r_pelvis_angles.shape[0])

        # Konversi ke numpy array jika perlu
        std_l_pelvis = std_l_pelvis.values if isinstance(std_l_pelvis, pd.Series) else std_l_pelvis
        std_r_pelvis = std_r_pelvis.values if isinstance(std_r_pelvis, pd.Series) else std_r_pelvis

        # Buat dataframe untuk pelvis
        lpelvis = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Lpelvis': mean_l_pelvis,
            'std_Lpelvis': std_l_pelvis,
            'your left pelvis': norm_kinematics_df['LPelvisAngles_X'].values})
        
        rpelvis = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Rpelvis': mean_r_pelvis,
            'std_Rpelvis': std_r_pelvis,
            'your right pelvis': norm_kinematics_df['RPelvisAngles_X'].values})

        # Hitung MAE per fase untuk Pelvis
        mae_pelvis_left_phases = self.calculate_mae_per_phase(
            lpelvis["your left pelvis"].values, 
            lpelvis["Mean_Lpelvis"].values, 
            phase_indices)
        
        mae_pelvis_right_phases = self.calculate_mae_per_phase(
            rpelvis["your right pelvis"].values, 
            rpelvis["Mean_Rpelvis"].values, 
            phase_indices)

        # ==================== KNEE ====================
        # Extract data knee dari filtered_df
        l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
        r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
        
        # Hitung mean untuk knee
        mean_l_knee = l_knee_angles.mean(axis=0).values
        std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
        mean_r_knee = r_knee_angles.mean(axis=0).values
        std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])
        
        # Konversi ke numpy array jika perlu
        std_l_knee = std_l_knee.values if isinstance(std_l_knee, pd.Series) else std_l_knee
        std_r_knee = std_r_knee.values if isinstance(std_r_knee, pd.Series) else std_r_knee
        
        # Buat dataframe untuk knee
        lknee = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Lknee': mean_l_knee,
            'std_Lknee': std_l_knee,
            'your left knee': norm_kinematics_df['LKneeAngles_X'].values
        })
        
        rknee = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Rknee': mean_r_knee,
            'std_Rknee': std_r_knee,
            'your right knee': norm_kinematics_df['RKneeAngles_X'].values
        })
        
        # Hitung MAE per fase untuk Knee
        mae_knee_left_phases = self.calculate_mae_per_phase(
            lknee["your left knee"].values, 
            lknee["Mean_Lknee"].values, 
            phase_indices
        )
        
        mae_knee_right_phases = self.calculate_mae_per_phase(
            rknee["your right knee"].values, 
            rknee["Mean_Rknee"].values, 
            phase_indices
        )
        
        # ==================== HIP ====================
        # Extract data hip dari filtered_df
        l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
        r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
        
        # Hitung mean untuk hip
        mean_l_hip = l_hip_angles.mean(axis=0).values
        std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
        mean_r_hip = r_hip_angles.mean(axis=0).values
        std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])
        
        # Konversi ke numpy array jika perlu
        std_l_hip = std_l_hip.values if isinstance(std_l_hip, pd.Series) else std_l_hip
        std_r_hip = std_r_hip.values if isinstance(std_r_hip, pd.Series) else std_r_hip
        
        # Buat dataframe untuk hip
        lhip = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Lhip': mean_l_hip,
            'std_Lhip': std_l_hip,
            'your left hip': norm_kinematics_df['LHipAngles_X'].values
        })
        
        rhip = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Rhip': mean_r_hip,
            'std_Rhip': std_r_hip,
            'your right hip': norm_kinematics_df['RHipAngles_X'].values
        })
        
        # Hitung MAE per fase untuk Hip
        mae_hip_left_phases = self.calculate_mae_per_phase(
            lhip["your left hip"].values, 
            lhip["Mean_Lhip"].values, 
            phase_indices
        )
        
        mae_hip_right_phases = self.calculate_mae_per_phase(
            rhip["your right hip"].values, 
            rhip["Mean_Rhip"].values, 
            phase_indices
        )
        
        # ==================== ANKLE ====================
        # Extract data ankle dari filtered_df
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
        
        # Hitung mean untuk ankle
        mean_l_ankle = l_ankle_angles.mean(axis=0).values
        std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
        mean_r_ankle = r_ankle_angles.mean(axis=0).values
        std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])
        
        # Konversi ke numpy array jika perlu
        std_l_ankle = std_l_ankle.values if isinstance(std_l_ankle, pd.Series) else std_l_ankle
        std_r_ankle = std_r_ankle.values if isinstance(std_r_ankle, pd.Series) else std_r_ankle
        
        # Buat dataframe untuk ankle
        lankle = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Lankle': mean_l_ankle,
            'std_Lankle': std_l_ankle,
            'your left ankle': norm_kinematics_df['LAnkleAngles_X'].values
        })
        
        rankle = pd.DataFrame({
            "%cycle": percentage_cycle,
            'Mean_Rankle': mean_r_ankle,
            'std_Rankle': std_r_ankle,
            'your right ankle': norm_kinematics_df['RAnkleAngles_X'].values
        })
        
        # Hitung MAE per fase untuk Ankle
        mae_ankle_left_phases = self.calculate_mae_per_phase(
            lankle["your left ankle"].values, 
            lankle["Mean_Lankle"].values, 
            phase_indices
        )
        
        mae_ankle_right_phases = self.calculate_mae_per_phase(
            rankle["your right ankle"].values, 
            rankle["Mean_Rankle"].values, 
            phase_indices
        )

        # ====== HITUNG MAE KESELURUHAN ======
        maelpelvis = np.mean(np.abs(lpelvis["your left pelvis"] - lpelvis["Mean_Lpelvis"]))
        maerpelvis = np.mean(np.abs(rpelvis["your right pelvis"] - rpelvis["Mean_Rpelvis"]))
        maelknee = np.mean(np.abs(lknee["your left knee"] - lknee["Mean_Lknee"]))
        maerknee = np.mean(np.abs(rknee["your right knee"] - rknee["Mean_Rknee"]))
        maelhip = np.mean(np.abs(lhip["your left hip"] - lhip["Mean_Lhip"]))
        maerhip = np.mean(np.abs(rhip["your right hip"] - rhip["Mean_Rhip"]))
        maelankle = np.mean(np.abs(lankle["your left ankle"] - lankle["Mean_Lankle"]))
        maerankle = np.mean(np.abs(rankle["your right ankle"] - rankle["Mean_Rankle"]))
        
        # ====== SIMPAN KE SESSION STATE ======
        # MAE keseluruhan
        st.session_state.mae_pelvis_left = maelpelvis
        st.session_state.mae_pelvis_right = maerpelvis
        st.session_state.mae_knee_left = maelknee
        st.session_state.mae_knee_right = maerknee
        st.session_state.mae_hip_left = maelhip
        st.session_state.mae_hip_right = maerhip
        st.session_state.mae_ankle_left = maelankle
        st.session_state.mae_ankle_right = maerankle
        
        # MAE per fase
        st.session_state.mae_pelvis_left_phases = mae_pelvis_left_phases
        st.session_state.mae_pelvis_right_phases = mae_pelvis_right_phases
        st.session_state.mae_knee_left_phases = mae_knee_left_phases
        st.session_state.mae_knee_right_phases = mae_knee_right_phases
        st.session_state.mae_hip_left_phases = mae_hip_left_phases
        st.session_state.mae_hip_right_phases = mae_hip_right_phases
        st.session_state.mae_ankle_left_phases = mae_ankle_left_phases
        st.session_state.mae_ankle_right_phases = mae_ankle_right_phases
        
        # Simpan phase_indices juga
        st.session_state.phase_indices = phase_indices

        # ====== BUAT FIGURES ======
        fig1 = self.create_pelvis_figure(lpelvis, "Left Pelvis", 'orange')
        fig2 = self.create_pelvis_figure(rpelvis, "Right Pelvis", 'dark blue')
        fig3 = self.create_joint_figure(lknee, "Left Knee", 'orange')
        fig4 = self.create_joint_figure(rknee, "Right Knee", 'dark blue')
        fig5 = self.create_joint_figure(lhip, "Left Hip", 'orange')
        fig6 = self.create_joint_figure(rhip, "Right Hip", 'dark blue')
        fig7 = self.create_joint_figure(lankle, "Left Ankle", 'orange')
        fig8 = self.create_joint_figure(rankle, "Right Ankle", 'dark blue')

        # Tampilkan dalam tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL RINGKASAN AI"])

        with tab1:
            tab1.subheader("PELVIS")
            tab1.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')

            col1, col2 = tab1.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Pelvis: {maelpelvis:.2f}°**")
                # self.display_mae_per_phase(mae_pelvis_left_phases, "Left Pelvis")
                
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Pelvis: {maerpelvis:.2f}°**")
                # self.display_mae_per_phase(mae_pelvis_right_phases, "Right Pelvis")
                
        with tab2:
            tab2.subheader("KNEE")
            tab2.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')

            col1, col2 = tab2.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Knee: {maelknee:.2f}°**")
                # self.display_mae_per_phase(mae_knee_left_phases, "Left Knee")
            with col2:
                st.plotly_chart(fig4, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Knee: {maerknee:.2f}°**")
                # self.display_mae_per_phase(mae_knee_right_phases, "Right Knee")

        with tab3:
            tab3.subheader("HIP")
            tab3.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')

            col1, col2 = tab3.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Hip: {maelhip:.2f}°**")
                # self.display_mae_per_phase(mae_hip_left_phases, "Left Hip")
            with col2:
                st.plotly_chart(fig6, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Hip: {maerhip:.2f}°**")
                # self.display_mae_per_phase(mae_hip_right_phases, "Right Hip")

        with tab4:
            tab4.subheader("ANKLE")
            tab4.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')

            col1, col2 = tab4.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Ankle: {maelankle:.2f}°**")
                # self.display_mae_per_phase(mae_ankle_left_phases, "Left Ankle")
            with col2:
                st.plotly_chart(fig8, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Ankle: {maerankle:.2f}°**")
                # self.display_mae_per_phase(mae_ankle_right_phases, "Right Ankle")

        with tab5:
            self.show_ai_summary_tab_with_phases()

    def create_default_summaries(self, prompt_type):
        """Membuat default summaries jika AI gagal"""
        return [
            {
                "label": f"Prompt {prompt_type} - Variasi 1",
                "value": "Ringkasan tidak tersedia. Silakan periksa koneksi API Gemini."
            },
            {
                "label": f"Prompt {prompt_type} - Variasi 2", 
                "value": "Ringkasan tidak tersedia. Silakan periksa koneksi API Gemini."
            },
            {
                "label": f"Prompt {prompt_type} - Variasi 3",
                "value": "Ringkasan tidak tersedia. Silakan periksa koneksi API Gemini."
            }
        ]
        
    def show_ai_summary_tab_with_phases(self):
        """Menampilkan tab Hasil Ringkasan AI dengan tombol generate manual"""
        st.subheader("HASIL RINGKASAN AI")
        
        # Cek apakah semua MAE sudah tersedia
        required_mae = [
            'mae_pelvis_left', 'mae_pelvis_right',
            'mae_knee_left', 'mae_knee_right',
            'mae_hip_left', 'mae_hip_right',
            'mae_ankle_left', 'mae_ankle_right',
            'phase_indices'
        ]
        
        missing_mae = [mae for mae in required_mae if mae not in st.session_state]
        
        if missing_mae:
            st.warning("Data MAE belum lengkap: {missing_mae}")
            st.info("Sistem sedang memproses data...")
            self.reset_ai_summary_session_state()
            return
    
        # INISIALISASI: Pastikan current_patient_key ada di session state
        if 'current_patient_key' not in st.session_state:
            st.session_state.current_patient_key = f"patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        current_patient_key = st.session_state.current_patient_key
        
        # Ambil data upper bound dan lower bound dari filtered_df yang disimpan
        if 'filtered_normal_df' not in st.session_state:
            st.info("Untuk menggunakan fitur AI, silakan upload data normal terlebih dahulu di menu 'Input Baseline Data Gait'")
            if st.button("🔄 Refresh", key="refresh_normal_data"):
                st.rerun()
            return
        
        filtered_df = st.session_state.filtered_normal_df

        if filtered_df.empty:
            st.warning("Data normal kosong. Silakan cek filter yang Anda gunakan.")
            return
        
        # Hitung upper bound dan lower bound
        bounds_data = self.calculate_bounds_from_normal_data(filtered_df)
        
        # Tampilkan tabel MAE
        st.markdown("### Ringkasan MAE Keseluruhan")
        mae_overall_data = []
        # Pelvis
        pelvis_left = st.session_state.mae_pelvis_left
        pelvis_right = st.session_state.mae_pelvis_right
        pelvis_avg = (pelvis_left + pelvis_right) / 2
        mae_overall_data.append({
            'Joint': 'Pelvis',
            'Kiri (°)': f"{pelvis_left:.2f}",
            'Kanan (°)': f"{pelvis_right:.2f}",
            'Rata-rata (°)': f"{pelvis_avg:.2f}"
        })
        
        # Knee
        knee_left = st.session_state.mae_knee_left
        knee_right = st.session_state.mae_knee_right
        knee_avg = (knee_left + knee_right) / 2
        mae_overall_data.append({
            'Joint': 'Knee',
            'Kiri (°)': f"{knee_left:.2f}",
            'Kanan (°)': f"{knee_right:.2f}",
            'Rata-rata (°)': f"{knee_avg:.2f}"
        })
        
        # Hip
        hip_left = st.session_state.mae_hip_left
        hip_right = st.session_state.mae_hip_right
        hip_avg = (hip_left + hip_right) / 2
        mae_overall_data.append({
            'Joint': 'Hip',
            'Kiri (°)': f"{hip_left:.2f}",
            'Kanan (°)': f"{hip_right:.2f}",
            'Rata-rata (°)': f"{hip_avg:.2f}"
        })
        
        # Ankle
        ankle_left = st.session_state.mae_ankle_left
        ankle_right = st.session_state.mae_ankle_right
        ankle_avg = (ankle_left + ankle_right) / 2
        mae_overall_data.append({
            'Joint': 'Ankle',
            'Kiri (°)': f"{ankle_left:.2f}",
            'Kanan (°)': f"{ankle_right:.2f}",
            'Rata-rata (°)': f"{ankle_avg:.2f}"
        })
        
        mae_overall_df = pd.DataFrame(mae_overall_data)
        st.dataframe(mae_overall_df, use_container_width=True, hide_index=True)
        
        # ===== TABEL MAE PER FASE GAIT =====
        st.markdown("### Detail MAE per Fase Gait")
        # Urutan fase gait
        phases_order = [
            'Initial Contact (0-2%)',
            'Loading Response (2-10%)',
            'Mid-Stance (10-30%)',
            'Terminal Stance (30-50%)',
            'Pre-Swing (50-60%)',
            'Initial Swing (60-73%)',
            'Mid-Swing (73-87%)',
            'Terminal Swing (87-100%)'
        ]
        
        # Buat data untuk tabel per fase
        mae_phases_data = []
        
        for phase in phases_order:
            row_data = {
                'Fase Gait': phase,
                'Pelvis Kiri (°)': f"{st.session_state.mae_pelvis_left_phases.get(phase, 0):.2f}",
                'Pelvis Kanan (°)': f"{st.session_state.mae_pelvis_right_phases.get(phase, 0):.2f}",
                'Knee Kiri (°)': f"{st.session_state.mae_knee_left_phases.get(phase, 0):.2f}",
                'Knee Kanan (°)': f"{st.session_state.mae_knee_right_phases.get(phase, 0):.2f}",
                'Hip Kiri (°)': f"{st.session_state.mae_hip_left_phases.get(phase, 0):.2f}",
                'Hip Kanan (°)': f"{st.session_state.mae_hip_right_phases.get(phase, 0):.2f}",
                'Ankle Kiri (°)': f"{st.session_state.mae_ankle_left_phases.get(phase, 0):.2f}",
                'Ankle Kanan (°)': f"{st.session_state.mae_ankle_right_phases.get(phase, 0):.2f}"
            }
            mae_phases_data.append(row_data)
        
        mae_phases_df = pd.DataFrame(mae_phases_data)
        st.dataframe(mae_phases_df, use_container_width=True, hide_index=True)
       
        # ===== TOMBOL GENERATE AI =====
        patient_saved_key = f'saved_summary_content_{current_patient_key}'
        patient_ai_generated_key = f'ai_summaries_generated_{current_patient_key}'
        
        # Jika sudah ada hasil yang disimpan, tampilkan dan beri opsi generate ulang
        if patient_saved_key in st.session_state and st.session_state[patient_saved_key]:
            st.markdown("### Hasil Terbaik yang Telah Disimpan")
            st.info(st.session_state[patient_saved_key])
            st.markdown("---")
            
            # Tombol untuk generate ulang
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 Generate Ringkasan Baru", use_container_width=True, type="secondary"):
                    # Hapus semua data AI untuk pasien ini
                    if patient_saved_key in st.session_state:
                        del st.session_state[patient_saved_key]
                    if patient_ai_generated_key in st.session_state:
                        del st.session_state[patient_ai_generated_key]
                    if f'summaries_a_{current_patient_key}' in st.session_state:
                        del st.session_state[f'summaries_a_{current_patient_key}']
                    if f'summaries_b_{current_patient_key}' in st.session_state:
                        del st.session_state[f'summaries_b_{current_patient_key}']
                    if f'selected_summary_label_{current_patient_key}' in st.session_state:
                        del st.session_state[f'selected_summary_label_{current_patient_key}']
                    if f'selected_summary_content_{current_patient_key}' in st.session_state:
                        del st.session_state[f'selected_summary_content_{current_patient_key}']
                    st.rerun()
            return  # Hentikan eksekusi, hanya tampilkan hasil yang disimpan
        
        # Jika belum ada hasil AI yang digenerate, tampilkan tombol generate
        if patient_ai_generated_key not in st.session_state:
            st.markdown("### Generate Ringkasan AI")
            st.info("Klik tombol di bawah untuk menghasilkan ringkasan AI berdasarkan data MAE dan batas normal (Upper/Lower Bound) yang telah dihitung.")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                generate_button = st.button("Generate Ringkasan AI", use_container_width=True, type="primary")
            
            if not generate_button:
                st.stop()  # Hentikan eksekusi sampai tombol ditekan
            
            # Jika tombol ditekan, generate summaries
            if generate_button:
                if gemini_model is None:
                    st.error("Fitur AI tidak tersedia karena API key Gemini tidak dikonfigurasi.")
                    return
                
                # Hitung overall MAE
                all_mae_values = [
                    st.session_state.mae_pelvis_left,
                    st.session_state.mae_pelvis_right,
                    st.session_state.mae_knee_left,
                    st.session_state.mae_knee_right,
                    st.session_state.mae_hip_left,
                    st.session_state.mae_hip_right,
                    st.session_state.mae_ankle_left,
                    st.session_state.mae_ankle_right]
                overall_mae = np.mean(all_mae_values)

                mae_summary = f"""
                MAE KESELURUHAN (Rata-rata seluruh siklus gait 0-100%):
                - Pelvis Kiri: {st.session_state.mae_pelvis_left:.2f}°, Pelvis Kanan: {st.session_state.mae_pelvis_right:.2f}°, Rata-rata: {(st.session_state.mae_pelvis_left + st.session_state.mae_pelvis_right)/2:.2f}°
                - Knee Kiri: {st.session_state.mae_knee_left:.2f}°, Knee Kanan: {st.session_state.mae_knee_right:.2f}°, Rata-rata: {(st.session_state.mae_knee_left + st.session_state.mae_knee_right)/2:.2f}°
                - Hip Kiri: {st.session_state.mae_hip_left:.2f}°, Hip Kanan: {st.session_state.mae_hip_right:.2f}°, Rata-rata: {(st.session_state.mae_hip_left + st.session_state.mae_hip_right)/2:.2f}°
                - Ankle Kiri: {st.session_state.mae_ankle_left:.2f}°, Ankle Kanan: {st.session_state.mae_ankle_right:.2f}°, Rata-rata: {(st.session_state.mae_ankle_left + st.session_state.mae_ankle_right)/2:.2f}°
                Rata-rata Keseluruhan Semua Sendi: {overall_mae:.2f}°
                """
                
                # Siapkan data MAE per fase untuk prompt
                mae_phases_summary = "\nMAE PER FASE GAIT:\n"
                
                for phase in phases_order:
                    mae_phases_summary += f"\n{phase}:\n"
                    mae_phases_summary += f"  - Pelvis Kiri: {st.session_state.mae_pelvis_left_phases.get(phase, 0):.2f}°, Pelvis Kanan: {st.session_state.mae_pelvis_right_phases.get(phase, 0):.2f}°\n"
                    mae_phases_summary += f"  - Knee Kiri: {st.session_state.mae_knee_left_phases.get(phase, 0):.2f}°, Knee Kanan: {st.session_state.mae_knee_right_phases.get(phase, 0):.2f}°\n"
                    mae_phases_summary += f"  - Hip Kiri: {st.session_state.mae_hip_left_phases.get(phase, 0):.2f}°, Hip Kanan: {st.session_state.mae_hip_right_phases.get(phase, 0):.2f}°\n"
                    mae_phases_summary += f"  - Ankle Kiri: {st.session_state.mae_ankle_left_phases.get(phase, 0):.2f}°, Ankle Kanan: {st.session_state.mae_ankle_right_phases.get(phase, 0):.2f}°\n"
                
                # Siapkan data bounds
                bounds_summary = "\nBATAS NORMAL (Upper Bound dan Lower Bound):\n"
                joints_for_bounds = [
                    ('LPelvisAngles_X', 'Pelvis Kiri'),
                    ('RPelvisAngles_X', 'Pelvis Kanan'),
                    ('LKneeAngles_X', 'Knee Kiri'),
                    ('RKneeAngles_X', 'Knee Kanan'),
                    ('LHipAngles_X', 'Hip Kiri'),
                    ('RHipAngles_X', 'Hip Kanan'),
                    ('LAnkleAngles_X', 'Ankle Kiri'),
                    ('RAnkleAngles_X', 'Ankle Kanan')
                ]
                
                for key, name in joints_for_bounds:
                    bound = bounds_data.get(key, {'upper': 0, 'lower': 0})
                    bounds_summary += f"- {name}: Upper={bound['upper']:.2f}°, Lower={bound['lower']:.2f}°\n"
                
                # Gabungkan semua data
                full_data = mae_summary + mae_phases_summary + bounds_summary
                        
                
                # PROMPT A (TIDAK DIUBAH)
                prompt_a = f"""
                Anda adalah seorang fisioterapis klinis dan ahli biomekanika yang berpengalaman dalam analisis gait. 
                Anda memahami konsep gait cycle, joint kinematics, serta evaluasi parameter gait berdasarkan rentang 
                nilai normal (upper bound dan lower bound) dan nilai Mean Absolute Error (MAE).         
                
                DATA ANALISIS GAIT:
                {full_data}
                
                INSTRUKSI:
                Lakukan analisis secara objektif, profesional, dan berbasis data yang diberikan.
                a. Interpretasikan nilai MAE sebagai ukuran rata-rata deviasi parameter gait pasien terhadap nilai gait normal.
                b. Identifikasi fase gait mana yang memiliki MAE tertinggi untuk setiap sendi dan setiap fase.
                c. Bandingkan hasil antara sisi kanan dan kiri untuk setiap sendi dan setiap fase.
                
                Gunakan bahasa medis yang jelas, sistematis, dan mudah dipahami oleh tenaga kesehatan.
                Analisis bersifat deskriptif dan tidak mencakup penetapan diagnosis medis.
                Hindari spekulasi atau asumsi di luar data yang tersedia. 
    
                Buat 3 variasi ringkasan berdasarkan data diatas:
                VARIASI 1: Analisis singkat dan padat (2-3 paragraf)
                VARIASI 2: Analisis terstruktur dengan sub-bagian per sendi dan per fase
                VARIASI 3: Analisis berfokus pada rekomendasi klinis
    
                Pisahkan setiap variasi dengan "=== VARIASI X ==="
                """
                
                # PROMPT B
                prompt_b = f"""
                Buat laporan hasil gait analysis berdasarkan data berikut:
                
                DATA ANALISIS GAIT:
                {full_data}
                
                INSTRUKSI:
                Struktur laporan hasil mengikuti format berikut:
                a. HASIL PEMERIKSAAN
                    - Sajikan nilai Mean Absolute Error (MAE) dalam bentuk poin untuk setiap sendi utama.
                    - Soroti nilai MAE tertinggi dan terendah dari setiap sendi.
                b. INTERPRETASI KLINIS
                    - Jelaskan makna klinis dari posisi parameter gait terhadap rentang nilai normal.
                    - Interpretasikan nilai MAE sebagai tingkat deviasi rata-rata terhadap gait normal.
                    - Hubungkan temuan dengan fase-fase gait cycle
                    - Bandingkan hasil antara sisi kanan dan kiri berdasarkan data yang tersedia.
                c. REKOMENDASI
                    - Saran klinis atau intervensi umum berdasarkan temuan
                    - Target perbaikan gait yang diharapkan        
                
                Berikan 3 variasi laporan berdasarkan data diatas:
                
                VARIASI 1: Laporan dengan fokus pada temuan utama
                VARIASI 2: Laporan klinis lengkap dengan detail per sendi dan fase gait
                VARIASI 3: Laporan dengan tambahan pada rekomendasi terapi
                
                Gunakan hanya data yang diberikan dan jangan menambahkan asumsi di luar data.
                Pisahkan setiap variasi dengan "=== VARIASI X ==="
                """
                
                # Generate summaries
                summaries_a = []
                summaries_b = []
                
                try:
                    with st.spinner("Membuat ringkasan Prompt A..."):
                        response_a = gemini_model.generate_content(prompt_a)
                        if response_a.text:
                            summaries_a = self.parse_ai_response_dropdown(response_a.text, "A")
                        else:
                            summaries_a = self.create_default_summaries("A")
                    
                    with st.spinner("Membuat ringkasan Prompt B..."):
                        response_b = gemini_model.generate_content(prompt_b)
                        if response_b.text:
                            summaries_b = self.parse_ai_response_dropdown(response_b.text, "B")
                        else:
                            summaries_b = self.create_default_summaries("B")
                            
                except Exception as e:
                    st.error(f"Error generating AI summaries: {e}")
                    summaries_a = self.create_default_summaries("A")
                    summaries_b = self.create_default_summaries("B")
                
                # Simpan ke session state
                st.session_state[f'summaries_a_{current_patient_key}'] = summaries_a
                st.session_state[f'summaries_b_{current_patient_key}'] = summaries_b
                st.session_state[patient_ai_generated_key] = True
                
                # Inisialisasi selected summary
                if f'selected_summary_label_{current_patient_key}' not in st.session_state:
                    if summaries_a:
                        st.session_state[f'selected_summary_label_{current_patient_key}'] = summaries_a[0]['label']
                        st.session_state[f'selected_summary_content_{current_patient_key}'] = summaries_a[0]['value']
                    elif summaries_b:
                        st.session_state[f'selected_summary_label_{current_patient_key}'] = summaries_b[0]['label']
                        st.session_state[f'selected_summary_content_{current_patient_key}'] = summaries_b[0]['value']
                st.rerun()
        
        # Jika sudah digenerate, tampilkan hasilnya
        else:
            # Ambil summaries dari session state
            summaries_a = st.session_state.get(f'summaries_a_{current_patient_key}', [])
            summaries_b = st.session_state.get(f'summaries_b_{current_patient_key}', [])
            
            # Tampilkan dalam 2 kolom
            st.markdown("---")
            st.markdown("## Hasil Prompt")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Hasil Prompt A (Analisis Klinis)")
                
                if summaries_a:
                    for i, summary in enumerate(summaries_a, 1):
                        with st.container():
                            st.markdown(f"#### Variasi {i}")
                            st.markdown(summary['value'])
                            if i < len(summaries_a):
                                st.markdown("---")
                else:
                    st.info("Tidak ada ringkasan yang dihasilkan")
            
            with col2:
                st.markdown("### Hasil Prompt B (Laporan Hasil)")
                
                if summaries_b:
                    for i, summary in enumerate(summaries_b, 1):
                        with st.container():
                            st.markdown(f"#### Variasi {i}")
                            st.markdown(summary['value'])
                            if i < len(summaries_b):
                                st.markdown("---")
                else:
                    st.info("Tidak ada ringkasan yang dihasilkan")
            
            # Dropdown untuk memilih hasil terbaik
            st.markdown("---")
            
            all_summaries = summaries_a + summaries_b
            dropdown_options = [summary["label"] for summary in all_summaries]
            
            with st.container():
                col_left, col_center, col_right = st.columns([1, 2, 1])
                
                with col_center:
                    st.markdown("### Pilih Hasil Terbaik")
                    
                    def on_dropdown_change():
                        selected_label = st.session_state.best_summary_dropdown
                        selected_content = next((s["value"] for s in all_summaries if s["label"] == selected_label), "")
                        st.session_state[f'selected_summary_label_{current_patient_key}'] = selected_label
                        st.session_state[f'selected_summary_content_{current_patient_key}'] = selected_content
                    
                    selected_label_key = f'selected_summary_label_{current_patient_key}'
                    current_index = 0
                    if selected_label_key in st.session_state and st.session_state[selected_label_key] in dropdown_options:
                        current_index = dropdown_options.index(st.session_state[selected_label_key])
                    
                    selected_label = st.selectbox(
                        "Pilih varian terbaik:",
                        options=dropdown_options,
                        index=current_index,
                        label_visibility="collapsed",
                        key="best_summary_dropdown",
                        on_change=on_dropdown_change
                    )
                    
                    selected_content_key = f'selected_summary_content_{current_patient_key}'
                    if selected_content_key in st.session_state and st.session_state[selected_content_key]:
                        st.markdown("** Konten yang dipilih:**")
                        st.info(st.session_state[selected_content_key])
                    
                    # Tombol simpan
                    if st.button("Simpan Hasil Terpilih", use_container_width=True, type="primary", key="save_selected"):
                        if selected_label_key in st.session_state and st.session_state[selected_label_key]:
                            parts = st.session_state[selected_label_key].split(" - ")
                            if len(parts) == 2:
                                prompt_type = parts[0].replace("Prompt ", "")
                                variant = parts[1].replace("Varian ", "")
                                
                                selected_content = st.session_state[selected_content_key]
                                
                                if selected_content:
                                    # Siapkan mae_data dengan bounds untuk disimpan
                                    mae_data_for_save = []
                                    for phase in phases_order:
                                        mae_data_for_save.append({
                                            'phase': phase,
                                            'pelvis_left': st.session_state.mae_pelvis_left_phases.get(phase, 0),
                                            'pelvis_right': st.session_state.mae_pelvis_right_phases.get(phase, 0),
                                            'knee_left': st.session_state.mae_knee_left_phases.get(phase, 0),
                                            'knee_right': st.session_state.mae_knee_right_phases.get(phase, 0),
                                            'hip_left': st.session_state.mae_hip_left_phases.get(phase, 0),
                                            'hip_right': st.session_state.mae_hip_right_phases.get(phase, 0),
                                            'ankle_left': st.session_state.mae_ankle_left_phases.get(phase, 0),
                                            'ankle_right': st.session_state.mae_ankle_right_phases.get(phase, 0)
                                            })
                                    
                                    success = self.save_selected_summary_with_phases(
                                        prompt_type=prompt_type,
                                        variant=variant,
                                        content=selected_content,
                                        mae_overall={
                                            'pelvis_left': st.session_state.mae_pelvis_left,
                                            'pelvis_right': st.session_state.mae_pelvis_right,
                                            'knee_left': st.session_state.mae_knee_left,
                                            'knee_right': st.session_state.mae_knee_right,
                                            'hip_left': st.session_state.mae_hip_left,
                                            'hip_right': st.session_state.mae_hip_right,
                                            'ankle_left': st.session_state.mae_ankle_left,
                                            'ankle_right': st.session_state.mae_ankle_right},
                                        mae_phases=mae_data_for_save,
                                        bounds_data=bounds_data)
                                    
                                    if success:
                                        st.session_state[patient_saved_key] = selected_content
                                        st.success(f"Hasil terpilih ({st.session_state[selected_label_key]}) berhasil disimpan!")
                                        st.rerun()
                                    else:
                                        st.error("Gagal menyimpan ke database")
                                else:
                                    st.error("Tidak dapat menemukan konten yang dipilih")
                            else:
                                st.error("Format label tidak valid")
                        else:
                            st.warning("Silakan pilih varian terlebih dahulu")

    def save_selected_summary_with_phases(self, prompt_type, variant, content, mae_overall, mae_phases, bounds_data):
        """Simpan ringkasan yang dipilih ke database dengan data MAE per fase"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']

            pasien_id = st.session_state.get('current_pasien_id', None)
            tanggal_pemeriksaan = st.session_state.get('current_tanggal_pemeriksaan', None)
            
            # Data yang akan disimpan
            summary_data = {
                'timestamp': datetime.now(),
                'dokter_id': st.session_state.get('terapis_user_id'),
                'dokter_nama': st.session_state.get('terapis_nama'),
                'pasien_id': pasien_id,
                'tanggal_pemeriksaan': tanggal_pemeriksaan,
                'prompt_type': prompt_type,
                'variant': variant,
                'content': content,
                'mae_overall': mae_overall,
                'mae_phases': mae_phases,
                'bounds_data': bounds_data,
                'is_best_selected': True
            }
            
            # Simpan ke database
            result = collection.insert_one(summary_data)
            
            return True
            
        except Exception as e:
            st.error(f"Error menyimpan ringkasan: {e}")
            return False

    def calculate_bounds_from_normal_data(self, filtered_df):
        """Menghitung upper bound dan lower bound dari data normal"""
        bounds = {}
        
        # Daftar joint yang akan dihitung bounds-nya
        joints = {
            'LPelvisAngles_X': [],
            'RPelvisAngles_X': [],
            'LHipAngles_X': [],
            'RHipAngles_X': [],
            'LKneeAngles_X': [],
            'RKneeAngles_X': [],
            'LAnkleAngles_X': [],
            'RAnkleAngles_X': []
        }
        
        for joint in joints.keys():
            if joint in filtered_df.columns:
                # Ambil semua nilai untuk joint ini (setiap baris adalah list of 101 values)
                joint_values = pd.DataFrame(filtered_df[joint].tolist())
                
                # Hitung mean dan std untuk setiap %cycle
                mean_values = joint_values.mean(axis=0).values
                std_values = joint_values.std(axis=0).values
                
                # Upper bound = mean + 2*std (95% confidence interval)
                # Lower bound = mean - 2*std
                upper_bound = mean_values + (2 * std_values)
                lower_bound = mean_values - (2 * std_values)
                
                bounds[joint] = {
                    'upper': np.mean(upper_bound),  # Rata-rata upper bound sepanjang gait cycle
                    'lower': np.mean(lower_bound),  # Rata-rata lower bound sepanjang gait cycle
                    'upper_by_cycle': upper_bound.tolist(),
                    'lower_by_cycle': lower_bound.tolist(),
                    'mean_by_cycle': mean_values.tolist()
                }
        
        return bounds
                            
    def save_selected_summary_with_bounds(self, prompt_type, variant, content, mae_data, bounds_data):
    # """Simpan ringkasan yang dipilih ke database dengan bounds data"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']
            
            # Data yang akan disimpan
            summary_data = {
                'timestamp': datetime.now(),
                'terapis_user_id': st.session_state.get('terapis_user_id'),
                'terapis_nama': st.session_state.get('terapis_nama'),
                'prompt_type': prompt_type,
                'variant': variant,
                'content': content,
                'mae_data': mae_data,
                'bounds_data': bounds_data,
                'is_best_selected': True
            }
            
            # Simpan ke database
            result = collection.insert_one(summary_data)
            
            return True
            
        except Exception as e:
            st.error(f"Error menyimpan ringkasan: {e}")
            return False
                        
    def reset_ai_summary_session_state(self):
        """Reset semua session state terkait AI summary untuk pasien baru"""
        # Reset semua kunci yang berkaitan dengan AI summary
        keys_to_reset = [
            'ai_summaries_generated',
            'summaries_a',
            'summaries_b',
            'selected_summary_label',
            'selected_summary_content',
            'saved_summary_content',
            'current_patient_key'
        ]
        
        # Juga reset semua kunci yang mengandung patient_key lama
        import re
        pattern = re.compile(r'.*patient_.*')
        for key in list(st.session_state.keys()):
            if pattern.match(key):
                del st.session_state[key]
        
        # Reset kunci utama
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        print("Session state AI summary telah direset untuk pasien baru")

    def parse_ai_response_dropdown(self, response_text, prompt_type):
        """Parse AI response untuk format dropdown"""
        summaries = []
        
        # Split berdasarkan varian
        variasi_patterns  = [
            "=== VARIASI 1 ===",
            "=== VARIASI 2 ===", 
            "=== VARIASI 3 ===",
            "VARIASI 1:",
            "VARIASI 2:",
            "VARIASI 3:"
        ]
        
        # Cari semua varian
        for i in range(1, 4):
            variasi_text = ""
            
            # Cari pattern untuk varian i
            patterns = [
                f"=== VARIASI {i} ===",
                f"VARIASI {i}:",
                f"Variasi {i}:",
                f"{i}."
            ]
            
            for pattern in patterns:
                if pattern in response_text:
                    # Ambil teks setelah pattern
                    start_idx = response_text.find(pattern) + len(pattern)
                    
                    # Cari akhir varian (pattern berikutnya atau akhir teks)
                    end_idx = len(response_text)
                    for j in range(i+1, 4):
                        next_patterns = [
                            f"=== VARIASI {j} ===",
                            f"VARIASI {j}:",
                            f"Variasi {j}:",
                            f"{j}."
                        ]
                        for next_pattern in next_patterns:
                            if next_pattern in response_text[start_idx:]:
                                pattern_end_idx = response_text.find(next_pattern, start_idx)
                                if pattern_end_idx < end_idx:
                                    end_idx = pattern_end_idx
                                    break
                    
                    variasi_text = response_text[start_idx:end_idx].strip()
                    break
            
            # Jika tidak ditemukan dengan pattern, coba split dengan nomor
            if not variasi_text and i == 1:
                # Fallback: split berdasarkan nomor
                parts = response_text.split(f"{i}.")
                if len(parts) > 1:
                    variasi_text = parts[1].strip()
                    if "2." in variasi_text:
                        variasi_text = variasi_text.split("2.")[0].strip()
            
            if variasi_text:
                summaries.append({
                    "label": f"Prompt {prompt_type} - Variasi {i}",
                    "value": variasi_text
                })
        
        # Jika masih kosong, buat default
        if not summaries:
            for i in range(1, 4):
                summaries.append({
                    "label": f"Prompt {prompt_type} - Variasi {i}",
                    "value": f"Ringkasan {prompt_type} - Variasi {i} tidak tersedia"
                })
        
        return summaries

    def save_selected_summary_simple(self, prompt_type, variant, content, mae_data):
        """Simpan ringkasan yang dipilih ke database"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']
            
            # Data yang akan disimpan
            summary_data = {
                'timestamp': datetime.now(),
                'terapis_username': st.session_state.get('terapis_username'),
                'prompt_type': prompt_type,
                'variant': variant,
                'content': content,
                'mae_data': mae_data,
                'is_best_selected': True  # Tandai sebagai hasil terbaik yang dipilih
            }
            
            # Simpan ke database
            result = collection.insert_one(summary_data)
            
            return True
            
        except Exception as e:
            st.error(f"Error menyimpan ringkasan: {e}")
            return False

    def create_pelvis_figure(self, data, title, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"], 
            mode='lines',
            name=f'Average {title}<br>(Normal Subjects)',
            line=dict(color=color),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"])]
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["your left pelvis" if "your left pelvis" in data.columns else "your right pelvis"], 
            mode='lines',
            name='Patient',
            line=dict(color='black')
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"] + data["std_Lpelvis" if "std_Lpelvis" in data.columns else "std_Rpelvis"], 
            mode='lines',
            name='Upper Bound',
            line=dict(color=color, width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"] - data["std_Lpelvis" if "std_Lpelvis" in data.columns else "std_Rpelvis"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color=color, width=0),
            fill='tonexty',
            fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
            showlegend=True,
            hoverinfo='text',
            text=[f"Upper Bound: {cycle}%, {valup:.2f}°<br>Lower Bound: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"] - data["std_Lpelvis" if "std_Lpelvis" in data.columns else "std_Rpelvis"], data["Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"] + data["std_Lpelvis" if "std_Lpelvis" in data.columns else "std_Rpelvis"])]
        ))
        fig.update_layout(
            title=title,
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )
        return fig

    def create_joint_figure(self, data, title, color):
        mean_col = [col for col in data.columns if col.startswith('Mean_')][0]
        std_col = [col for col in data.columns if col.startswith('std_')][0]
        patient_col = [col for col in data.columns if col.startswith('your ')][0]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data[mean_col], 
            mode='lines',
            name=f'Average {title}<br>(Normal Subjects)',
            line=dict(color=color),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data[mean_col])]
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data[patient_col], 
            mode='lines',
            name='Patient',
            line=dict(color='black')
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data[mean_col] + data[std_col], 
            mode='lines',
            name='Upper Bound',
            line=dict(color=color, width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data[mean_col] - data[std_col], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color=color, width=0),
            fill='tonexty',
            fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound: {cycle}%, {valup:.2f}°<br>Lower Bound: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data[mean_col] - data[std_col], data[mean_col] + data[std_col])]
        ))
        fig.update_layout(
            title=title,
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )
        return fig

    def show_normal_dashboard(self):
        # st.markdown("---")
        
        # Tampilkan grafik normal tanpa data pasien
        px.defaults.template = 'plotly_dark'
        px.defaults.color_continuous_scale = 'reds'
        
        # Koneksi ke MongoDB
        client = get_mongo_client()
        db = client['GaitDB']
        collection = db['gait_data']

        # Membaca data dari MongoDB
        cursor = collection.find().limit(100)
        data = list(cursor)
        if len(data) == 0:
            st.error("Database Normal Belum Ada. Silahkan Upload Data Normal pada Menu 'Input Baseline Data Gait'")
            st.info("📝 Untuk melihat dashboard analisis gait, Anda perlu mengupload data subjek normal terlebih dahulu.")
            return
            
        # Normalisasi data untuk DataFrame
        df = pd.json_normalize(data)
        # Mengubah nama kolom untuk mempermudah akses
        df.columns = df.columns.str.replace('Trial Information.', '')
        df.columns = df.columns.str.replace('Subject Parameters.', '')
        df.columns = df.columns.str.replace('Body Measurements.', '')
        df.columns = df.columns.str.replace('Norm Kinematics.', '')

        # ====== FILTER DI ATAS ======
        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### Filter Data")

        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            # Filter usia
            min_age = df['Age'].min()
            max_age = df['Age'].max()
            age_range = st.slider(
                'Filter by Age Range:',
                min_value=min_age,
                max_value=max_age,
                value=(min_age, max_age)
            )

        with col2:
            # filter BMI
            bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
            classbmi = st.selectbox(label="BMI Classification", options=bmi_options)

        with col3:
            # filter gender
            gender_mapping = {
                "L": "Pria",
                "P": "Wanita"
            }
            df["Gender"] = df["Gender"].map(gender_mapping)
            gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
            gender = st.selectbox(label="Gender", options=gender_options)

        st.markdown("</div>", unsafe_allow_html=True)
        # st.markdown("---")
            
        # Apply filters
        filtered_df = df[(df['Age'] >= age_range[0]) & (df['Age'] <= age_range[1])]
        if classbmi != "All BMI Classification":
            filtered_df = filtered_df[filtered_df['BMI Classification'] == classbmi]
        if gender != "All Gender":
            filtered_df = filtered_df[filtered_df["Gender"] == gender]
            
        if filtered_df.empty:
            st.error(f"There is no data with gender {gender} classified as {classbmi}.")
        else:
            st.markdown(f"**Total Records:** {len(filtered_df)}")

            st.session_state.filtered_normal_df = filtered_df
            # Tampilkan grafik normal saja (tanpa data pasien)
            self.show_normal_charts_only(filtered_df)
            
    def show_normal_charts_only(self, filtered_df):
        # Pelvis
        percentage_cycle = pd.DataFrame(filtered_df['Percentage of Gait Cycle'].tolist())
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())

        percentage_cycle.columns = [f"%cycle_{i}" for i in range(percentage_cycle.shape[1])]
        l_pelvis_angles.columns = [f"L_Pelvis_{i}" for i in range(l_pelvis_angles.shape[1])]
        r_pelvis_angles.columns = [f"R_Pelvis_{i}" for i in range(r_pelvis_angles.shape[1])]

        mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
        std_l_pelvis = l_pelvis_angles.std(axis=0)/np.sqrt(l_pelvis_angles.shape[0])
        mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
        std_r_pelvis = r_pelvis_angles.std(axis=0)/np.sqrt(r_pelvis_angles.shape[0])

        std_l_pelvis = std_l_pelvis.values if isinstance(std_l_pelvis, pd.Series) else std_l_pelvis
        std_r_pelvis = std_r_pelvis.values if isinstance(std_r_pelvis, pd.Series) else std_r_pelvis

        lpelvis = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Lpelvis': mean_l_pelvis,
            'std_Lpelvis': std_l_pelvis
        })

        rpelvis = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Rpelvis': mean_r_pelvis,
            'std_Rpelvis': std_r_pelvis
        })
        
        ## Create the figure for Pelvis
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=lpelvis["%cycle"], 
            y=lpelvis["Mean_Lpelvis"], 
            mode='lines',
            name='Average Left Pelvis<br>(Normal Subjects)',
            line=dict(color='orange'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lpelvis["%cycle"], lpelvis["Mean_Lpelvis"])]
        ))
        fig1.add_trace(go.Scatter(
            x=lpelvis["%cycle"], 
            y=lpelvis["Mean_Lpelvis"] + lpelvis["std_Lpelvis"], 
            mode='lines',
            name='Upper Bound (Left)',
            line=dict(color='orange', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig1.add_trace(go.Scatter(
            x=lpelvis["%cycle"], 
            y=lpelvis["Mean_Lpelvis"] - lpelvis["std_Lpelvis"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='orange', width=0),
            fill='tonexty',
            fillcolor='rgba(255, 165, 0, 0.2)',
            showlegend=True,
            hoverinfo='text',
            text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lpelvis["%cycle"], lpelvis["Mean_Lpelvis"] - lpelvis["std_Lpelvis"], lpelvis["Mean_Lpelvis"] + lpelvis["std_Lpelvis"])]
        ))
        fig1.update_layout(
            title="Left Pelvis",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=rpelvis["%cycle"], 
            y=rpelvis["Mean_Rpelvis"], 
            mode='lines',
            name='Average Right Pelvis<br>(Normal Subjects)',
            line=dict(color='dark blue'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rpelvis["%cycle"], rpelvis["Mean_Rpelvis"])]
        ))
        fig2.add_trace(go.Scatter(
            x=rpelvis["%cycle"], 
            y=rpelvis["Mean_Rpelvis"] + rpelvis["std_Rpelvis"], 
            mode='lines',
            name='Upper Bound (Right)',
            line=dict(color='dark blue', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig2.add_trace(go.Scatter(
            x=rpelvis["%cycle"], 
            y=rpelvis["Mean_Rpelvis"] - rpelvis["std_Rpelvis"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='dark blue', width=0),
            fill='tonexty',
            fillcolor='rgba(0, 255, 255, 0.2)',
            showlegend=True,
            hoverinfo='text',
            text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rpelvis["%cycle"], rpelvis["Mean_Rpelvis"] - rpelvis["std_Rpelvis"], rpelvis["Mean_Rpelvis"] + rpelvis["std_Rpelvis"])]
        ))
        fig2.update_layout(
            title="Right Pelvis",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )

        # KNEE
        l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
        r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())

        l_knee_angles.columns = [f"L_Knee_{i}" for i in range(l_knee_angles.shape[1])]
        r_knee_angles.columns = [f"R_Knee_{i}" for i in range(r_knee_angles.shape[1])]

        mean_l_knee = l_knee_angles.mean(axis=0).values
        std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
        mean_r_knee = r_knee_angles.mean(axis=0).values
        std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])

        std_l_knee = std_l_knee.values if isinstance(std_l_knee, pd.Series) else std_l_knee
        std_r_knee = std_r_knee.values if isinstance(std_r_knee, pd.Series) else std_r_knee

        lknee = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Lknee': mean_l_knee,
            'std_Lknee': std_l_knee
        })
        
        rknee = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Rknee': mean_r_knee,
            'std_Rknee': std_r_knee
        })

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=lknee["%cycle"], 
            y=lknee["Mean_Lknee"], 
            mode='lines',
            name='Average Left Knee<br>(Normal Subjects)',
            line=dict(color='orange'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lknee["%cycle"], lknee["Mean_Lknee"])]
        ))
        fig3.add_trace(go.Scatter(
            x=lknee["%cycle"], 
            y=lknee["Mean_Lknee"] + lknee["std_Lknee"], 
            mode='lines',
            name='Upper Bound (Left)',
            line=dict(color='orange', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig3.add_trace(go.Scatter(
            x=lknee["%cycle"], 
            y=lknee["Mean_Lknee"] - lknee["std_Lknee"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='orange', width=0),
            fill='tonexty',
            fillcolor='rgba(255, 165, 0, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lknee["%cycle"], lknee["Mean_Lknee"] - lknee["std_Lknee"], lknee["Mean_Lknee"] + lknee["std_Lknee"])]
        ))
        fig3.update_layout(
            title="Left Knee",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )
        
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=rknee["%cycle"], 
            y=rknee["Mean_Rknee"], 
            mode='lines',
            name='Average Right Knee<br>(Normal Subjects)',
            line=dict(color='dark blue'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rknee["%cycle"], rknee["Mean_Rknee"])]
        ))
        fig4.add_trace(go.Scatter(
            x=rknee["%cycle"], 
            y=rknee["Mean_Rknee"] + rknee["std_Rknee"], 
            mode='lines',
            name='Upper Bound (Right)',
            line=dict(color='dark blue', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig4.add_trace(go.Scatter(
            x=rknee["%cycle"], 
            y=rknee["Mean_Rknee"] - rknee["std_Rknee"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='dark blue', width=0),
            fill='tonexty',
            fillcolor='rgba(0, 255, 255, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rknee["%cycle"], rknee["Mean_Rknee"] - rknee["std_Rknee"], rknee["Mean_Rknee"] + rknee["std_Rknee"])]
        ))
        fig4.update_layout(
            title="Right Knee",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )

        # HIP
        l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
        r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())

        l_hip_angles.columns = [f"L_Hip_{i}" for i in range(l_hip_angles.shape[1])]
        r_hip_angles.columns = [f"R_Hip_{i}" for i in range(r_hip_angles.shape[1])]

        mean_l_hip = l_hip_angles.mean(axis=0).values
        std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
        mean_r_hip = r_hip_angles.mean(axis=0).values
        std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])

        std_l_hip = std_l_hip.values if isinstance(std_l_hip, pd.Series) else std_l_hip
        std_r_hip = std_r_hip.values if isinstance(std_r_hip, pd.Series) else std_r_hip

        lhip = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Lhip': mean_l_hip,
            'std_Lhip': std_l_hip
        })
        
        rhip = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Rhip': mean_r_hip,
            'std_Rhip': std_r_hip
        })

        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(
            x=lhip["%cycle"], 
            y=lhip["Mean_Lhip"], 
            mode='lines',
            name='Average Left Hip<br>(Normal Subjects)',
            line=dict(color='orange'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lhip["%cycle"], lhip["Mean_Lhip"])]
        ))
        fig5.add_trace(go.Scatter(
            x=lhip["%cycle"], 
            y=lhip["Mean_Lhip"] + lhip["std_Lhip"], 
            mode='lines',
            name='Upper Bound (Left)',
            line=dict(color='orange', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig5.add_trace(go.Scatter(
            x=lhip["%cycle"], 
            y=lhip["Mean_Lhip"] - lhip["std_Lhip"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='orange', width=0),
            fill='tonexty',
            fillcolor='rgba(255, 165, 0, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lhip["%cycle"], lhip["Mean_Lhip"] - lhip["std_Lhip"], lhip["Mean_Lhip"] + lhip["std_Lhip"])]
        ))
        fig5.update_layout(
            title="Left Hip",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )
        
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(
            x=rhip["%cycle"], 
            y=rhip["Mean_Rhip"], 
            mode='lines',
            name='Average Right Hip<br>(Normal Subjects)',
            line=dict(color='dark blue'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rhip["%cycle"], rhip["Mean_Rhip"])]
        ))
        fig6.add_trace(go.Scatter(
            x=rhip["%cycle"], 
            y=rhip["Mean_Rhip"] + rhip["std_Rhip"], 
            mode='lines',
            name='Upper Bound (Right)',
            line=dict(color='dark blue', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig6.add_trace(go.Scatter(
            x=rhip["%cycle"], 
            y=rhip["Mean_Rhip"] - rhip["std_Rhip"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='dark blue', width=0),
            fill='tonexty',
            fillcolor='rgba(0, 255, 255, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rhip["%cycle"], rhip["Mean_Rhip"] - rhip["std_Rhip"], rhip["Mean_Rhip"] + rhip["std_Rhip"])]
        ))
        fig6.update_layout(
            title="Right Hip",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )

        # ANKLE
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())

        l_ankle_angles.columns = [f"L_Ankle_{i}" for i in range(l_ankle_angles.shape[1])]
        r_ankle_angles.columns = [f"R_Ankle_{i}" for i in range(r_ankle_angles.shape[1])]

        mean_l_ankle = l_ankle_angles.mean(axis=0).values
        std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
        mean_r_ankle = r_ankle_angles.mean(axis=0).values
        std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])

        std_l_ankle = std_l_ankle.values if isinstance(std_l_ankle, pd.Series) else std_l_ankle
        std_r_ankle = std_r_ankle.values if isinstance(std_r_ankle, pd.Series) else std_r_ankle

        lankle = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Lankle': mean_l_ankle,
            'std_Lankle': std_l_ankle
        })

        rankle = pd.DataFrame({
            "%cycle": list(range(101)),
            'Mean_Rankle': mean_r_ankle,
            'std_Rankle': std_r_ankle
        })
        
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(
            x=lankle["%cycle"], 
            y=lankle["Mean_Lankle"], 
            mode='lines',
            name='Average Left Ankle<br>(Normal Subjects)',
            line=dict(color='orange'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lankle["%cycle"], lankle["Mean_Lankle"])]
        ))
        fig7.add_trace(go.Scatter(
            x=lankle["%cycle"], 
            y=lankle["Mean_Lankle"] + lankle["std_Lankle"], 
            mode='lines',
            name='Upper Bound (Left)',
            line=dict(color='orange', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig7.add_trace(go.Scatter(
            x=lankle["%cycle"], 
            y=lankle["Mean_Lankle"] - lankle["std_Lankle"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='orange', width=0),
            fill='tonexty',
            fillcolor='rgba(255, 165, 0, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lankle["%cycle"], lankle["Mean_Lankle"] - lankle["std_Lankle"], lankle["Mean_Lankle"] + lankle["std_Lankle"])]
        ))
        fig7.update_layout(
            title="Left Ankle",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )

        fig8 = go.Figure()
        fig8.add_trace(go.Scatter(
            x=rankle["%cycle"], 
            y=rankle["Mean_Rankle"], 
            mode='lines',
            name='Average Right Ankle<br>(Normal Subjects)',
            line=dict(color='dark blue'),
            hoverinfo='text',
            text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rankle["%cycle"], rankle["Mean_Rankle"])]
        ))
        fig8.add_trace(go.Scatter(
            x=rankle["%cycle"], 
            y=rankle["Mean_Rankle"] + rankle["std_Rankle"], 
            mode='lines',
            name='Upper Bound (Right)',
            line=dict(color='dark blue', width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig8.add_trace(go.Scatter(
            x=rankle["%cycle"], 
            y=rankle["Mean_Rankle"] - rankle["std_Rankle"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color='dark blue', width=0),
            fill='tonexty',
            fillcolor='rgba(0, 255, 255, 0.2)',
            showlegend=False,
            hoverinfo='text',
            text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rankle["%cycle"], rankle["Mean_Rankle"] - rankle["std_Rankle"], rankle["Mean_Rankle"] + rankle["std_Rankle"])]
        ))
        fig8.update_layout(
            title="Right Ankle",
            xaxis_title="%Cycle",
            yaxis_title="Value",
            template="plotly_dark",
            title_x=0.5,
            hovermode="x unified"
        )

        tab1, tab2, tab3, tab4 = st.tabs(["PELVIS", "KNEE","HIP","ANKLE"])

        with tab1:
            tab1.subheader("PELVIS")
            tab1.write(
                'Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, '
                'di antara tulang pinggul, dan di atas paha.'
            )
            col1, col2 = tab1.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                
        with tab2:
            tab2.subheader("KNEE")
            tab2.write(
                'Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, '
                'berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).'
            )
            col1, col2 = tab2.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                st.plotly_chart(fig4, use_container_width=True)

        with tab3:
            tab3.subheader("HIP")
            tab3.write(
                'Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.'
            )
            col1, col2 = tab3.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
            with col2:
                st.plotly_chart(fig6, use_container_width=True)

        with tab4:
            tab4.subheader("ANKLE")
            tab4.write(
                'Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).'
            )
            col1, col2 = tab4.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
            with col2:
                st.plotly_chart(fig8, use_container_width=True)

# # Jalankan aplikasi
# if __name__ == "__main__":
#     app = TerapisPage()
#     app.run()
