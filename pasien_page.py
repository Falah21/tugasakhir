import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime
from pymongo import MongoClient
from css_style import load_css
from register_page import RegisterPage
# import traceback
import bcrypt

# Optimasi koneksi MongoDB
def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )

# Login Form
def login_form_pasien(role_label: str = "Pasien"):
    st.markdown(load_css(), unsafe_allow_html=True)

    # Tombol kembali
    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    # Page Login
    st.markdown("<h2>Aplikasi GAIT Clinic</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan GAIT</p>", unsafe_allow_html=True)
    # st.markdown("---")
    st.subheader(f"Login - {role_label}")
    user_id = st.text_input("NIK", placeholder="Masukkan NIK anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")
    submit = st.button("Login", use_container_width=True)
    st.markdown("<p class='register-link'>Belum punya akun?</p>", unsafe_allow_html=True)
    if st.button("Register", use_container_width=True):
        st.session_state.show_register = True
        st.rerun()

    return user_id, password, submit

# Pasien Page
class PasienPage:
    def __init__(self):
        # Inisialisasi session state
        st.session_state.setdefault("pasien_auth", {})
        st.session_state.setdefault("pasien_list", [])
        st.session_state.setdefault("show_register", False)
        st.session_state.setdefault("pasien_logged_in", False)
        st.session_state.setdefault("pasien_user_id", None)
        st.session_state.setdefault("pasien_menu", "Dashboard")
        # st.session_state.setdefault("pasien_nama", "Pasien") 
        
        # Load data dari database saat inisialisasi
        # self._load_pasien_data_from_db()

        # Instance RegisterPage
        self.register_page = RegisterPage()

    # def _load_pasien_data_from_db(self):
    #     try:
    #         client = get_mongo_client()
    #         db = client['GaitDB']
    #         collection = db['users']
            
    #         # Ambil semua data pasien
    #         pasien_data = list(collection.find({'role': 'pasien'}))

    #         st.session_state["pasien_auth"] = {}
    #         st.session_state["pasien_list"] = []
            
    #         # Update session state dengan data dari database
    #         for pasien in pasien_data:
    #             user_id = pasien.get('user_id')
    #             password = pasien.get('password')
    #             if user_id and password:
    #                 st.session_state["pasien_auth"][user_id] = password

    #                 st.session_state["pasien_list"].append({
    #                     "User ID": user_id,
    #                     "Nama Lengkap": pasien.get('nama_lengkap', ''),
    #                     "Tanggal Lahir": pasien.get('tanggal_lahir', ''),
    #                     "Jenis Kelamin": pasien.get('jenis_kelamin', ''),
    #                     "Role": pasien.get('role', ''),
    #                     "Tanggal Dibuat": pasien.get('tanggal_dibuat', '')
    #                 })
                    
    #     except Exception as e:
    #         st.error(f"Error loading patient data: {e}")

    def _authenticate_pasien(self, user_id, password):
        """Autentikasi pasien dari database"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['users']
            
            # Cari user dengan role 'pasien'
            pasien = collection.find_one({
                'user_id': user_id,
                'role': 'pasien'
            })
            
            if pasien:
                stored_password = pasien.get('password')
                # Verifikasi password dengan bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return {
                        'user_id': pasien.get('user_id'),
                        'nama_lengkap': pasien.get('nama_lengkap'),
                        'role': pasien.get('role'),
                        'tanggal_lahir': pasien.get('tanggal_lahir'),
                        'jenis_kelamin': pasien.get('jenis_kelamin')
                    }
                return None
                
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
        
    def _get_pemeriksaan_data(self, pasien_id, tanggal):
        """Fungsi untuk mendapatkan data pemeriksaan berdasarkan user_id dan tanggal dari database"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['patient_examinations']
            
            # Cari data pemeriksaan berdasarkan user_id dan tanggal
            pemeriksaan = collection.find_one({
                'pasien_id': pasien_id,
                'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d")
            })
            
            return pemeriksaan
            
        except Exception as e:
            st.error(f"Error mengambil data pemeriksaan: {e}")
            return None

    def _get_all_pemeriksaan_dates(self, pasien_id):
        """Mendapatkan semua tanggal pemeriksaan untuk pasien tertentu"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['patient_examinations']
            
            # Ambil semua tanggal pemeriksaan untuk pasien ini
            pemeriksaan_list = collection.find(
                {'pasien_id': pasien_id},
                {'tanggal_pemeriksaan': 1}
            )
            
            dates = []
            for exam in pemeriksaan_list:
                tanggal_str = exam.get('tanggal_pemeriksaan')
                if tanggal_str:
                    try:
                        dates.append(datetime.strptime(tanggal_str, "%Y-%m-%d").date())
                    except:
                        continue
            
            return sorted(dates, reverse=True)  # Urutkan dari terbaru
            
        except Exception as e:
            st.error(f"Error mengambil daftar pemeriksaan: {e}")
            return []

    def _get_normal_data(self):
        """Mendapatkan data normal dari database"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['gait_data']
            
            # Ambil data normal
            cursor = collection.find().limit(100)
            data = list(cursor)
            
            if len(data) == 0:
                return None
                
            # Normalisasi data untuk DataFrame
            df = pd.json_normalize(data)
            df.columns = df.columns.str.replace('Trial Information.', '')
            df.columns = df.columns.str.replace('Subject Parameters.', '')
            df.columns = df.columns.str.replace('Body Measurements.', '')
            df.columns = df.columns.str.replace('Norm Kinematics.', '')
            
            return df
            
        except Exception as e:
            st.error(f"Error mengambil data normal: {e}")
            return None

    def _create_joint_figure(self, data, title, color, patient_data=None):
        """Membuat figure untuk joint tertentu"""
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
        if patient_data is not None:
            fig.add_trace(go.Scatter(
                x=data["%cycle"], 
                y=patient_data, 
                mode='lines',
                name='Data Anda',
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
            text=[f"Batas Atas: {cycle}%, {valup:.2f}°<br>Batas Bawah: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data["mean"] - data["std"], data["mean"] + data["std"])]
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

    def _process_kinematic_data(self, filtered_df, patient_kinematics=None):
        """Memproses data kinematik untuk visualisasi"""
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

        # Data pasien jika ada
        patient_data = {}
        if patient_kinematics:
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

    def _show_dashboard_visualization(self, kinematic_data):
        """Menampilkan visualisasi dashboard"""
        # Buat visualisasi untuk setiap joint
        fig1 = self._create_joint_figure(kinematic_data['lpelvis'], "Left Pelvis", 'orange', 
                                       kinematic_data['patient_data'].get('l_pelvis'))
        fig2 = self._create_joint_figure(kinematic_data['rpelvis'], "Right Pelvis", 'darkblue', 
                                       kinematic_data['patient_data'].get('r_pelvis'))
        fig3 = self._create_joint_figure(kinematic_data['lknee'], "Left Knee", 'orange', 
                                       kinematic_data['patient_data'].get('l_knee'))
        fig4 = self._create_joint_figure(kinematic_data['rknee'], "Right Knee", 'darkblue', 
                                       kinematic_data['patient_data'].get('r_knee'))
        fig5 = self._create_joint_figure(kinematic_data['lhip'], "Left Hip", 'orange', 
                                       kinematic_data['patient_data'].get('l_hip'))
        fig6 = self._create_joint_figure(kinematic_data['rhip'], "Right Hip", 'darkblue', 
                                       kinematic_data['patient_data'].get('r_hip'))
        fig7 = self._create_joint_figure(kinematic_data['lankle'], "Left Ankle", 'orange', 
                                       kinematic_data['patient_data'].get('l_ankle'))
        fig8 = self._create_joint_figure(kinematic_data['rankle'], "Right Ankle", 'darkblue', 
                                       kinematic_data['patient_data'].get('r_ankle'))

        # Tampilkan dalam tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL PEMERIKSAAN AI"])

        with tab1:
            st.subheader("PELVIS")
            st.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')
            
            # Hitung mean differences
            if kinematic_data['patient_data'].get('l_pelvis'):
                maelpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_pelvis']) - kinematic_data['lpelvis']["mean"]))
                maerpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_pelvis']) - kinematic_data['rpelvis']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
                if kinematic_data['patient_data'].get('l_pelvis'):
                    st.write(f"**Perbedaan rata-rata sudut pelvis kiri (Anda vs Normal): {maelpelvis:.2f}°**")
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
                if kinematic_data['patient_data'].get('r_pelvis'):
                    st.write(f"**Perbedaan rata-rata sudut pelvis kanan (Anda vs Normal): {maerpelvis:.2f}°**")
                
        with tab2:
            st.subheader("KNEE")
            st.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
            
            if kinematic_data['patient_data'].get('l_knee'):
                maelknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_knee']) - kinematic_data['lknee']["mean"]))
                maerknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_knee']) - kinematic_data['rknee']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig3, use_container_width=True)
                if kinematic_data['patient_data'].get('l_knee'):
                    st.write(f"**Perbedaan rata-rata sudut lutut kiri (Anda vs Normal): {maelknee:.2f}°**")
            with col2:
                st.plotly_chart(fig4, use_container_width=True)
                if kinematic_data['patient_data'].get('r_knee'):
                    st.write(f"**Perbedaan rata-rata sudut lutut kanan (Anda vs Normal): {maerknee:.2f}°**")

        with tab3:
            st.subheader("HIP")
            st.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
            
            if kinematic_data['patient_data'].get('l_hip'):
                maelhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_hip']) - kinematic_data['lhip']["mean"]))
                maerhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_hip']) - kinematic_data['rhip']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig5, use_container_width=True)
                if kinematic_data['patient_data'].get('l_hip'):
                    st.write(f"**Perbedaan rata-rata sudut pinggul kiri (Anda vs Normal): {maelhip:.2f}°**")
            with col2:
                st.plotly_chart(fig6, use_container_width=True)
                if kinematic_data['patient_data'].get('r_hip'):
                    st.write(f"**Perbedaan rata-rata sudut pinggul kanan (Anda vs Normal): {maerhip:.2f}°**")

        with tab4:
            st.subheader("ANKLE")
            st.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
            
            if kinematic_data['patient_data'].get('l_ankle'):
                maelankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_ankle']) - kinematic_data['lankle']["mean"]))
                maerankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_ankle']) - kinematic_data['rankle']["mean"]))
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig7, use_container_width=True)
                if kinematic_data['patient_data'].get('l_ankle'):
                    st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kiri (Anda vs Normal): {maelankle:.2f}°**")
            with col2:
                st.plotly_chart(fig8, use_container_width=True)
                if kinematic_data['patient_data'].get('r_ankle'):
                    st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kanan (Anda vs Normal): {maerankle:.2f}°**")

        with tab5:
            self._show_ai_summary_tab()

    def _get_ai_summary_for_examination(self, pasien_id, tanggal_pemeriksaan):
        """Mendapatkan ringkasan AI yang dipilih dokter untuk pemeriksaan tertentu"""
        try:
            client = get_mongo_client()
            db = client['GaitDB']
            collection = db['ai_summaries']
            
            # Cari ringkasan AI berdasarkan pasien_id dan tanggal pemeriksaan
            # is_best_selected = True berarti ini hasil yang dipilih dokter
            ai_summary = collection.find_one({
                'pasien_id': pasien_id,
                'tanggal_pemeriksaan': tanggal_pemeriksaan.strftime("%Y-%m-%d"),
                'is_best_selected': True
            })
            
            return ai_summary

    def _show_ai_summary_tab(self, ai_summary, selected_date):
        """Menampilkan tab hasil pemeriksaan AI"""
        st.subheader(f"Hasil Analisis AI - {selected_date.strftime('%d %B %Y')}")
        
        # Tampilkan informasi dokter yang memeriksa
        dokter_nama = ai_summary.get('terapis_nama', 'Dokter')
        st.caption(f"Diproses oleh: Dr. {dokter_nama}")
        
        # Tampilkan prompt type dan variant
        prompt_type = ai_summary.get('prompt_type', 'A')
        variant = ai_summary.get('variant', '1')
        st.caption(f"Jenis Analisis: Prompt {prompt_type} - Varian {variant}")
        
        st.markdown("---")
        
        # Tampilkan ringkasan AI
        content = ai_summary.get('content', '')
        if content:
            st.markdown("### 📋 Hasil Analisis")
            st.markdown(content)
        else:
            st.warning("Konten ringkasan tidak tersedia.")
        
        st.markdown("---")
        
        # Tampilkan data MAE jika ada (opsional, bisa di-expand)
        mae_overall = ai_summary.get('mae_overall', {})
        mae_phases = ai_summary.get('mae_phases', [])
        
        if mae_overall or mae_phases:
            with st.expander("📊 Lihat Data MAE (Mean Absolute Error)"):
                # Tabel MAE Keseluruhan
                if mae_overall:
                    st.markdown("#### MAE Keseluruhan")
                    mae_overall_data = []
                    
                    # Pelvis
                    pelvis_left = mae_overall.get('pelvis_left', 0)
                    pelvis_right = mae_overall.get('pelvis_right', 0)
                    pelvis_avg = mae_overall.get('pelvis_avg', (pelvis_left + pelvis_right) / 2)
                    mae_overall_data.append({
                        'Joint': 'Pelvis',
                        'Kiri (°)': f"{pelvis_left:.2f}",
                        'Kanan (°)': f"{pelvis_right:.2f}",
                        'Rata-rata (°)': f"{pelvis_avg:.2f}"
                    })
                    
                    # Knee
                    knee_left = mae_overall.get('knee_left', 0)
                    knee_right = mae_overall.get('knee_right', 0)
                    knee_avg = mae_overall.get('knee_avg', (knee_left + knee_right) / 2)
                    mae_overall_data.append({
                        'Joint': 'Knee',
                        'Kiri (°)': f"{knee_left:.2f}",
                        'Kanan (°)': f"{knee_right:.2f}",
                        'Rata-rata (°)': f"{knee_avg:.2f}"
                    })
                    
                    # Hip
                    hip_left = mae_overall.get('hip_left', 0)
                    hip_right = mae_overall.get('hip_right', 0)
                    hip_avg = mae_overall.get('hip_avg', (hip_left + hip_right) / 2)
                    mae_overall_data.append({
                        'Joint': 'Hip',
                        'Kiri (°)': f"{hip_left:.2f}",
                        'Kanan (°)': f"{hip_right:.2f}",
                        'Rata-rata (°)': f"{hip_avg:.2f}"
                    })
                    
                    # Ankle
                    ankle_left = mae_overall.get('ankle_left', 0)
                    ankle_right = mae_overall.get('ankle_right', 0)
                    ankle_avg = mae_overall.get('ankle_avg', (ankle_left + ankle_right) / 2)
                    mae_overall_data.append({
                        'Joint': 'Ankle',
                        'Kiri (°)': f"{ankle_left:.2f}",
                        'Kanan (°)': f"{ankle_right:.2f}",
                        'Rata-rata (°)': f"{ankle_avg:.2f}"
                    })
                    
                    st.dataframe(pd.DataFrame(mae_overall_data), use_container_width=True, hide_index=True)
                
                # Tabel MAE per Fase
                if mae_phases:
                    st.markdown("#### MAE per Fase Gait")
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
                    
                    mae_phases_data = []
                    for phase_data in mae_phases:
                        phase = phase_data.get('phase', '')
                        if phase:
                            row = {
                                'Fase Gait': phase,
                                'Pelvis Kiri (°)': f"{phase_data.get('pelvis_left', 0):.2f}",
                                'Pelvis Kanan (°)': f"{phase_data.get('pelvis_right', 0):.2f}",
                                'Knee Kiri (°)': f"{phase_data.get('knee_left', 0):.2f}",
                                'Knee Kanan (°)': f"{phase_data.get('knee_right', 0):.2f}",
                                'Hip Kiri (°)': f"{phase_data.get('hip_left', 0):.2f}",
                                'Hip Kanan (°)': f"{phase_data.get('hip_right', 0):.2f}",
                                'Ankle Kiri (°)': f"{phase_data.get('ankle_left', 0):.2f}",
                                'Ankle Kanan (°)': f"{phase_data.get('ankle_right', 0):.2f}"
                            }
                            mae_phases_data.append(row)
                    
                    if mae_phases_data:
                        st.dataframe(pd.DataFrame(mae_phases_data), use_container_width=True, hide_index=True)
        
        # Footer
        st.caption(f"Tanggal analisis: {ai_summary.get('timestamp', datetime.now()).strftime('%d %B %Y %H:%M') if ai_summary.get('timestamp') else 'Tidak tersedia'}")
        
    def _dashboard_page(self):
        user_id = st.session_state.get("pasien_user_id")
        
        # Gunakan pencarian berdasarkan User ID
        profil = None
        for p in st.session_state["pasien_list"]:
            if p["User ID"] == user_id:
                profil = p
                break

        if profil:
            st.session_state.pasien_nama = profil["Nama Lengkap"]
         
        st.markdown("<h1 style='text-align: center; color: #560000;'>Dashboard Pemeriksaan GAIT</h1>", unsafe_allow_html=True)
        
        # Dapatkan semua tanggal pemeriksaan untuk pasien ini
        available_dates = self._get_all_pemeriksaan_dates(user_id)
        
        if not available_dates:
            st.warning("🔍 Silahkan periksa dulu ke dokter agar dashboard pemeriksaan GAIT anda muncul")
            return
        
        # Pilih tanggal pemeriksaan
        selected_date = st.selectbox(
            "Pilih Tanggal Pemeriksaan",
            options=available_dates,
            format_func=lambda x: x.strftime("%d %B %Y")
        )
        
        # Dapatkan data pemeriksaan untuk tanggal yang dipilih
        # PERBAIKAN: gunakan user_id, bukan nik
        pemeriksaan = self._get_pemeriksaan_data(user_id, selected_date)
        
        if not pemeriksaan:
            st.warning(f"❌ Tidak ada data pemeriksaan untuk tanggal {selected_date.strftime('%d %B %Y')}")
            return
        
        # Dapatkan data normal
        normal_data = self._get_normal_data()
        if normal_data is None:
            st.error("❌ Data normal belum tersedia. Silakan hubungi administrator.")
            return
        
        # Tampilkan informasi pemeriksaan
        patient_info = pemeriksaan.get('patient_info', {})
        st.markdown(f"### Hasil Pemeriksaan - {selected_date.strftime('%d %B %Y')}")
        
        # Proses data untuk visualisasi
        with st.spinner("Memuat visualisasi data..."):
            kinematic_data = self._process_kinematic_data(
                normal_data, 
                pemeriksaan.get('gait_data', {}).get('Norm Kinematics', {})
            )
            
            # Tampilkan visualisasi
            self._show_dashboard_visualization(kinematic_data)

    def _profile_page(self):
        user_id = st.session_state.get("pasien_user_id")
        
        # Gunakan pencarian berdasarkan User ID
        profil = None
        for p in st.session_state["pasien_list"]:
            if p["User ID"] == user_id:
                profil = p
                break
        
        st.markdown("<h1 style='text-align: center; color: #560000;'>Profil Pasien</h1>", unsafe_allow_html=True)
        
        if profil:
            # st.markdown("<div class='account-card'>", unsafe_allow_html=True)
            st.subheader("Data Profil")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**NIK:** {profil['User ID']}")
                st.markdown(f"**Nama Lengkap:** {profil['Nama Lengkap']}")
                st.markdown(f"**Tanggal Lahir:** {profil['Tanggal Lahir']}")
                
            with col2:
                st.markdown(f"**Jenis Kelamin:** {profil['Jenis Kelamin']}")
                st.markdown(f"**Role:** {profil['Role']}")
                st.markdown(f"**Tanggal Pendaftaran:** {profil['Tanggal Dibuat']}")
            # st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Data profil tidak ditemukan")

    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)
        if st.session_state.get("show_register", False):
            self.register_page.show()
            return
        
        if not st.session_state.get("pasien_logged_in", False):
            # Kalau belum login, tampilkan form login
            user_id, password, submit = login_form_pasien()
            if submit:
                # # Debug: lihat apa yang dimasukkan
                # st.write(f"Debug - Input user_id: '{user_id}'")
                # st.write(f"Debug - session_state pasien_auth keys: {list(st.session_state['pasien_auth'].keys())}")
                auth_result = self._authenticate_pasien(user_id, password)
               
                if auth_result:
                    st.session_state.pasien_logged_in = True
                    st.session_state.pasien_user_id = auth_result['user_id']  # Simpan sebagai user_id
                    st.session_state.pasien_nama = auth_result['nama_lengkap']
                    st.session_state.pasien_menu = "Dashboard"
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("NIK atau password salah!")
            return

        # ========== SIDEBAR MENU PASIEN ==========
        pasien_nama = st.session_state.get('pasien_nama', 'Pasien')
        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> {pasien_nama}</p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p class='sidebar-title'>Menu</p>", unsafe_allow_html=True)
        
        menu_list = ["Dashboard", "Profile", "Logout"]

        for menu in menu_list:
            if st.sidebar.button(
                menu, 
                use_container_width=True, type="primary"
                                 if st.session_state.pasien_menu == menu
                                 else "secondary"):
                st.session_state.pasien_menu = menu
                st.rerun()
        
        if st.session_state.pasien_menu == "Dashboard":
            self._dashboard_page()
        elif st.session_state.pasien_menu == "Profile":
            self._profile_page()
        elif st.session_state.pasien_menu == "Logout":
            st.session_state.pasien_logged_in = False
            st.session_state.pasien_user_id = None
            st.session_state.pasien_nama = None
            st.session_state.show_register = False
            st.session_state.role = None
            st.rerun()
