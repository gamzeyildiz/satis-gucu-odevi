import streamlit as st
import pulp
import pandas as pd
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Gücü Optimizasyonu", layout="wide")

st.title("📍 Satış Gücü ve Ofis Yeri Atama Modeli")
st.markdown("""
Bu uygulama, **Anadolu Teknoloji Çözümleri A.Ş.** için optimal ofis ve personel dağılımını hesaplar.
**Not:** Veriler ve kısıtlar (özellikle Personel Sınırı = 8) yüklediğiniz Excel dosyasıyla birebir eşlenmiştir.
""")

# --- 1. VERİ GİRİŞİ (SOL PANEL) ---
st.sidebar.header("⚙️ Parametre Ayarları")

# Excel Yükleme Opsiyonu
uploaded_file = st.sidebar.file_uploader("📂 Başka Excel Yükle (Opsiyonel)", type=["xlsx", "xlsm"])

# Maliyetler ve Kısıtlar (Excel'deki Değerler)
with st.sidebar.expander("💰 Maliyet ve Kapasite", expanded=True):
    sabit_maliyet_varsayilan = st.number_input("Sabit Ofis Maliyeti (TL)", value=120000, step=1000)
    maas = st.number_input("Personel Maaşı (TL)", value=40000, step=1000)
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=120, step=10)
    # Excel'de bu değer 8 olarak görünüyor. Bu çok kritik bir kısıt!
    big_m = st.number_input("Maksimum Personel (Big M)", value=8, step=1, help="Bir ofiste çalışabilecek maksimum kişi sayısı.")

# --- VARSAYILAN VERİLERİN OLUŞTURULMASI ---
if uploaded_file is None:
    # 1. İlçe Listesi (Excel'den)
    ilceler_listesi = [
        "Kadışehri", "Sorgun", "Çayıralan", "Boğazlıyan", "Şefaatli", 
        "Çiçekdağı", "Kaman", "Mucur", "Sarıyahşi", "Ortaköy", 
        "Güzelyurt", "Eskil"
    ]
    
    # 2. Talepler (Excel'den: 150, 200... şeklinde giden liste)
    talepler_listesi = [150, 200, 150, 180, 120, 150, 360, 230, 180, 310, 240, 170]
    
    # 3. Hizmet Süreleri Matrisi (12x12 - Excel'deki tablonun aynısı)
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

    # DataFrame Oluşturma
    varsayilan_veri = {
        'İlçe': ilceler_listesi,
        'Talep (Müşteri)': talepler_listesi,
        'Ofis Maliyeti (TL)': [sabit_maliyet_varsayilan] * 12
    }
    df = pd.DataFrame(varsayilan_veri)
    df_distance = pd.DataFrame(
        matrix_values, 
        columns=ilceler_listesi, 
        index=ilceler_listesi
    )

else:
    # Kullanıcı dosya yüklerse çalışacak kısım
    try:
        df = pd.read_excel(uploaded_file)
        # Format kontrolü
        if len(df.columns) >= 3:
            df.columns = ['İlçe', 'Talep (Müşteri)', 'Ofis Maliyeti (TL)'] + list(df.columns[3:])
            ilceler_listesi = df['İlçe'].astype(str).tolist()
            # Yüklenen dosyada matris yoksa rastgele oluştur
            df_distance = pd.DataFrame(
                np.random.randint(2, 10, size=(len(df), len(df))), 
                columns=ilceler_listesi, 
                index=ilceler_listesi
            )
            np.fill_diagonal(df_distance.values, 1)
        else:
            st.error("Excel formatı uygun değil. En az 3 sütun olmalı.")
            st.stop()
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        st.stop()

# --- VERİ EDİTÖRÜ GÖSTERİMİ ---
st.subheader("📋 İlçe Verileri (Düzenlenebilir)")
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# Güncel Listeleri Al
ilceler = edited_df['İlçe'].astype(str).tolist()
talepler = dict(zip(edited_df['İlçe'], edited_df['Talep (Müşteri)']))
ofis_maliyetleri = dict(zip(edited_df['İlçe'], edited_df['Ofis Maliyeti (TL)']))

# --- MATRİS GÖSTERİMİ ---
st.subheader("🚗 Hizmet Süreleri Matrisi (Saat)")
edited_matrix = st.data_editor(df_distance, use_container_width=True)

# --- 2. OPTİMİZASYON BUTONU ---
st.markdown("---")
solve_btn = st.button("🚀 Modeli Çöz", type="primary")

if solve_btn:
    with st.spinner('Solver optimal çözümü hesaplıyor...'):
        try:
            # Model Kurulumu
            prob = pulp.LpProblem("Satis_Gucu_Modeli", pulp.LpMinimize)

            # Değişkenler
            y = pulp.LpVariable.dicts("Ofis", ilceler, cat='Binary')
            p = pulp.LpVariable.dicts("Personel", ilceler, lowBound=0, cat='Integer')
            x = pulp.LpVariable.dicts("Atama", (ilceler, ilceler), lowBound=0, cat='Integer')

            # Amaç Fonksiyonu
            prob += pulp.lpSum([ofis_maliyetleri[i] * y[i] + maas * p[i] for i in ilceler])

            # Kısıtlar
            for j in ilceler:
                # Talep
