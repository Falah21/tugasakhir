import io
import json
import math
import time
import traceback
from datetime import datetime
import bcrypt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import google.generativeai as genai
from css_style import load_css

# Konfigurasi Gemini API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    gemini_model = None
    st.warning("API Key Gemini tidak ditemukan. Fitur AI akan dinonaktifkan.")

# Login Form
def login_form(role_label: str = "Dokter"):
    st.markdown(load_css(), unsafe_allow_html=True)
    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    # 
    st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Login - {role_label}")
    user_id = st.text_input("NIP", max_chars=18, placeholder="Masukkan NIP anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")
    submit = st.button("Login", use_container_width=True)

    st.markdown("<p class='footer'>Dengan masuk, Anda menyetujui kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>", unsafe_allow_html=True)
    return user_id, password, submit
    
# Optimasi koneksi MongoDB
def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000)

# GaitAnalysisData untuk Data Normal
class GaitAnalysisDataNormal:
    def __init__(self, content, usia, jenis_kelamin):
        try:
            self.df = pd.read_excel(io.BytesIO(content), sheet_name=[0, 1]) # Membaca file Excel
            self.suin = self.df[0]  # Lembar pertama untuk data mentah
            self.normkin = self.df[1].iloc[:, :31]  # Lembar kedua untuk normskin
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
    
# GaitAnalysisData untuk data pemeriksaan pasien
class GaitAnalysisData:
    def __init__(self, data):
        self.df = pd.read_excel(data, sheet_name=[0, 1])
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
                "LPelvisAngles_X": self.normkin_processed["LPelvisAngles_X"].values.tolist(),
                "RPelvisAngles_X": self.normkin_processed["RPelvisAngles_X"].values.tolist(), 
                "LHipAngles_X": self.normkin_processed["LHipAngles_X"].values.tolist(),  
                "RHipAngles_X": self.normkin_processed["RHipAngles_X"].values.tolist(), 
                "LKneeAngles_X": self.normkin_processed["LKneeAngles_X"].values.tolist(), 
                "RKneeAngles_X": self.normkin_processed["RKneeAngles_X"].values.tolist(),
                "LAnkleAngles_X": self.normkin_processed["LAnkleAngles_X"].values.tolist(),  
                "RAnkleAngles_X": self.normkin_processed["RAnkleAngles_X"].values.tolist(),  
                "LFootProgressAngles_X": self.normkin_processed["LFootProgressAngles_X"].values.tolist(),  
                "RFootProgressAngles_X": self.normkin_processed["RFootProgressAngles_X"].values.tolist() 
            }
        }

    def to_dict(self):
        return {
            **self.trial_info,
            **self.subject_params,
            **self.body_measurements,
            **self.norm_kinematics
        }
        
