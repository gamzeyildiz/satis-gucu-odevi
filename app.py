import streamlit as st
import pulp
import pandas as pd
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Gücü Optimizasyonu", layout="wide")

st.title("📍 Satış Gücü ve Ofis Yeri Atama Modeli")
st.markdown("""
Bu uygulama, **Anadolu Teknoloji Çözümleri A.Ş.** için optimal ofis ve personel dağılımını hesaplar.
Veriler varsayılan olarak **YILDIZ_UYAR_N25110141_ödev3.xlsm** dosyasındaki ödev verilerine göre ayarlanmıştır.
""")

# --- 1. VERİ GİRİŞİ (SOL PANEL) ---
st.sidebar.header("⚙️ Parametre Ayarları")

# Excel Yükleme Opsiyonu
uploaded_file = st.sidebar.file_uploader("📂 Başka Excel Yükle (Opsiyonel)", type=["xlsx", "xlsm"])

# Maliyetler (Excel'den alınan varsayılanlar: 120k Maliyet, 40k Maaş, 120 Saat)
with st.sidebar.expander("💰 Maliyet ve Kapasite", expanded=True):
    # Sabit Maliyet Excel'de tek bir hücrede (N1) tanımlıydı: 120.000 TL
    sabit_maliyet_varsayilan = st.number_input("Sabit Ofis Maliyeti (TL)", value=120000, step=1000)
    # Personel Maaşı Excel'de (N2): 40.000 TL
    maas = st.number_input("Personel Maaşı (TL)", value=40000, step=1000)
    # Kapasite Excel'de: 120 Saat
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=120, step=10)
    big_m = 1000  # Büyük M sayısı

# --- VARSAYILAN VERİLER (EXCEL'DEN ÇEKİLENLER) ---
if uploaded_file is None:
    # Excel'den çıkarılan gerçek ilçe ve talep listesi
    ilceler_listesi = [
        "Kadışehri", "Sorgun", "Çayıralan", "Boğazlıyan", "Şefaatli", 
        "Çiçekdağı", "Kaman", "Mucur", "Sarıyahşi", "Ortaköy", 
        "Güzelyurt", "Eskil"
    ]
    # Excel'den okunan 'Müşteri Sayısı' (Talep)
    talepler_listesi = [150, 200, 150, 180, 120, 150, 360, 230, 180, 310, 240, 170]
    
    # Excel'deki 12x12 Hizmet Süresi Matrisi
    matrix_values = [
        [1, 3, 5, 6, 8, 10, 13, 14, 16, 17, 20, 23],
        [3, 1, 3, 5, 7, 8, 9, 11, 14, 16, 19, 21],
        [5, 3, 1, 2, 5, 8, 10, 12, 13, 15, 16, 17],
        [6, 5, 2, 1, 2, 5, 7, 9, 11, 12, 14, 16],
        [8, 7, 5, 2, 1, 3, 5, 8, 9, 11, 13, 14],
        [10, 8, 8, 5, 3, 1, 4, 6, 7, 10, 11, 13],
        [13, 9, 10, 7, 5, 4, 1, 3, 5, 8, 9, 11],
        [14, 11, 12, 9, 8, 6, 3, 1, 4, 6, 8, 10],
        [16, 14, 13, 11, 9, 7, 5, 4, 1, 3, 5, 8],
        [17, 16, 15, 12, 11, 10, 8, 6, 3, 1, 4, 7],
        [20, 19, 16, 14, 13, 11, 9, 8, 5, 4, 1, 5],
        [23, 21, 17, 16, 14, 13, 11, 9, 8, 7, 5, 1]
    ]

    varsayilan_veri = {
        'İlçe': ilceler_listesi,
        'Talep (Müşteri)': talepler_listesi,
        'Ofis Maliyeti (TL)': [sabit_maliyet_varsayilan] * 12
    }
    df = pd.DataFrame(varsayilan_veri)
    df_distance = pd.DataFrame(matrix_values, columns=ilceler_listesi, index=ilceler_listesi)

else:
    # Kullanıcı yeni dosya yüklerse
    try:
