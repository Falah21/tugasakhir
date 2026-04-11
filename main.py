# import streamlit as st
# from admin_page import AdminPage
# from pasien_page import PasienPage
# from terapis_page import TerapisPage
# # from css_style import load_css

# st.set_page_config(
#     page_title="Sistem Dashboard Gait Analysis",
#     page_icon="⛨",
#     layout="wide"  # biar bisa full width
# )

# # st.markdown(load_css(), unsafe_allow_html=True)

# # Inisialisasi session state
# if "role" not in st.session_state:
#     st.session_state.role = None

# # Fungsi navigasi biar gak perlu double click
# def go_to(role):
#     st.session_state.role = role
#     st.rerun()  # langsung rerun

# def main():
#     st.markdown("""
#         <style>
#         body {
#             background-color: #fafafa;
#         }

#         /* Judul utama pakai <h2> */
#         h2 {
#             text-align: center !important;
#             font-weight: 600 !important;
#             font-size: clamp(30px, 4vw, 44px) !important;
#             color: #560000 !important;  /* 🔥 warna maroon solid */
#             line-height: 1.2 !important;
#             margin-bottom: 0.1rem !important;
#             margin-top: 0rem !important;
#         }

#         /* Subjudul */
#         .subtitle {
#             text-align: center;
#             color: #333;
#             font-size: clamp(16px, 2vw, 22px);
#             font-weight: 500;
#             margin-top: 0rem;
#             margin-bottom: 1rem;
#         }

#         /* Section title */
#         .section-title {
#             text-align: center;
#             color: #444;
#             font-weight: 600;
#             font-size: clamp(16px, 2vw, 20px);
#             margin-bottom: 25px;
#         }

#         /* Wrapper tombol biar center dan responsif */
#         .button-wrapper {
#             display: flex;
#             justify-content: center;
#             align-items: center;
#             flex-wrap: wrap;
#             gap: 2rem; /* jarak antar tombol */
#             width: 100%;
#             # text-align: center;
#             margin-top: 1rem;
#         }

#         /* Tombol utama */
#         div[data-testid="stButton"] > button {
#             background-color: #ffffff;
#             border: 1px;
#             border-radius: 12px;
#             box-shadow: 0px 3px 8px rgba(0,0,0,0.1);
#             color: #222;
#             font-size: clamp(14px, 1.5vw, 18px);
#             font-weight: 600;
#             height: 100px;
#             width: 260px;
#             transition: all 0.2s ease-in-out;
#         }

#         /* Hover efek */
#         div[data-testid="stButton"] > button:hover {
#             transform: scale(1.05);
#             box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
#             background-color: #f9f9f9;
#             # color: white;
#         }

#         /* Tombol agar full di layar kecil */
#         @media (max-width: 768px) {
#             div[data-testid="stButton"] > button {
#                 width: 90%; /* tombol auto-lebar di HP */
#                 height: 90px;
#             }
#             .button-wrapper {
#                 flex-direction: column;
#                 gap: 1.2rem;
#             }
#         }
#         </style>
#     """, unsafe_allow_html=True)

#     # Konten utama
#     st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
#     st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
#     st.markdown("<p class='section-title'>Silahkan Pilih Role Terlebih Dahulu</p>", unsafe_allow_html=True)

#     # Tombol responsif di tengah
#     st.markdown("<div class='button-wrapper'>", unsafe_allow_html=True)
#     col1, col2, col3 = st.columns([1, 1, 1])

#     with col1:
#         if st.button("Admin"):
#             go_to("admin")
#     with col2:
#         if st.button("Dokter"):
#             go_to("terapis")
#     with col3:
#         if st.button("Pasien"):
#             go_to("pasien")
        
#     st.markdown("</div>", unsafe_allow_html=True)

#     # st.markdown("<div class='button-grid'>", unsafe_allow_html=True)

#     # if st.button("Admin"):
#     #     go_to("admin")
    
#     # if st.button("Dokter"):
#     #     go_to("terapis")
    
#     # if st.button("Pasien"):
#     #     go_to("pasien")
    
#     # st.markdown("</div>", unsafe_allow_html=True)

# # Routing role
# if st.session_state.role == "admin":
#     AdminPage().run()
# elif st.session_state.role == "terapis":
#     TerapisPage().run()
# elif st.session_state.role == "pasien":
#     PasienPage().run()
# else:
#     main()