class DokterPage:
    def _check_dokter_login(self, user_id, password):
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['users']
            
            # Cari user dengan role dokter
            dokter = collection.find_one({'user_id': user_id, 'role': 'dokter'})
            
            if dokter:
                stored_password = dokter.get('password') # Ambil password hash dari database
                # Verifikasi password dengan bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return {
                        'user_id': dokter.get('user_id'),
                        'nama_lengkap': dokter.get('nama_lengkap'),
                        'role': dokter.get('role'),
                        'tanggal_lahir': dokter.get('tanggal_lahir', ''),
                        'jenis_kelamin': dokter.get('jenis_kelamin', '')
                }
            return None
            
        except Exception as e:
            st.error(f"Error checking login: {e}")
            return None

    # Menu Utama
    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # inisialisasi session state
        if 'uploaded_patient_data' not in st.session_state:
            st.session_state.uploaded_patient_data = None
        if 'norm_kinematics_df' not in st.session_state:
            st.session_state.norm_kinematics_df = None
        if "dokter_logged_in" not in st.session_state:
            st.session_state.dokter_logged_in = False
        if "dokter_user_id" not in st.session_state:
            st.session_state.dokter_user_id = None
        if "dokter_nama" not in st.session_state:
            st.session_state.dokter_nama = None 
        if "dokter_menu" not in st.session_state:
            st.session_state.dokter_menu = "Dashboard"       

        # jika belum login → tampilkan form login
        if not st.session_state.dokter_logged_in:
            username, password, submit = login_form("Dokter")
            if submit:
                # Cek login dari database
                user_data = self._check_dokter_login(username, password)
                if user_data:
                    st.session_state.dokter_logged_in = True
                    st.session_state.dokter_user_id = user_data['user_id']
                    st.session_state.dokter_nama = user_data['nama_lengkap']
                    st.session_state.dokter_role = user_data['role']
                    st.success(f"Login berhasil! Selamat datang dr. {user_data['nama_lengkap']}")
                    st.rerun()
                else:
                    st.error("Login gagal! Username atau password salah.")
            return
        
        # Sidebar Menu
        dokter_nama = st.session_state.get('dokter_nama', 'Dokter')
        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> dr. {dokter_nama}</p>", unsafe_allow_html=True)
        st.sidebar.markdown("<p class='sidebar-subtitle'>Menu</p>", unsafe_allow_html=True)
        
        menu_list = ["Dashboard", "Input Baseline Data Gait", "Input Pemeriksaan Pasien", "Riwayat Pemeriksaan", "Logout"]
        for menu in menu_list:
            if st.sidebar.button(menu, use_container_width=True, type="primary" 
                                 if st.session_state.dokter_menu == menu else "secondary"):
                                     st.session_state.dokter_menu = menu
                                     st.rerun()

        # Navigasi Utama
        if st.session_state.dokter_menu == "Dashboard":
            self.show_dashboard()
        elif st.session_state.dokter_menu == "Input Baseline Data Gait":
            self.input_data_gait_normal()
        elif st.session_state.dokter_menu == "Input Pemeriksaan Pasien":
            self.input_data_gait_pasien()
        elif st.session_state.dokter_menu == "Riwayat Pemeriksaan":
            self.show_examination_history()
        elif st.session_state.dokter_menu == "Logout":
            self.reset_patient_data_session_state()
            st.session_state.dokter_logged_in = False
            st.session_state.dokter_user_id = None
            st.session_state.dokter_nama = None
            st.session_state.dokter_role = None
            st.session_state.dokter_menu = "Dashboard"
            st.session_state.role = None
            
            st.rerun()

    # Menu Input Baseline Data Gait
    def input_data_gait_normal(self):
        st.subheader("Input Baseline Data Gait")
        uploaded_file = st.file_uploader("Upload file data subjek gait normal (Format .xlsx)", type=["xlsx"], key="normal_upload")
        
        if uploaded_file is not None:
            col1, col2 = st.columns(2)
            with col1:
                usia = st.number_input("Masukkan Usia:", min_value=0, max_value=120, key="usia_normal")
            with col2:
                jenis_kelamin = st.selectbox("Jenis Kelamin", ["Pilih Jenis Kelamin", "L", "P"], key="gender_normal").strip().upper()

            if st.button("Proses Data Baseline", key="process_normal"):
                if usia == 0 or jenis_kelamin == "":
                    st.warning("Harap masukkan usia dan jenis kelamin sebelum memproses file.")
                elif jenis_kelamin not in ['L', 'P']:
                    st.warning("Jenis kelamin harus diisi.")
                else:
                    try:
                        content = uploaded_file.read()
                        gait_data = GaitAnalysisDataNormal(content, usia, jenis_kelamin)
                    
                        if hasattr(gait_data, 'df'):
                            data_dict = gait_data.to_dict()

                            def check_missing(data):
                                if isinstance(data, dict):
                                    return any(check_missing(v) for v in data.values())
                                elif isinstance(data, list):
                                    return any(check_missing(v) for v in data)
                                else:
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
                                    st.markdown("Ringkasan Data yang Disimpan")
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

    # Menu Input Pemeriksaan Pasien                
    def input_data_gait_pasien(self):
        st.subheader("Input Pemeriksaan Pasien")
        with st.form(key="form_pemeriksaan_pasien"):
            try:
                client = get_mongo_client()
                db = client['GaitDB']
                collection = db['users']
                
                # Ambil semua data pasien
                pasien_data = list(collection.find({'role': 'pasien'}, {'user_id': 1, 'nama_lengkap': 1}))
        
                # Buat opsi dropdown
                pasien_options = ["Pilih Data Pasien yang akan diperiksa"] + [
                    f"{pasien['user_id']} - {pasien['nama_lengkap']}" 
                    for pasien in pasien_data
                    if 'user_id' in pasien and 'nama_lengkap' in pasien]
                
            except Exception as e:
                st.error(f"Error mengambil data pasien: {e}")
                pasien_options = ["Pilih Data Pasien yang akan diperiksa"]
            
            # Dropdown untuk memilih pasien
            selected_pasien = st.selectbox("Pilih Data Pasien yang akan diperiksa", options=pasien_options, key="pasien_dropdown_form")
            # Input tanggal pemeriksaan
            tanggal = st.date_input("Tanggal Pemeriksaan", key="tanggal_form")
            col1, col2 = st.columns(2)
            with col1:
                tinggi_badan = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.1f", key="tinggi_form")
            with col2:
                berat_badan = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.1f", key="berat_form")
            
            # Upload file data GAIT pasien
            uploaded_file = st.file_uploader("Upload file data gait pasien (Format .xlsx)", type=["xlsx"], key="file_uploader_form")
            # Tombol submit di dalam form
            submit_button = st.form_submit_button("Simpan Data Pemeriksaan", type="primary", use_container_width=True)
        
        # Proses setelah submit
        if submit_button:
            if selected_pasien == "Pilih Data Pasien yang akan diperiksa":
                st.warning("Silakan pilih pasien terlebih dahulu sebelum mengupload file.")
                return
            if uploaded_file is None:
                st.warning("Silakan upload file data gait pasien terlebih dahulu.")
                return
            if tinggi_badan <= 0 or berat_badan <= 0:
                st.warning("Silakan isi tinggi badan dan berat badan dengan benar.")
                return
            
            # Hitung BMI
            if tinggi_badan > 0:
                tinggi_m = tinggi_badan / 100
                bmi = berat_badan / (tinggi_m ** 2)
                
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
            
            parts = selected_pasien.split(" - ")
            pasien_user_id = parts[0].strip()
            nama_pasien = parts[1].strip()
            
            try:              
                # Proses file dengan GaitAnalysisData
                gait_data = GaitAnalysisData(uploaded_file)
                processed_data = gait_data.to_dict()
                # Ekstrak data untuk Norm Kinematics
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
    
                st.session_state.norm_kinematics_df = pd.DataFrame(rows)
                
                # Simpan data pasien ke MongoDB
                examination_data = {
                    'pasien_id': pasien_user_id,
                    'nama_pasien': nama_pasien,
                    'dokter_id': st.session_state.get('dokter_user_id', 'unknown'),
                    'dokter_nama': st.session_state.get('dokter_nama', 'unknown'),
                    'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d"),
                    'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'tinggi_badan': tinggi_badan,
                    'berat_badan': berat_badan,
                    'bmi': bmi,
                    'bmi_classification': bmi_class,
                    'file_info': {
                        'file_name': uploaded_file.name,
                        'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                    'gait_data': processed_data,
                    'norm_kinematics': rows
                }
                
                client = get_mongo_client()
                db = client['GaitDB']
                collection = db['patient_examinations']
    
                st.session_state.current_pasien_id = pasien_user_id
                st.session_state.current_nama_pasien = nama_pasien
                st.session_state.current_tanggal_pemeriksaan = tanggal.strftime("%Y-%m-%d")
                
                current_key = f"patient_{pasien_user_id}_{tanggal.strftime('%Y-%m-%d')}"
                st.session_state.current_patient_key = current_key

                self.reset_ai_summary_for_patient_and_date(pasien_user_id, tanggal.strftime("%Y-%m-%d"))
                
                # Cek apakah sudah ada pemeriksaan
                existing_exam = collection.find_one({'pasien_id': pasien_user_id, 'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d")})
                if existing_exam:
                    st.warning(f"{nama_pasien} sudah memiliki data pemeriksaan pada tanggal {tanggal.strftime('%d %B %Y')}. Data akan diupdate.")
                    collection.update_one(
                        {'_id': existing_exam['_id']},
                        {'$set': examination_data}
                    )
                    st.success(f"Data gait pasien dengan NIK {pasien_user_id} berhasil diupdate!")
                else:
                    collection.insert_one(examination_data)
                    st.success(f"Data pasien dengan NIK {pasien_user_id} berhasil disimpan!")
            
                # Reset ringkasan AI untuk pasien baru
                # self.reset_ai_summary_session_state_except_current()
                # st.session_state.current_patient_key = f"patient_{pasien_user_id}_{tanggal.strftime('%Y%m%d_%H%M%S')}" 
            except Exception as e:
                st.error(f"Error dalam memproses file: {e}")     

    # Menu Riwayat Pemeriksaan Pasien
    def show_examination_history(self):
        st.subheader("Riwayat Pemeriksaan")
        
        # Buat 2 tab
        tab1, tab2 = st.tabs(["Riwayat Pemeriksaan", "Detail Riwayat Pasien"])
        
        with tab1:
            self._show_examination_list()
        
        with tab2:
            self.show_patient_detail_history()

    def _show_examination_list(self):
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['patient_examinations']
            
            dokter_id = st.session_state.get('dokter_user_id', None)
            dokter_nama = st.session_state.get('dokter_nama', None)
            
            if not dokter_id:
                st.error("Data dokter tidak ditemukan. Silakan login kembali.")
                return
    
            # Ambil data pemeriksaan hanya untuk dokter yang login
            examinations = list(collection.find({'dokter_id': dokter_id}).sort('upload_date', -1))
            
            if not examinations:
                st.info(f"Belum ada riwayat pemeriksaan pasien untuk Dr. {dokter_nama}.")
                return
    
            # Siapkan data untuk tabel
            table_data = []
            for exam in examinations:
                file_info = exam.get('file_info', {})
                table_data.append({
                    'Tanggal Pemeriksaan': exam.get('tanggal_pemeriksaan', 'N/A'),
                    'NIK Pasien': exam.get('pasien_id', 'N/A'),
                    'Nama Pasien': exam.get('nama_pasien', 'N/A'),
                    'Tinggi (cm)':  exam.get('tinggi_badan', 'N/A'),
                    'Berat (kg)': exam.get('berat_badan', 'N/A'),
                    'Klasifikasi BMI': exam.get('bmi_classification', 'N/A'),
                    'Dokter': dokter_nama,
                    'File Name': file_info.get('file_name', 'N/A') if isinstance(file_info, dict) else 'N/A'
                })
            
            df = pd.DataFrame(table_data)
            
            st.markdown("#### Filter Riwayat")
            col1, col2 = st.columns(2)
            
            with col1:
                filter_nik = st.text_input("Filter berdasarkan NIK Pasien:")
            with col2:
                filter_nama = st.text_input("Filter berdasarkan Nama Pasien:")
    
            filtered_df = df.copy()
            if filter_nik:
                filtered_df = filtered_df[filtered_df['NIK Pasien'].str.contains(filter_nik, case=False, na=False)]
            if filter_nama:
                filtered_df = filtered_df[filtered_df['Nama Pasien'].str.contains(filter_nama, case=False, na=False)]
            
            if not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True)
                st.markdown(f"**Menampilkan {len(filtered_df)} dari {len(df)} data pemeriksaan**")
    
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download Riwayat sebagai CSV", 
                    data=csv, 
                    file_name=f"riwayat_pemeriksaan_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv"
                )
            else:
                st.info("Tidak ada data yang sesuai dengan filter.")
    
        except Exception as e:
            st.error(f"Error mengambil data riwayat: {e}")
    
    def show_patient_detail_history(self):
        st.markdown("#### Detail Riwayat Pemeriksaan Pasien")
        
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            users_collection = db['users']
            examinations_collection = db['patient_examinations']
            
            # Ambil semua data pasien
            pasien_data = list(users_collection.find({'role': 'pasien'}, {'user_id': 1, 'nama_lengkap': 1, 'tanggal_lahir': 1, 'jenis_kelamin': 1}))
            
            if not pasien_data:
                st.info("Belum ada data pasien terdaftar.")
                return
            
            # Pilih pasien
            pasien_options = ["Silakan pilih pasien"] + [f"{p['user_id']} - {p['nama_lengkap']}" for p in pasien_data]
            selected_label = st.selectbox("Pilih Pasien", options=pasien_options, key="detail_pasien_select", index=0)
            
            if selected_label == "Silakan pilih pasien" or not selected_label:
                st.info("Silakan pilih pasien terlebih dahulu untuk melihat riwayat pemeriksaan.")
                return
                
            pasien_id = selected_label.split(" - ")[0].strip()
                
                # # Ambil data profil pasien
                # profil_pasien = next((p for p in pasien_data if p['user_id'] == pasien_id), None)
                
                # if profil_pasien:
                #     with st.expander("📋 Profil Pasien", expanded=True):
                #         col1, col2, col3 = st.columns(3)
                #         with col1:
                #             st.markdown(f"**NIK:** {profil_pasien['user_id']}")
                #             st.markdown(f"**Nama Lengkap:** {profil_pasien['nama_lengkap']}")
                #         with col2:
                #             st.markdown(f"**Tanggal Lahir:** {profil_pasien.get('tanggal_lahir', '-')}")
                #             st.markdown(f"**Jenis Kelamin:** {profil_pasien.get('jenis_kelamin', '-')}")
                #         with col3:
                #             st.markdown(f"**Usia:** {self._calculate_age(profil_pasien.get('tanggal_lahir', ''))} tahun")
                
            dokter_id = st.session_state.get('dokter_user_id')
            examinations = list(examinations_collection.find({'pasien_id': pasien_id, 'dokter_id': dokter_id}).sort('tanggal_pemeriksaan', -1))
                
            if not examinations:
                st.warning(f"Belum ada riwayat pemeriksaan untuk pasien ini.")
                return
                
            # Pilih tanggal pemeriksaan
            tanggal_options = {f"{e['tanggal_pemeriksaan']}": e for e in examinations}
            selected_tanggal_label = st.selectbox("Pilih Tanggal Pemeriksaan", options=list(tanggal_options.keys()), key="detail_tanggal_select")
                
            if selected_tanggal_label:
                selected_exam = tanggal_options[selected_tanggal_label]
                self._show_patient_examination_detail(selected_exam, pasien_id)
                    
        except Exception as e:
            st.error(f"Error mengambil data riwayat: {e}")
    
    def _show_patient_examination_detail(self, examination, pasien_id):
        
        tanggal = examination.get('tanggal_pemeriksaan')
        st.markdown(f"#### Hasil Pemeriksaan - {tanggal}")
        
        # Informasi pemeriksaan
        with st.container(border=True):
            st.markdown("##### Informasi Pasien")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Tinggi Badan:** {examination.get('tinggi_badan', '-')} cm")
                st.markdown(f"**Berat Badan:** {examination.get('berat_badan', '-')} kg")
            with col2:
                st.markdown(f"**BMI:** {examination.get('bmi', '-'):.2f}" if examination.get('bmi') else "**BMI:** -")
                st.markdown(f"**Klasifikasi BMI:** {examination.get('bmi_classification', '-')}")
        
        # Ambil data gait dari pemeriksaan
        gait_data = examination.get('gait_data', {})
        norm_kinematics = gait_data.get('Norm Kinematics', {})
        
        if not norm_kinematics:
            st.warning("Data kinematik tidak tersedia untuk pemeriksaan ini.")
            return
        
        # Ambil data normal untuk perbandingan
        normal_data = self._get_normal_data_for_comparison()
        if normal_data is None:
            st.error("Data normal belum tersedia. Silakan hubungi administrator.")
            return
        
        # Buat DataFrame dari norm_kinematics pasien yang tersimpan
        rows = []
        for i in range(len(norm_kinematics.get("Percentage of Gait Cycle", []))):
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
        
        patient_kinematics_df = pd.DataFrame(rows)
        
        # Simpan sementara ke session state untuk keperluan fungsi yang sudah ada
        temp_norm_kinematics_df = st.session_state.get('norm_kinematics_df', None)
        temp_filtered_normal_df = st.session_state.get('filtered_normal_df', None)
        
        st.session_state.norm_kinematics_df = patient_kinematics_df
        st.session_state.filtered_normal_df = normal_data
        
        # Proses data kinematik dan hitung MAE
        kinematic_data = self._process_kinematic_data_for_detail(normal_data, norm_kinematics)
        
        # Hitung MAE dan simpan ke session state
        percentage_cycle = list(range(101))
        phase_indices = self.get_phase_indices(percentage_cycle)
        
        # Hitung MAE untuk setiap sendi
        # Pelvis
        l_pelvis_normal = pd.DataFrame(normal_data['LPelvisAngles_X'].tolist()).mean(axis=0).values
        r_pelvis_normal = pd.DataFrame(normal_data['RPelvisAngles_X'].tolist()).mean(axis=0).values
        
        mae_pelvis_left_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('LPelvisAngles_X', [])), 
            l_pelvis_normal, 
            phase_indices
        )
        mae_pelvis_right_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('RPelvisAngles_X', [])), 
            r_pelvis_normal, 
            phase_indices
        )
        
        # Knee
        l_knee_normal = pd.DataFrame(normal_data['LKneeAngles_X'].tolist()).mean(axis=0).values
        r_knee_normal = pd.DataFrame(normal_data['RKneeAngles_X'].tolist()).mean(axis=0).values
        
        mae_knee_left_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('LKneeAngles_X', [])), 
            l_knee_normal, 
            phase_indices
        )
        mae_knee_right_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('RKneeAngles_X', [])), 
            r_knee_normal, 
            phase_indices
        )
        
        # Hip
        l_hip_normal = pd.DataFrame(normal_data['LHipAngles_X'].tolist()).mean(axis=0).values
        r_hip_normal = pd.DataFrame(normal_data['RHipAngles_X'].tolist()).mean(axis=0).values
        
        mae_hip_left_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('LHipAngles_X', [])), 
            l_hip_normal, 
            phase_indices
        )
        mae_hip_right_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('RHipAngles_X', [])), 
            r_hip_normal, 
            phase_indices
        )
        
        # Ankle
        l_ankle_normal = pd.DataFrame(normal_data['LAnkleAngles_X'].tolist()).mean(axis=0).values
        r_ankle_normal = pd.DataFrame(normal_data['RAnkleAngles_X'].tolist()).mean(axis=0).values
        
        mae_ankle_left_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('LAnkleAngles_X', [])), 
            l_ankle_normal, 
            phase_indices
        )
        mae_ankle_right_phases = self.calculate_mae_per_phase(
            np.array(norm_kinematics.get('RAnkleAngles_X', [])), 
            r_ankle_normal, 
            phase_indices
        )
        
        # MAE Keseluruhan
        st.session_state.mae_pelvis_left = np.mean(list(mae_pelvis_left_phases.values())) if mae_pelvis_left_phases else 0
        st.session_state.mae_pelvis_right = np.mean(list(mae_pelvis_right_phases.values())) if mae_pelvis_right_phases else 0
        st.session_state.mae_knee_left = np.mean(list(mae_knee_left_phases.values())) if mae_knee_left_phases else 0
        st.session_state.mae_knee_right = np.mean(list(mae_knee_right_phases.values())) if mae_knee_right_phases else 0
        st.session_state.mae_hip_left = np.mean(list(mae_hip_left_phases.values())) if mae_hip_left_phases else 0
        st.session_state.mae_hip_right = np.mean(list(mae_hip_right_phases.values())) if mae_hip_right_phases else 0
        st.session_state.mae_ankle_left = np.mean(list(mae_ankle_left_phases.values())) if mae_ankle_left_phases else 0
        st.session_state.mae_ankle_right = np.mean(list(mae_ankle_right_phases.values())) if mae_ankle_right_phases else 0
        
        # MAE per fase
        st.session_state.mae_pelvis_left_phases = mae_pelvis_left_phases
        st.session_state.mae_pelvis_right_phases = mae_pelvis_right_phases
        st.session_state.mae_knee_left_phases = mae_knee_left_phases
        st.session_state.mae_knee_right_phases = mae_knee_right_phases
        st.session_state.mae_hip_left_phases = mae_hip_left_phases
        st.session_state.mae_hip_right_phases = mae_hip_right_phases
        st.session_state.mae_ankle_left_phases = mae_ankle_left_phases
        st.session_state.mae_ankle_right_phases = mae_ankle_right_phases
        st.session_state.phase_indices = phase_indices
        
        # Tampilkan visualisasi
        self._show_detail_visualization(kinematic_data, pasien_id, tanggal, examination)
        
        # Kembalikan session state seperti semula
        if temp_norm_kinematics_df is not None:
            st.session_state.norm_kinematics_df = temp_norm_kinematics_df
        else:
            if 'norm_kinematics_df' in st.session_state:
                del st.session_state.norm_kinematics_df
        
        if temp_filtered_normal_df is not None:
            st.session_state.filtered_normal_df = temp_filtered_normal_df
        else:
            if 'filtered_normal_df' in st.session_state:
                del st.session_state.filtered_normal_df
    
    def _get_normal_data_for_comparison(self):
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['gait_data']
            
            cursor = collection.find().limit(100)
            data = list(cursor)
            
            if len(data) == 0:
                return None
            
            df = pd.json_normalize(data)
            df.columns = df.columns.str.replace('Trial Information.', '')
            df.columns = df.columns.str.replace('Subject Parameters.', '')
            df.columns = df.columns.str.replace('Body Measurements.', '')
            df.columns = df.columns.str.replace('Norm Kinematics.', '')
            
            return df
        except Exception as e:
            st.error(f"Error mengambil data normal: {e}")
            return None
    
    def _process_kinematic_data_for_detail(self, filtered_df, patient_kinematics):
        # Pelvis
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())
        
        mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
        std_l_pelvis = l_pelvis_angles.std(axis=0)/np.sqrt(l_pelvis_angles.shape[0])
        mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
        std_r_pelvis = r_pelvis_angles.std(axis=0)/np.sqrt(r_pelvis_angles.shape[0])
        
        lpelvis = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_l_pelvis,
            'std': std_l_pelvis
        })
        
        rpelvis = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_r_pelvis,
            'std': std_r_pelvis
        })
        
        # Knee
        l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
        r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
        
        mean_l_knee = l_knee_angles.mean(axis=0).values
        std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
        mean_r_knee = r_knee_angles.mean(axis=0).values
        std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])
        
        lknee = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_l_knee,
            'std': std_l_knee
        })
        
        rknee = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_r_knee,
            'std': std_r_knee
        })
        
        # Hip
        l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
        r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
        
        mean_l_hip = l_hip_angles.mean(axis=0).values
        std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
        mean_r_hip = r_hip_angles.mean(axis=0).values
        std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])
        
        lhip = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_l_hip,
            'std': std_l_hip
        })
        
        rhip = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_r_hip,
            'std': std_r_hip
        })
        
        # Ankle
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
        
        mean_l_ankle = l_ankle_angles.mean(axis=0).values
        std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
        mean_r_ankle = r_ankle_angles.mean(axis=0).values
        std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])
        
        lankle = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_l_ankle,
            'std': std_l_ankle
        })
        
        rankle = pd.DataFrame({
            "%cycle": list(range(101)),
            'mean': mean_r_ankle,
            'std': std_r_ankle
        })
        
        # Data pasien
        patient_data = {
            'l_pelvis': patient_kinematics.get('LPelvisAngles_X', []),
            'r_pelvis': patient_kinematics.get('RPelvisAngles_X', []),
            'l_knee': patient_kinematics.get('LKneeAngles_X', []),
            'r_knee': patient_kinematics.get('RKneeAngles_X', []),
            'l_hip': patient_kinematics.get('LHipAngles_X', []),
            'r_hip': patient_kinematics.get('RHipAngles_X', []),
            'l_ankle': patient_kinematics.get('LAnkleAngles_X', []),
            'r_ankle': patient_kinematics.get('RAnkleAngles_X', [])
        }
        
        return {
            'lpelvis': lpelvis, 'rpelvis': rpelvis,
            'lknee': lknee, 'rknee': rknee,
            'lhip': lhip, 'rhip': rhip,
            'lankle': lankle, 'rankle': rankle,
            'patient_data': patient_data
        }
    
    def _create_joint_figure_for_detail(self, data, title, color, patient_data=None):
        fig = go.Figure()
        
        # Data normal (rata-rata)
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["mean"], 
            mode='lines',
            name=f'Rata-rata Subjek Normal',
            line=dict(color=color),
            hoverinfo='text',
            text=[f"Rata-rata Normal: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data["mean"])]
        ))
        
        # Data pasien jika ada
        if patient_data is not None and len(patient_data) > 0:
            fig.add_trace(go.Scatter(
                x=data["%cycle"], 
                y=patient_data, 
                mode='lines',
                name='Data Pasien',
                line=dict(color='black', width=3)
            ))
        
        # Area standar error
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["mean"] + data["std"], 
            mode='lines',
            name='Upper Bound',
            line=dict(color=color, width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data["mean"] - data["std"], 
            mode='lines',
            name='Standard Error Area',
            line=dict(color=color, width=0),
            fill='tonexty',
            fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
            showlegend=True,
            hoverinfo='text',
            text=[
                f"Batas Atas: {cycle}%, {valup:.2f}°<br>"
                f"Batas Bawah: {cycle}%, {vallow:.2f}°"
                for cycle, vallow, valup in zip(
                    data["%cycle"],
                    data["mean"] - data["std"],
                    data["mean"] + data["std"]
                )
            ]
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="% Siklus Gait",
            yaxis_title="Sudut (Derajat)",
            template="plotly_white",
            title_x=0.5,
            hovermode="x unified",
            height=400
        )
        return fig
    
    def _show_detail_visualization(self, kinematic_data, pasien_id, tanggal_pemeriksaan, pemeriksaan):
        
        # Buat visualisasi untuk setiap joint
        fig1 = self._create_joint_figure_for_detail(kinematic_data['lpelvis'], "Left Pelvis", 'orange', 
                                               kinematic_data['patient_data'].get('l_pelvis'))
        fig2 = self._create_joint_figure_for_detail(kinematic_data['rpelvis'], "Right Pelvis", 'darkblue', 
                                               kinematic_data['patient_data'].get('r_pelvis'))
        fig3 = self._create_joint_figure_for_detail(kinematic_data['lknee'], "Left Knee", 'orange', 
                                               kinematic_data['patient_data'].get('l_knee'))
        fig4 = self._create_joint_figure_for_detail(kinematic_data['rknee'], "Right Knee", 'darkblue', 
                                               kinematic_data['patient_data'].get('r_knee'))
        fig5 = self._create_joint_figure_for_detail(kinematic_data['lhip'], "Left Hip", 'orange', 
                                               kinematic_data['patient_data'].get('l_hip'))
        fig6 = self._create_joint_figure_for_detail(kinematic_data['rhip'], "Right Hip", 'darkblue', 
                                               kinematic_data['patient_data'].get('r_hip'))
        fig7 = self._create_joint_figure_for_detail(kinematic_data['lankle'], "Left Ankle", 'orange', 
                                               kinematic_data['patient_data'].get('l_ankle'))
        fig8 = self._create_joint_figure_for_detail(kinematic_data['rankle'], "Right Ankle", 'darkblue', 
                                               kinematic_data['patient_data'].get('r_ankle'))
        
        # Tampilkan dalam tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL RINGKASAN"])
        
        with tab1:
            st.subheader("PELVIS")
            st.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')
            
            # Hitung mean differences
            if kinematic_data['patient_data'].get('l_pelvis') and len(kinematic_data['patient_data']['l_pelvis']) > 0:
                maelpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_pelvis']) - kinematic_data['lpelvis']["mean"]))
                maerpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_pelvis']) - kinematic_data['rpelvis']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
                if kinematic_data['patient_data'].get('l_pelvis') and len(kinematic_data['patient_data']['l_pelvis']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pelvis kiri (Pasien vs Normal): {maelpelvis:.2f}°**")
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                if kinematic_data['patient_data'].get('r_pelvis') and len(kinematic_data['patient_data']['r_pelvis']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pelvis kanan (Pasien vs Normal): {maerpelvis:.2f}°**")
                
        with tab2:
            st.subheader("KNEE")
            st.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
            
            if kinematic_data['patient_data'].get('l_knee') and len(kinematic_data['patient_data']['l_knee']) > 0:
                maelknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_knee']) - kinematic_data['lknee']["mean"]))
                maerknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_knee']) - kinematic_data['rknee']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
                if kinematic_data['patient_data'].get('l_knee') and len(kinematic_data['patient_data']['l_knee']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut lutut kiri (Pasien vs Normal): {maelknee:.2f}°**")
            with col2:
                st.plotly_chart(fig4, use_container_width=True)
                if kinematic_data['patient_data'].get('r_knee') and len(kinematic_data['patient_data']['r_knee']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut lutut kanan (Pasien vs Normal): {maerknee:.2f}°**")
        
        with tab3:
            st.subheader("HIP")
            st.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
            
            if kinematic_data['patient_data'].get('l_hip') and len(kinematic_data['patient_data']['l_hip']) > 0:
                maelhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_hip']) - kinematic_data['lhip']["mean"]))
                maerhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_hip']) - kinematic_data['rhip']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
                if kinematic_data['patient_data'].get('l_hip') and len(kinematic_data['patient_data']['l_hip']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pinggul kiri (Pasien vs Normal): {maelhip:.2f}°**")
            with col2:
                st.plotly_chart(fig6, use_container_width=True)
                if kinematic_data['patient_data'].get('r_hip') and len(kinematic_data['patient_data']['r_hip']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pinggul kanan (Pasien vs Normal): {maerhip:.2f}°**")
        
        with tab4:
            st.subheader("ANKLE")
            st.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
            
            if kinematic_data['patient_data'].get('l_ankle') and len(kinematic_data['patient_data']['l_ankle']) > 0:
                maelankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_ankle']) - kinematic_data['lankle']["mean"]))
                maerankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_ankle']) - kinematic_data['rankle']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
                if kinematic_data['patient_data'].get('l_ankle') and len(kinematic_data['patient_data']['l_ankle']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kiri (Pasien vs Normal): {maelankle:.2f}°**")
            with col2:
                st.plotly_chart(fig8, use_container_width=True)
                if kinematic_data['patient_data'].get('r_ankle') and len(kinematic_data['patient_data']['r_ankle']) > 0:
                    st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kanan (Pasien vs Normal): {maerankle:.2f}°**")
        
        with tab5:
            # Tampilkan tabel MAE per fase yang sudah ada
            self._show_mae_phases_table()
            # Tampilkan tabel kinematika gait yang baru
            self._show_gait_kinematics_table()
            # Tampilkan AI summaries
            self._show_ai_summaries_for_detail(pasien_id, tanggal_pemeriksaan)
    
    def _show_mae_phases_table(self):
        """Menampilkan tabel MAE per fase gait yang sudah ada"""
        if not all(key in st.session_state for key in [
            'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
            'mae_knee_left_phases', 'mae_knee_right_phases',
            'mae_hip_left_phases', 'mae_hip_right_phases',
            'mae_ankle_left_phases', 'mae_ankle_right_phases'
        ]):
            st.info("Data MAE per fase belum tersedia.")
            return
        
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
        
        st.markdown("### Detail MAE per Fase Gait")
        
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
        st.markdown("---")
    
    def _show_gait_kinematics_table(self):
        """Menampilkan tabel hasil kinematika gait untuk kaki kanan dan kiri"""
        
        # Periksa apakah data MAE per fase tersedia
        if not all(key in st.session_state for key in [
            'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
            'mae_knee_left_phases', 'mae_knee_right_phases',
            'mae_hip_left_phases', 'mae_hip_right_phases',
            'mae_ankle_left_phases', 'mae_ankle_right_phases',
            'norm_kinematics_df', 'filtered_normal_df'
        ]):
            st.info("Data kinematika gait belum tersedia. Silakan upload data pasien terlebih dahulu.")
            return
        
        st.markdown("### Hasil Kinematika Gait")
        
        # Daftar fase gait dengan rentang persentase yang sesuai
        phases = [
            "Initial Contact (0-2%)",
            "Loading Response (2-10%)",
            "Mid Stance (10-30%)",
            "Terminal Stance (30-50%)",
            "Pre-Swing (50-60%)",
            "Initial Swing (60-73%)",
            "Mid Swing (73-87%)",
            "Terminal Swing (87-100%)"
        ]
        
        # Dapatkan data pasien dari norm_kinematics_df
        patient_df = st.session_state.norm_kinematics_df
        
        # Dapatkan data normal (rata-rata dari filtered_normal_df)
        filtered_df = st.session_state.filtered_normal_df
        
        # Hitung nilai rata-rata normal untuk setiap joint di setiap titik persentase
        normal_means = {}
        
        # Pelvis
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())
        normal_means['l_pelvis'] = l_pelvis_angles.mean(axis=0).values
        normal_means['r_pelvis'] = r_pelvis_angles.mean(axis=0).values
        
        # Knee
        l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
        r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
        normal_means['l_knee'] = l_knee_angles.mean(axis=0).values
        normal_means['r_knee'] = r_knee_angles.mean(axis=0).values
        
        # Hip
        l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
        r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
        normal_means['l_hip'] = l_hip_angles.mean(axis=0).values
        normal_means['r_hip'] = r_hip_angles.mean(axis=0).values
        
        # Ankle
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
        normal_means['l_ankle'] = l_ankle_angles.mean(axis=0).values
        normal_means['r_ankle'] = r_ankle_angles.mean(axis=0).values
        
        # Fungsi untuk mendapatkan nilai rata-rata dalam rentang fase tertentu
        def get_phase_average(values, phase_start, phase_end):
            """Menghitung rata-rata nilai dalam rentang persentase fase"""
            # Persentase dari 0-100
            percentages = list(range(101))
            indices = [i for i, p in enumerate(percentages) if phase_start <= p <= phase_end]
            if indices and len(values) > max(indices):
                phase_values = [values[i] for i in indices]
                return np.mean(phase_values)
            return 0
        
        # Buat mapping rentang persentase untuk setiap fase
        phase_ranges = {
            "Initial Contact (0-2%)": (0, 2),
            "Loading Response (2-10%)": (2, 10),
            "Mid Stance (10-30%)": (10, 30),
            "Terminal Stance (30-50%)": (30, 50),
            "Pre-Swing (50-60%)": (50, 60),
            "Initial Swing (60-73%)": (60, 73),
            "Mid Swing (73-87%)": (73, 87),
            "Terminal Swing (87-100%)": (87, 100)
        }
        
        # Daftar sendi dan kolom yang sesuai di patient_df
        joints = [
            ("Pelvis", "LPelvisAngles_X", "RPelvisAngles_X", "l_pelvis", "r_pelvis"),
            ("Knee", "LKneeAngles_X", "RKneeAngles_X", "l_knee", "r_knee"),
            ("Hip", "LHipAngles_X", "RHipAngles_X", "l_hip", "r_hip"),
            ("Ankle", "LAnkleAngles_X", "RAnkleAngles_X", "l_ankle", "r_ankle")
        ]
        
        # Buat tabel untuk Kaki Kanan
        st.markdown("#### Kaki Kanan")
        
        right_table_data = []
        for phase in phases:
            start_pct, end_pct = phase_ranges[phase]
            first_row = True
            for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
                # Ambil data pasien untuk fase ini (nilai rata-rata dalam rentang fase)
                patient_values = patient_df[right_col].values
                patient_avg = get_phase_average(patient_values, start_pct, end_pct)
                
                # Ambil data normal (baseline) untuk fase ini
                normal_values = normal_means[normal_right_key]
                normal_avg = get_phase_average(normal_values, start_pct, end_pct)
                
                # Ambil MAE yang sudah dihitung sebelumnya
                mae_key = f"mae_{joint_name.lower()}_right_phases"
                mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
                
                # Alternatif: hitung MAE ulang jika perlu
                if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                    indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                    if indices:
                        patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                        normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                        if patient_phase and normal_phase:
                            mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                
                right_table_data.append({
                    "Fase Gait": phase if first_row else "",
                    "Sendi": joint_name,
                    "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                    "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                    "Deviasi (MAE)": f"{mae_value:.2f}°"
                })
                
                first_row = False
        
        df_right = pd.DataFrame(right_table_data)
        st.dataframe(df_right, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Buat tabel untuk Kaki Kiri
        st.markdown("#### Kaki Kiri")
        
        left_table_data = []
        for phase in phases:
            start_pct, end_pct = phase_ranges[phase]
            first_row = True
            for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
                # Ambil data pasien untuk fase ini (nilai rata-rata dalam rentang fase)
                patient_values = patient_df[left_col].values
                patient_avg = get_phase_average(patient_values, start_pct, end_pct)
                
                # Ambil data normal (baseline) untuk fase ini
                normal_values = normal_means[normal_left_key]
                normal_avg = get_phase_average(normal_values, start_pct, end_pct)
                
                # Ambil MAE yang sudah dihitung sebelumnya
                mae_key = f"mae_{joint_name.lower()}_left_phases"
                mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
                
                # Alternatif: hitung MAE ulang jika perlu
                if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                    indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                    if indices:
                        patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                        normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                        if patient_phase and normal_phase:
                            mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                
                left_table_data.append({
                    "Fase Gait": phase if first_row else "",
                    "Sendi": joint_name,
                    "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                    "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                    "Deviasi (MAE)": f"{mae_value:.2f}°"
                })
                first_row = False
        
        df_left = pd.DataFrame(left_table_data)
        st.dataframe(df_left, use_container_width=True, hide_index=True)
        st.markdown("---")
    
    def _get_ai_summaries_for_detail(self, pasien_id, tanggal_pemeriksaan):
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']
            
            summary = collection.find_one(
                {
                    'pasien_id': pasien_id,
                    'tanggal_pemeriksaan': tanggal_pemeriksaan
                },
                sort=[('timestamp', -1)]
            )
            
            return [summary] if summary else []
            
        except Exception as e:
            st.error(f"Error mengambil ringkasan AI: {e}")
            return []
    
    def _show_ai_summaries_for_detail(self, pasien_id, tanggal_pemeriksaan):
        
        ai_summaries = self._get_ai_summaries_for_detail(pasien_id, tanggal_pemeriksaan)
        
        if not ai_summaries:
            st.info("Belum ada hasil analisis AI untuk pemeriksaan ini.")
            return
        
        st.markdown("### Hasil Analisis AI")
        
        # Tampilkan semua ringkasan AI
        for i, summary in enumerate(ai_summaries, 1):
            with st.container(border=True):
                content = summary.get('content', 'Konten tidak tersedia')
                st.markdown(content)
                
                # Tampilkan MAE Overall jika ada
                mae_overall = summary.get('mae_overall')
                if mae_overall:
                    st.markdown("**Mean Absolute Error (MAE) - Perbedaan rata-rata sudut Pasien vs Normal:**")
                    
                    mae_data = []
                    # Pelvis
                    pelvis_avg = (mae_overall.get('pelvis_left', 0) + mae_overall.get('pelvis_right', 0)) / 2
                    mae_data.append({
                        'Sendi': 'Pelvis (Panggul)',
                        'Kiri (°)': f"{mae_overall.get('pelvis_left', 0):.2f}",
                        'Kanan (°)': f"{mae_overall.get('pelvis_right', 0):.2f}",
                        'Rata-rata (°)': f"{pelvis_avg:.2f}"
                    })
                    
                    # Knee
                    knee_avg = (mae_overall.get('knee_left', 0) + mae_overall.get('knee_right', 0)) / 2
                    mae_data.append({
                        'Sendi': 'Knee (Lutut)',
                        'Kiri (°)': f"{mae_overall.get('knee_left', 0):.2f}",
                        'Kanan (°)': f"{mae_overall.get('knee_right', 0):.2f}",
                        'Rata-rata (°)': f"{knee_avg:.2f}"
                    })
                    
                    # Hip
                    hip_avg = (mae_overall.get('hip_left', 0) + mae_overall.get('hip_right', 0)) / 2
                    mae_data.append({
                        'Sendi': 'Hip (Pinggul)',
                        'Kiri (°)': f"{mae_overall.get('hip_left', 0):.2f}",
                        'Kanan (°)': f"{mae_overall.get('hip_right', 0):.2f}",
                        'Rata-rata (°)': f"{hip_avg:.2f}"
                    })
                    
                    # Ankle
                    ankle_avg = (mae_overall.get('ankle_left', 0) + mae_overall.get('ankle_right', 0)) / 2
                    mae_data.append({
                        'Sendi': 'Ankle (Pergelangan Kaki)',
                        'Kiri (°)': f"{mae_overall.get('ankle_left', 0):.2f}",
                        'Kanan (°)': f"{mae_overall.get('ankle_right', 0):.2f}",
                        'Rata-rata (°)': f"{ankle_avg:.2f}"
                    })
                    
                    df_mae = pd.DataFrame(mae_data)
                    st.dataframe(df_mae, use_container_width=True, hide_index=True)
                
                # Pemisah antar ringkasan jika ada lebih dari satu
                if i < len(ai_summaries):
                    st.markdown("---")

    def show_dashboard(self):
        st.markdown("## Dashboard Gait Analysis")

        # CEK LEBIH EFISIEN - hanya cek key existence
        has_patient_data = ('uploaded_patient_data' in st.session_state and 
                           'norm_kinematics_df' in st.session_state and
                           st.session_state.norm_kinematics_df is not None)

        if has_patient_data:
            try:
                self.process_dashboard_with_patient()
            except Exception as e:
                st.error(f"Error dalam memproses dashboard: {e}")
        else:
            st.warning("ℹ️ Tidak ada data pasien yang diupload. Silakan upload data pasien di menu 'Input Pemeriksan Pasien' untuk melihat analisis perbandingan.")
            self.show_normal_dashboard()

    # Proses dashboard dengan data pasien
    def process_dashboard_with_patient(self):       
        px.defaults.template = 'plotly_dark'
        px.defaults.color_continuous_scale = 'reds'

        client = get_mongo_client()
        db = client['GaitDB']
        collection = db['gait_data']

        cursor = collection.find().limit(100)  # Batasi data
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

        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### Filter Data")
    
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            min_age = df['Age'].min()
            max_age = df['Age'].max()
            age_range = st.slider('Filter by Age Range:', min_value=min_age, max_value=max_age, value=(min_age, max_age))
    
        with col2:
            bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
            classbmi = st.selectbox(label="BMI Classification", options=bmi_options)
    
        with col3:
            gender_mapping = {"L": "Pria", "P": "Wanita"}
            df["Gender"] = df["Gender"].map(gender_mapping)
            gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
            gender = st.selectbox(label="Gender", options=gender_options)
    
        st.markdown("</div>", unsafe_allow_html=True)
            
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

        norm_kinematics_df = st.session_state.norm_kinematics_df
        self.create_visualizations(filtered_df, norm_kinematics_df)

    # dashboard baseline data normal (tanpa pemeriksaan pasien)
    def show_normal_dashboard(self):
        px.defaults.template = 'plotly_dark'
        px.defaults.color_continuous_scale = 'reds'

        client = get_mongo_client()
        db = client['GaitDB']
        collection = db['gait_data']

        cursor = collection.find().limit(100)
        data = list(cursor)
        if len(data) == 0:
            st.error("Database Normal Belum Ada. Silahkan Upload Data Normal pada Menu 'Input Baseline Data Gait'")
            st.info("Untuk melihat dashboard analisis gait, Anda perlu mengupload data subjek normal terlebih dahulu.")
            return

        df = pd.json_normalize(data)
        df.columns = df.columns.str.replace('Trial Information.', '') # Mengubah nama kolom
        df.columns = df.columns.str.replace('Subject Parameters.', '')
        df.columns = df.columns.str.replace('Body Measurements.', '')
        df.columns = df.columns.str.replace('Norm Kinematics.', '')

        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### Filter Data")

        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            min_age = df['Age'].min()
            max_age = df['Age'].max()
            age_range = st.slider('Filter by Age Range:', min_value=min_age, max_value=max_age, value=(min_age, max_age))

        with col2:
            bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
            classbmi = st.selectbox(label="BMI Classification", options=bmi_options)

        with col3:
            gender_mapping = {"L": "Pria", "P": "Wanita"}
            df["Gender"] = df["Gender"].map(gender_mapping)
            gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
            gender = st.selectbox(label="Gender", options=gender_options)

        st.markdown("</div>", unsafe_allow_html=True)

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
            self.show_normal_charts_only(filtered_df)

    # Visualisasi untuk semua sendi
    def create_visualizations(self, filtered_df, norm_kinematics_df):
        percentage_cycle = list(range(101))
        phase_indices = self.get_phase_indices(percentage_cycle) # Dapatkan indeks untuk setiap fase
        
        # PELVIS
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())

        mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
        std_l_pelvis = l_pelvis_angles.std(axis=0) / np.sqrt(l_pelvis_angles.shape[0])
        mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
        std_r_pelvis = r_pelvis_angles.std(axis=0) / np.sqrt(r_pelvis_angles.shape[0])
        std_l_pelvis = std_l_pelvis.values if isinstance(std_l_pelvis, pd.Series) else std_l_pelvis
        std_r_pelvis = std_r_pelvis.values if isinstance(std_r_pelvis, pd.Series) else std_r_pelvis

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
        
        # ANKLE
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
        
        mean_l_ankle = l_ankle_angles.mean(axis=0).values
        std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
        mean_r_ankle = r_ankle_angles.mean(axis=0).values
        std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])

        std_l_ankle = std_l_ankle.values if isinstance(std_l_ankle, pd.Series) else std_l_ankle
        std_r_ankle = std_r_ankle.values if isinstance(std_r_ankle, pd.Series) else std_r_ankle

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
        
        # Simpan phase_indices 
        st.session_state.phase_indices = phase_indices

        # Buat Figure
        fig1 = self.create_pelvis_figure(lpelvis, "Left Pelvis", 'orange')
        fig2 = self.create_pelvis_figure(rpelvis, "Right Pelvis", 'dark blue')
        fig3 = self.create_joint_figure(lknee, "Left Knee", 'orange')
        fig4 = self.create_joint_figure(rknee, "Right Knee", 'dark blue')
        fig5 = self.create_joint_figure(lhip, "Left Hip", 'orange')
        fig6 = self.create_joint_figure(rhip, "Right Hip", 'dark blue')
        fig7 = self.create_joint_figure(lankle, "Left Ankle", 'orange')
        fig8 = self.create_joint_figure(rankle, "Right Ankle", 'dark blue')

        # Tampilkan dalam tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL RINGKASAN"])

        with tab1:
            tab1.subheader("PELVIS")
            tab1.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')
            col1, col2 = tab1.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Pelvis: {maelpelvis:.2f}°**") 
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Pelvis: {maerpelvis:.2f}°**") 
                
        with tab2:
            tab2.subheader("KNEE")
            tab2.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
            col1, col2 = tab2.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Knee: {maelknee:.2f}°**")
            with col2:
                st.plotly_chart(fig4, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Knee: {maerknee:.2f}°**")
                
        with tab3:
            tab3.subheader("HIP")
            tab3.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')

            col1, col2 = tab3.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Hip: {maelhip:.2f}°**")
            with col2:
                st.plotly_chart(fig6, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Hip: {maerhip:.2f}°**")
                
        with tab4:
            tab4.subheader("ANKLE")
            tab4.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')

            col1, col2 = tab4.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
                st.write(f"**MAE Keseluruhan Left Ankle: {maelankle:.2f}°**")
            with col2:
                st.plotly_chart(fig8, use_container_width=True)
                st.write(f"**MAE Keseluruhan Right Ankle: {maerankle:.2f}°**")

        with tab5:
            # 1. Ringkasan MAE Keseluruhan
            self.show_mae_overall_summary()
            # 2. Detail MAE per Fase Gait
            self._show_mae_phases_table()
            # 3. Hasil Kinematika Gait
            self._show_gait_kinematics_table()
            # Tampilkan AI summaries
            self.show_ai_generation_section()

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
                'di antara tulang pinggul, dan di atas paha.')
            col1, col2 = tab1.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                
        with tab2:
            tab2.subheader("KNEE")
            tab2.write(
                'Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, '
                'berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
            col1, col2 = tab2.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                st.plotly_chart(fig4, use_container_width=True)

        with tab3:
            tab3.subheader("HIP")
            tab3.write(
                'Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
            col1, col2 = tab3.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
            with col2:
                st.plotly_chart(fig6, use_container_width=True)

        with tab4:
            tab4.subheader("ANKLE")
            tab4.write(
                'Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
            col1, col2 = tab4.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
            with col2:
                st.plotly_chart(fig8, use_container_width=True)

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
                
    # Gait Per Fase
    def get_gait_phase(self, percentage):
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
            indices = [i for i, p in enumerate(percentage_list) if start <= p <= end]
            phase_indices[phase] = indices
        return phase_indices

    # MAE untuk setiap fase gait
    def calculate_mae_per_phase(self, patient_values, normal_values, phase_indices):
        mae_per_phase = {}
        for phase, indices in phase_indices.items():
            if indices:
                patient_phase = [patient_values[i] for i in indices]
                normal_phase = [normal_values[i] for i in indices]
                mae = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                mae_per_phase[phase] = mae
        return mae_per_phase
        
    # Upper bound dan Lower bound
    def calculate_bounds_from_normal_data(self, filtered_df):
        bounds = {}
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
                # Ambil semua nilai untuk joint
                joint_values = pd.DataFrame(filtered_df[joint].tolist())
                mean_values = joint_values.mean(axis=0).values
                std_values = joint_values.std(axis=0).values
                upper_bound = mean_values + (2 * std_values)
                lower_bound = mean_values - (2 * std_values)
                bounds[joint] = {
                    'upper': np.mean(upper_bound),
                    'lower': np.mean(lower_bound),
                    'upper_by_cycle': upper_bound.tolist(),
                    'lower_by_cycle': lower_bound.tolist(),
                    'mean_by_cycle': mean_values.tolist()
                }
        return bounds

    def show_mae_overall_summary(self):
        """Menampilkan ringkasan MAE keseluruhan untuk semua sendi"""
        st.markdown("### Ringkasan MAE Keseluruhan")
            # Validasi data MAE keseluruhan
        required_mae_keys = [
            'mae_pelvis_left', 'mae_pelvis_right',
            'mae_knee_left', 'mae_knee_right',
            'mae_hip_left', 'mae_hip_right',
            'mae_ankle_left', 'mae_ankle_right'
        ]
        
        missing_keys = [key for key in required_mae_keys if key not in st.session_state]
        if missing_keys:
            st.info("Data MAE keseluruhan belum tersedia. Silakan upload data pasien terlebih dahulu.")
            return
        mae_overall_data = []
        
        # Pelvis
        pelvis_avg = (st.session_state.mae_pelvis_left + st.session_state.mae_pelvis_right) / 2
        mae_overall_data.append({
            'Sendi': 'Pelvis (Panggul)',
            'Kiri (°)': f"{st.session_state.mae_pelvis_left:.2f}",
            'Kanan (°)': f"{st.session_state.mae_pelvis_right:.2f}",
            'Rata-rata (°)': f"{pelvis_avg:.2f}"
        })
        
        # Knee
        knee_avg = (st.session_state.mae_knee_left + st.session_state.mae_knee_right) / 2
        mae_overall_data.append({
            'Sendi': 'Knee (Lutut)',
            'Kiri (°)': f"{st.session_state.mae_knee_left:.2f}",
            'Kanan (°)': f"{st.session_state.mae_knee_right:.2f}",
            'Rata-rata (°)': f"{knee_avg:.2f}"
        })
        
        # Hip
        hip_avg = (st.session_state.mae_hip_left + st.session_state.mae_hip_right) / 2
        mae_overall_data.append({
            'Sendi': 'Hip (Pinggul)',
            'Kiri (°)': f"{st.session_state.mae_hip_left:.2f}",
            'Kanan (°)': f"{st.session_state.mae_hip_right:.2f}",
            'Rata-rata (°)': f"{hip_avg:.2f}"
        })
        
        # Ankle
        ankle_avg = (st.session_state.mae_ankle_left + st.session_state.mae_ankle_right) / 2
        mae_overall_data.append({
            'Sendi': 'Ankle (Pergelangan Kaki)',
            'Kiri (°)': f"{st.session_state.mae_ankle_left:.2f}",
            'Kanan (°)': f"{st.session_state.mae_ankle_right:.2f}",
            'Rata-rata (°)': f"{ankle_avg:.2f}"
        })
        
        df_mae_overall = pd.DataFrame(mae_overall_data)
        st.dataframe(df_mae_overall, use_container_width=True, hide_index=True)
        
    def _show_mae_phases_table(self):
        """Menampilkan tabel MAE per fase gait yang sudah ada"""
        if not all(key in st.session_state for key in [
            'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
            'mae_knee_left_phases', 'mae_knee_right_phases',
            'mae_hip_left_phases', 'mae_hip_right_phases',
            'mae_ankle_left_phases', 'mae_ankle_right_phases'
        ]):
            st.info("Data MAE per fase belum tersedia.")
            return
        
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
        
        st.markdown("### Detail MAE per Fase Gait")
        
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
        st.markdown("---")
    
    def _show_gait_kinematics_table(self):
        """Menampilkan tabel hasil kinematika gait untuk kaki kanan dan kiri"""
        
        # Periksa apakah data MAE per fase tersedia
        if not all(key in st.session_state for key in [
            'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
            'mae_knee_left_phases', 'mae_knee_right_phases',
            'mae_hip_left_phases', 'mae_hip_right_phases',
            'mae_ankle_left_phases', 'mae_ankle_right_phases',
            'norm_kinematics_df', 'filtered_normal_df'
        ]):
            st.info("Data kinematika gait belum tersedia. Silakan upload data pasien terlebih dahulu.")
            return
        
        st.markdown("### Hasil Kinematika Gait")
        
        # Daftar fase gait dengan rentang persentase yang sesuai
        phases = [
            "Initial Contact (0-2%)",
            "Loading Response (2-10%)",
            "Mid Stance (10-30%)",
            "Terminal Stance (30-50%)",
            "Pre-Swing (50-60%)",
            "Initial Swing (60-73%)",
            "Mid Swing (73-87%)",
            "Terminal Swing (87-100%)"
        ]
        
        # Dapatkan data pasien dari norm_kinematics_df
        patient_df = st.session_state.norm_kinematics_df
        
        # Dapatkan data normal (rata-rata dari filtered_normal_df)
        filtered_df = st.session_state.filtered_normal_df
        
        # Hitung nilai rata-rata normal untuk setiap joint di setiap titik persentase
        normal_means = {}
        
        # Pelvis
        l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
        r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())
        normal_means['l_pelvis'] = l_pelvis_angles.mean(axis=0).values
        normal_means['r_pelvis'] = r_pelvis_angles.mean(axis=0).values
        
        # Knee
        l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
        r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
        normal_means['l_knee'] = l_knee_angles.mean(axis=0).values
        normal_means['r_knee'] = r_knee_angles.mean(axis=0).values
        
        # Hip
        l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
        r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
        normal_means['l_hip'] = l_hip_angles.mean(axis=0).values
        normal_means['r_hip'] = r_hip_angles.mean(axis=0).values
        
        # Ankle
        l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
        r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
        normal_means['l_ankle'] = l_ankle_angles.mean(axis=0).values
        normal_means['r_ankle'] = r_ankle_angles.mean(axis=0).values
        
        # Fungsi untuk mendapatkan nilai rata-rata dalam rentang fase tertentu
        def get_phase_average(values, phase_start, phase_end):
            """Menghitung rata-rata nilai dalam rentang persentase fase"""
            # Persentase dari 0-100
            percentages = list(range(101))
            indices = [i for i, p in enumerate(percentages) if phase_start <= p <= phase_end]
            if indices and len(values) > max(indices):
                phase_values = [values[i] for i in indices]
                return np.mean(phase_values)
            return 0
        
        # Buat mapping rentang persentase untuk setiap fase
        phase_ranges = {
            "Initial Contact (0-2%)": (0, 2),
            "Loading Response (2-10%)": (2, 10),
            "Mid Stance (10-30%)": (10, 30),
            "Terminal Stance (30-50%)": (30, 50),
            "Pre-Swing (50-60%)": (50, 60),
            "Initial Swing (60-73%)": (60, 73),
            "Mid Swing (73-87%)": (73, 87),
            "Terminal Swing (87-100%)": (87, 100)
        }
        
        # Daftar sendi dan kolom yang sesuai di patient_df
        joints = [
            ("Pelvis", "LPelvisAngles_X", "RPelvisAngles_X", "l_pelvis", "r_pelvis"),
            ("Knee", "LKneeAngles_X", "RKneeAngles_X", "l_knee", "r_knee"),
            ("Hip", "LHipAngles_X", "RHipAngles_X", "l_hip", "r_hip"),
            ("Ankle", "LAnkleAngles_X", "RAnkleAngles_X", "l_ankle", "r_ankle")
        ]
        
        # Buat tabel untuk Kaki Kanan
        st.markdown("#### Kaki Kanan")
        
        right_table_data = []
        for phase in phases:
            start_pct, end_pct = phase_ranges[phase]
            first_row = True
            for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
                # Ambil data pasien untuk fase ini (nilai rata-rata dalam rentang fase)
                patient_values = patient_df[right_col].values
                patient_avg = get_phase_average(patient_values, start_pct, end_pct)
                
                # Ambil data normal (baseline) untuk fase ini
                normal_values = normal_means[normal_right_key]
                normal_avg = get_phase_average(normal_values, start_pct, end_pct)
                
                # Ambil MAE yang sudah dihitung sebelumnya
                mae_key = f"mae_{joint_name.lower()}_right_phases"
                mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
                
                # Alternatif: hitung MAE ulang jika perlu
                if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                    indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                    if indices:
                        patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                        normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                        if patient_phase and normal_phase:
                            mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                
                right_table_data.append({
                    "Fase Gait": phase if first_row else "",
                    "Sendi": joint_name,
                    "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                    "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                    "Deviasi (MAE)": f"{mae_value:.2f}°"
                })
                
                first_row = False
        
        df_right = pd.DataFrame(right_table_data)
        st.dataframe(df_right, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Buat tabel untuk Kaki Kiri
        st.markdown("#### Kaki Kiri")
        
        left_table_data = []
        for phase in phases:
            start_pct, end_pct = phase_ranges[phase]
            first_row = True
            for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
                # Ambil data pasien untuk fase ini (nilai rata-rata dalam rentang fase)
                patient_values = patient_df[left_col].values
                patient_avg = get_phase_average(patient_values, start_pct, end_pct)
                
                # Ambil data normal (baseline) untuk fase ini
                normal_values = normal_means[normal_left_key]
                normal_avg = get_phase_average(normal_values, start_pct, end_pct)
                
                # Ambil MAE yang sudah dihitung sebelumnya
                mae_key = f"mae_{joint_name.lower()}_left_phases"
                mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
                
                # Alternatif: hitung MAE ulang jika perlu
                if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                    indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                    if indices:
                        patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                        normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                        if patient_phase and normal_phase:
                            mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
                
                left_table_data.append({
                    "Fase Gait": phase if first_row else "",
                    "Sendi": joint_name,
                    "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                    "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                    "Deviasi (MAE)": f"{mae_value:.2f}°"
                })
                first_row = False
        
        df_left = pd.DataFrame(left_table_data)
        st.dataframe(df_left, use_container_width=True, hide_index=True)

    # Fungsi AI
    def show_ai_generation_section(self):
        # Validasi data yang dibutuhkan untuk AI
        required_keys = [
            'mae_pelvis_left', 'mae_pelvis_right',
            'mae_knee_left', 'mae_knee_right',
            'mae_hip_left', 'mae_hip_right',
            'mae_ankle_left', 'mae_ankle_right',
            'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
            'mae_knee_left_phases', 'mae_knee_right_phases',
            'mae_hip_left_phases', 'mae_hip_right_phases',
            'mae_ankle_left_phases', 'mae_ankle_right_phases',
            'phase_indices']
        
        missing_keys = [key for key in required_keys if key not in st.session_state]
        if missing_keys:
            st.warning("Data MAE belum tersedia. Silakan upload data pasien terlebih dahulu.")
            return
    
        # INISIALISASI
        if 'current_patient_key' not in st.session_state:
            st.warning("Belum ada data pasien. Silakan upload data pasien terlebih dahulu.")
            return
    
        current_patient_key = st.session_state.current_patient_key
        
        # Ambil data upper bound dan lower bound
        if 'filtered_normal_df' not in st.session_state:
            st.info("Silakan upload data normal terlebih dahulu.")
            return
        
        filtered_df = st.session_state.filtered_normal_df
        if filtered_df.empty:
            st.warning("Data normal kosong. Silakan cek filter yang Anda gunakan.")
            return
        
        # Hitung upper bound dan lower bound
        bounds_data = self.calculate_bounds_from_normal_data(filtered_df)

        # TOMBOL GENERATE AI
        patient_saved_key = f'saved_summary_content_{current_patient_key}'
        patient_ai_generated_key = f'ai_summaries_generated_{current_patient_key}'
        
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
        # Jika sudah ada hasil yang disimpan
        if patient_saved_key in st.session_state and st.session_state[patient_saved_key]:
            st.markdown("#### Hasil Ringkasan AI")
            st.info(st.session_state[patient_saved_key])
            st.markdown("---")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Generate Ringkasan Baru", use_container_width=True, type="secondary"):
                    if patient_saved_key in st.session_state:
                        del st.session_state[patient_saved_key]
                    if patient_ai_generated_key in st.session_state:
                        del st.session_state[patient_ai_generated_key]
                    if f'ai_summary_content_{current_patient_key}' in st.session_state:
                        del st.session_state[f'ai_summary_content_{current_patient_key}']
                    st.rerun()
            return
        
        # Jika belum ada hasil AI yang digenerate
        if patient_ai_generated_key not in st.session_state:
            st.markdown("### Generate Ringkasan AI")
            st.info("Klik tombol di bawah untuk menghasilkan ringkasan AI berdasarkan data MAE dan batas normal (Upper/Lower Bound) yang telah dihitung.")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                generate_button = st.button("Generate Ringkasan AI", use_container_width=True, type="primary")
            
            if not generate_button:
                st.stop()
            
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

                final_prompt = f"""
                Anda adalah fisioterapis klinis dan analis biomekanika gait.
                
                DATA:
                {full_data}
                
                TUGAS:
                Lakukan interpretasi gait analysis secara klinis dan terstruktur berdasarkan data yang diberikan.
                
                ATURAN WAJIB:
                - Maksimal 300 kata
                - Fokus pada temuan paling signifikan
                - Hindari terlalu banyak angka
                - Gunakan istilah klinis yang profesional dan mudah dipahami
                - Gunakan hanya data yang diberikan
                - Jangan menetapkan diagnosis medis pasti
                - Gunakan bahasa interpretatif dan observasional, bukan diagnosis medis.
                - Gunakan istilah seperti "mengindikasikan", "berpotensi menunjukkan", atau "konsisten dengan"
                - Gunakan data upper bound dan lower bound untuk menentukan apakah parameter berada di luar rentang normal
                - Sebutkan secara singkat jika terdapat parameter yang berada di luar rentang normal
                - Prioritaskan temuan dengan MAE tinggi dan berada di luar rentang normal
                - Gunakan format **bold** untuk menyoroti sendi bermasalah, fase gait kritis, dan tingkat deviasi
                - Jangan menggunakan bold secara berlebihan
                
                STRUKTUR:
                1. Highlight Temuan Utama:
                - Sebutkan 3–4 temuan paling signifikan
                
                2. Tabel Ringkasan Deviasi
                | Sendi | Sisi | Fase Paling Bermasalah | Tingkat Deviasi | Hasil |
                |-------|------|------------------------|-----------------|-------|
                Isi maksimal 5–7 baris.
                
                3. Interpretasi Klinis
                Buat dalam bentuk bullet point per sendi.
                - Gunakan istilah observasional seperti:
                  - lebih
                  - kurang
                  - cenderung meningkat
                  - cenderung menurun
                - Hindari diagnosis medis atau kesimpulan pasti
                - Fokus pada pola gerak dan fungsi gait
                - Jelaskan apakah gerakan tampak lebih atau kurang dibanding pola normal
                - Sertakan jika parameter berada di luar rentang normal
                
                4. Kesimpulan
                Buat dalam bentuk bullet point singkat.
                - Jelaskan indikasi fungsional berdasarkan pola gait
                - Hindari diagnosis medis
                - Fokus pada kemungkinan gangguan biomekanik atau kompensasi gerak.
                """
                
                # Generate summaries
                
                try:
                    with st.spinner("Mohon tunggu... Sistem sedang membuat Ringkasan AI"):
                        response = gemini_model.generate_content(final_prompt)
                        summary_content = response.text
                            
                except Exception as e:
                    st.error(f"Error generating AI summaries: {e}")
                    summary_content = "Ringkasan tidak tersedia. Silakan periksa koneksi API Gemini atau coba lagi nanti."
                
                # Simpan ke session state
                st.session_state[f'ai_summary_content_{current_patient_key}'] = summary_content
                st.session_state[patient_ai_generated_key] = True
                st.rerun()
        
        # Jika sudah digenerate, tampilkan hasil
        else:
            # Ambil summaries dari session state
            summary_content = st.session_state.get(f'ai_summary_content_{current_patient_key}', "")
            if not summary_content:
                st.warning("Tidak ada ringkasan yang dihasilkan. Silakan generate ulang.")
                if st.button("Generate Ulang"):
                    if f'ai_summaries_generated_{current_patient_key}' in st.session_state:
                        del st.session_state[f'ai_summaries_generated_{current_patient_key}']
                    st.rerun()
                return

            st.markdown("### Hasil Ringkasan AI")
            st.markdown(summary_content)
            st.markdown("---")

            # Dropdown untuk memilih dan menyimpan hasil terbaik
            st.markdown("### Simpan Hasil")
          
            # Tombol simpan
            if st.button("Simpan Hasil Ringkasan", use_container_width=True, type="primary", key="save_ai_summary"):
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
                    
                success = self.save_single_summary(
                    content=summary_content,
                    mae_overall={
                        'pelvis_left': st.session_state.mae_pelvis_left,
                        'pelvis_right': st.session_state.mae_pelvis_right,
                        'knee_left': st.session_state.mae_knee_left,
                        'knee_right': st.session_state.mae_knee_right,
                        'hip_left': st.session_state.mae_hip_left,
                        'hip_right': st.session_state.mae_hip_right,
                        'ankle_left': st.session_state.mae_ankle_left,
                        'ankle_right': st.session_state.mae_ankle_right
                    },
                    mae_phases=mae_data_for_save,
                    bounds_data=bounds_data
                )
                  
                if success:
                    st.session_state[patient_saved_key] = summary_content
                    st.success("Ringkasan AI berhasil disimpan!")
                    st.rerun()
                else:
                    st.error("Gagal menyimpan ke database")

    # Simpan ringkasan yang dipilih ke database dengan data MAE per fase
    def save_single_summary(self, content, mae_overall, mae_phases, bounds_data):
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']

            pasien_id = st.session_state.get('current_pasien_id', None)
            nama_pasien = st.session_state.get('current_nama_pasien', None)
            tanggal_pemeriksaan = st.session_state.get('current_tanggal_pemeriksaan', None)

            if not pasien_id and 'norm_kinematics_df' in st.session_state:
                st.warning("Data pasien tidak ditemukan di session state. Pastikan data pasien sudah diupload.")
                return False
            
            # Data yang akan disimpan
            summary_data = {
                'timestamp': datetime.now(),
                'dokter_id': st.session_state.get('dokter_user_id'),
                'dokter_nama': st.session_state.get('dokter_nama'),
                'pasien_id': pasien_id,
                'nama_pasien': nama_pasien,
                'tanggal_pemeriksaan': tanggal_pemeriksaan,
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
            
    # Reset session state AI summary untuk pasien baru
    def reset_ai_summary_session_state_except_current(self):
        keys_to_reset = [
            'ai_summaries_generated',
            'saved_summary_content'
        ]
        
        # Reset kunci utama
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        # Hapus juga kunci yang mengandung pattern lama
        if 'current_patient_key' in st.session_state:
            current_key = st.session_state.current_patient_key
            # Hapus semua kunci yang mengandung pattern selain current_key
            for key in list(st.session_state.keys()):
                if ('patient_' in key or 'summaries_' in key) and key != 'current_patient_key':
                    del st.session_state[key]

    def reset_patient_data_session_state(self):
        patient_keys = [
            'uploaded_patient_data',
            'norm_kinematics_df',
            'current_pasien_id',
            'current_nama_pasien',
            'current_tanggal_pemeriksaan',
            'current_patient_key',
            'filtered_normal_df'
        ]
        
        for key in patient_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reset AI summary terkait pasien
        self.reset_ai_summary_session_state_except_current()

    # Reset AI summary untuk pasien dan tanggal tertentu
    def reset_ai_summary_for_patient_and_date(self, pasien_id, tanggal_pemeriksaan):
        patient_date_key = f"patient_{pasien_id}_{tanggal_pemeriksaan}"
        
        # Kunci-kunci yang perlu dihapus untuk pasien dan tanggal ini
        keys_to_reset = [
            f'ai_summaries_generated_{patient_date_key}',
            f'saved_summary_content_{patient_date_key}'
        ]
        
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reset kunci utama AI jika perlu
        if 'ai_summaries_generated' in st.session_state and st.session_state.get('current_patient_key') == patient_date_key:
            if 'ai_summaries_generated' in st.session_state:
                del st.session_state['ai_summaries_generated']
