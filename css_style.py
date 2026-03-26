import streamlit as st

def load_css():
    """Mengembalikan string CSS untuk semua halaman"""
    return """
    <style>
        /* ===== GLOBAL STYLES ===== */
        .block-container {
            padding-top: 3vh !important;
            padding-bottom: 2rem !important;
            max-width: 90vw;
            margin: auto;
        }
        
        /* Tombol back tetap */
        .back-fixed {
            position: fixed;
            top: 30px;
            left: 40px;
            background-color: #a30000;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            z-index: 999;
        }
        .back-fixed:hover {
            background-color: #660000;
        }

        /* Responsive */
        @media (max-width: 900px) {
            .block-container {
                width: 95%;
                max-width: 95vw;
                padding-top: 6vh !important;
            }
        }

        /* Typography */
        h2 {
            color: #560000 !important;
            text-align: center;
            margin-bottom: 0rem !important;
            font-size: clamp(1.8rem, 2.5vw, 2.5rem);
        }

        .subtitle {
            text-align: center;
            font-size: clamp(1rem, 1.5vw, 1.15rem);
            color: #222;
            margin-top: 0rem !important;
            margin-bottom: 0.4rem !important;
        }
        
        hr.custom {
            margin-top: 0.4rem !important;
            margin-bottom: 1rem !important;
            border: 0;
            border-top: 1.5px solid #ccc;
            width: 60%;
            margin-left: auto;
            margin-right: auto;
        }

        /* Form elements */
        label, .stTextInput label {
            font-weight: 600 !important;
        }

        .stTextInput>div>div>input,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox select {
            background-color: #f3ebeb !important;
            border: 1px solid #e2dada !important;
            border-radius: 6px;
            height: 42px;
            font-size: 1rem;
        }

        /* Buttons */
        .btn-primary {
            width: 100% !important;
            border-radius: 6px;
            background-color: #fff !important;
            color: #000 !important;
            border: 1px solid #ddd !important;
            font-weight: 500;
            height: 42px;
            font-size: 1rem;
        }

        .btn-primary:hover {
            border-color: #5b0a0a !important;
            color: #5b0a0a !important;
        }

        .btn-red {
            background-color: #a30000 !important;
            color: white !important;
            border: none !important;
        }
        
        .btn-red:hover {
            background-color: #660000 !important;
        }

        /* Links */
        a.forgot {
            color: #a30000 !important;
            font-size: 0.9rem;
            text-decoration: none;
        }

        p.register-link, p.login-link {
            color: #a30000 !important;
            font-weight: 600;
            text-align: center;
            margin-top: 1rem;
            margin-bottom: 0.4rem;
        }

        p.footer {
            text-align: center;
            font-size: 0.85rem;
            color: #444;
            margin-top: 1rem;
        }

        /* Tables */
        .dataframe {
            border: 1px solid #ddd !important;
            border-radius: 8px !important;
        }
        
        .action-buttons {
            display: flex;
            gap: 5px;
        }
        
        .stButton button {
            border-radius: 6px;
        }

        /* Animations */
        button:hover, .btn-primary:hover, .btn-red:hover {
            transition: all 0.1s ease-in-out;
        }

        /* Layout khusus untuk halaman register */
        .register-container {
            max-width: 700px !important;
        }

        /* ===== SIDEBAR STYLES (DARI KODE YANG ANDA KIRIM) ===== */
        body { background-color: #f9f9f9; }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #560000;
        }

        .sidebar-title {
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 10px 20px;
        }

        .sidebar-subtitle {
            color: #ddd;
            font-size: 14px;
            padding-left: 20px;
            margin-bottom: 10px;
        }

        .filter-box {
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 10px;
        }

        /* Mengubah warna teks di sidebar menjadi putih */
        section[data-testid="stSidebar"] div[class*="stRadio"] label {
            color: white !important;
        }
        
        section[data-testid="stSidebar"] div[class*="stRadio"] div[role="radiogroup"] {
            color: white !important;
        }
        
        /* Mengubah warna teks untuk semua elemen di sidebar */
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        
        /* Khusus untuk radio button yang dipilih */
        section[data-testid="stSidebar"] div[class*="stRadio"] div[data-testid="stMarkdownContainer"] p {
            color: white !important;
        }

        /* FIX: Button sidebar agar tulisan selalu terlihat */
        section[data-testid="stSidebar"] button {
            background-color: #6b0000 !important;
            color: #ffffff !important;
            border-radius: 8px;
            height: 42px;
            font-weight: 600;
            border: none;
        }
        
        /* Hover */
        section[data-testid="stSidebar"] button:hover {
            background-color: #8a0000 !important;
            color: #ffffff !important;
        }
        
        /* Tombol aktif (menu terpilih) */
        section[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #ffffff !important;
            color: #560000 !important;
            border: 2px solid #560000 !important;
        }
        section[data-testid="stSidebar"] button * {
            color: inherit !important;
        }

        /* Main content area */
        .main .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* Stats cards */
        .stats-card {
            background: #ffffff !important;
            color: #000000 !important;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #ddd;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stats-number {
            font-size: 2rem;
            font-weight: bold;
            margin: 10px 0;
        }

        /* Panel styling */
        .panel {
            background-color: #fff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        /* Account card */
        .account-card {
            background-color: #fff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-left: 4px solid #560000;
        }

        /* ===== CARD STYLES YANG SUDAH ADA ===== */
        /* Stats cards, panel, account-card sudah di atas, jadi bagian ini bisa dihapus atau dibiarkan saja */
        /* Tapi karena sudah ada di atas, saya komentar saja biar tidak double */
        /*
        .stats-card {
            background: #ffffff !important;
            color: #000000 !important;
            padding: 20px !important;
            border-radius: 10px !important;
            text-align: center !important;
            border: 1px solid #ddd !important;
            margin-bottom: 15px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        
        .stats-number {
            font-size: 2rem !important;
            font-weight: bold !important;
            margin: 10px 0 !important;
            color: #560000 !important;
        }
        */

        /* ===== DASHBOARD STYLES ===== */
        .dashboard-container {
            background-color: #f9f9f9 !important;
            min-height: 100vh !important;
        }

        .metric-card {
            background: white !important;
            border-radius: 10px !important;
            padding: 20px !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        }

        /* ===== FORMS ===== */
        .form-container {
            background: white !important;
            padding: 25px !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
            margin-bottom: 20px !important;
        }

        /* ===== TABLES ===== */
        .dataframe-container {
            background: white !important;
            padding: 15px !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        }

        /* ===== ALERTS ===== */
        .alert-success {
            background-color: #d4edda !important;
            color: #155724 !important;
            border: 1px solid #c3e6cb !important;
            border-radius: 8px !important;
            padding: 12px !important;
            margin: 10px 0 !important;
        }

        .alert-warning {
            background-color: #fff3cd !important;
            color: #856404 !important;
            border: 1px solid #ffeaa7 !important;
            border-radius: 8px !important;
            padding: 12px !important;
            margin: 10px 0 !important;
        }

        .alert-error {
            background-color: #f8d7da !important;
            color: #721c24 !important;
            border: 1px solid #f5c6cb !important;
            border-radius: 8px !important;
            padding: 12px !important;
            margin: 10px 0 !important;
        }

        .alert-info {
            background-color: #d1ecf1 !important;
            color: #0c5460 !important;
            border: 1px solid #bee5eb !important;
            border-radius: 8px !important;
            padding: 12px !important;
            margin: 10px 0 !important;
        }

        /* ===== ICONS ===== */
        .icon-large {
            font-size: 2rem !important;
            margin-right: 10px !important;
        }

        .icon-medium {
            font-size: 1.5rem !important;
            margin-right: 8px !important;
        }

        /* ===== SPACING UTILITIES ===== */
        .mt-1 { margin-top: 0.25rem !important; }
        .mt-2 { margin-top: 0.5rem !important; }
        .mt-3 { margin-top: 1rem !important; }
        .mt-4 { margin-top: 1.5rem !important; }
        .mt-5 { margin-top: 2rem !important; }
        
        .mb-1 { margin-bottom: 0.25rem !important; }
        .mb-2 { margin-bottom: 0.5rem !important; }
        .mb-3 { margin-bottom: 1rem !important; }
        .mb-4 { margin-bottom: 1.5rem !important; }
        .mb-5 { margin-bottom: 2rem !important; }
        
        .p-1 { padding: 0.25rem !important; }
        .p-2 { padding: 0.5rem !important; }
        .p-3 { padding: 1rem !important; }
        .p-4 { padding: 1.5rem !important; }
        .p-5 { padding: 2rem !important; }
    </style>
    """