import streamlit as st
from admin_page import AdminPage
from pasien_page import PasienPage
from terapis_page import TerapisPage

st.set_page_config(
    page_title="Sistem Dashboard Gait Analysis",
    page_icon="⛨",
    layout="wide"
)

# Inisialisasi session state
if "role" not in st.session_state:
    st.session_state.role = None

# Fungsi navigasi
def go_to(role):
    st.session_state.role = role
    st.rerun()

def main():
    st.markdown("""
        <style>
        body {
            background-color: #fafafa;
        }

        /* Judul utama */
        h2 {
            text-align: center !important;
            font-weight: 600 !important;
            font-size: clamp(30px, 4vw, 44px) !important;
            color: #560000 !important;
            line-height: 1.2 !important;
            margin-bottom: 0.1rem !important;
            margin-top: 0rem !important;
        }

        /* Subjudul */
        .subtitle {
            text-align: center;
            color: #333;
            font-size: clamp(16px, 2vw, 22px);
            font-weight: 500;
            margin-top: 0rem;
            margin-bottom: 1rem;
        }

        /* Section title */
        .section-title {
            text-align: center;
            color: #444;
            font-weight: 600;
            font-size: clamp(16px, 2vw, 20px);
            margin-bottom: 25px;
        }

        /* Container utama tombol - menggunakan CSS Grid */
        .button-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Grid system untuk tombol */
        .button-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2rem;
            justify-items: center;
            align-items: center;
            margin-top: 1rem;
        }
        
        /* Styling untuk wrapper tombol Streamlit */
        .stButton {
            width: 100%;
            max-width: 280px;
        }
        
        /* Tombol utama */
        div[data-testid="stButton"] > button {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 12px;
            box-shadow: 0px 3px 8px rgba(0,0,0,0.1);
            color: #222;
            font-size: clamp(14px, 1.5vw, 18px);
            font-weight: 600;
            height: 100px;
            width: 100%;
            min-width: 180px;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
            white-space: nowrap;
            padding: 0 20px;
        }
        
        /* Hover efek */
        div[data-testid="stButton"] > button:hover {
            transform: scale(1.05);
            box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
            background-color: #f9f9f9;
            border-color: #560000;
            color: #560000;
        }
        
        /* Active/click effect */
        div[data-testid="stButton"] > button:active {
            transform: scale(0.98);
        }
        
        /* Responsif untuk tablet (layar sedang) */
        @media (max-width: 768px) {
            .button-grid {
                grid-template-columns: repeat(3, 1fr);
                gap: 1.5rem;
            }
            
            div[data-testid="stButton"] > button {
                height: 90px;
                min-width: 140px;
                font-size: 16px;
                white-space: normal;
                word-break: keep-all;
            }
        }
        
        /* Responsif untuk mobile (layar kecil) */
        @media (max-width: 640px) {
            .button-grid {
                grid-template-columns: 1fr;
                gap: 1rem;
                max-width: 300px;
                margin-left: auto;
                margin-right: auto;
            }
            
            div[data-testid="stButton"] > button {
                height: 80px;
                width: 100%;
                min-width: auto;
                font-size: 18px;
            }
            
            .stButton {
                max-width: 100%;
            }
        }
        
        /* Untuk layar sangat besar */
        @media (min-width: 1400px) {
            .button-grid {
                gap: 3rem;
            }
            
            div[data-testid="stButton"] > button {
                height: 120px;
                font-size: 20px;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # Konten utama
    st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    st.markdown("<p class='section-title'>Silahkan Pilih Role Terlebih Dahulu</p>", unsafe_allow_html=True)

    # Tombol responsif menggunakan grid
    st.markdown("<div class='button-container'><div class='button-grid'>", unsafe_allow_html=True)
    
    # Kolom untuk tombol - menggunakan columns dengan rasio yang sama
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        if st.button("👤 Admin", key="btn_admin", use_container_width=True):
            go_to("admin")
    
    with col2:
        if st.button("👨‍⚕️ Dokter", key="btn_dokter", use_container_width=True):
            go_to("terapis")
    
    with col3:
        if st.button("📋 Pasien", key="btn_pasien", use_container_width=True):
            go_to("pasien")
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# Routing role
if st.session_state.role == "admin":
    AdminPage().run()
elif st.session_state.role == "terapis":
    TerapisPage().run()
elif st.session_state.role == "pasien":
    PasienPage().run()
else:
    main()
