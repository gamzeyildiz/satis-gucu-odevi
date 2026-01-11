import streamlit as st
import pulp
import pandas as pd
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Gücü Optimizasyonu", layout="wide")

st.title("📍 Satış Gücü ve Ofis Yeri Atama Modeli")
st.markdown("""
Bu uygulama, **Anadolu Teknoloji Çözümleri A.Ş.** için optimal ofis ve personel dağılımını hesaplar.
Veriler varsayılan olarak ödev verilerine göre ayarlanmıştır.
""")

# --- 1. VERİ GİRİŞİ (SOL PANEL) ---
st.sidebar.header("⚙️ Parametre Ayarları")

# Excel Yükleme Opsiyonu
uploaded_file = st.sidebar.file_uploader("📂 Başka Excel Yükle (Opsiyonel)", type=["xlsx", "xlsm"])

# Maliyetler (Varsayılanlar: 120k Maliyet, 40k Maaş, 120 Saat)
with st.sidebar.expander("💰 Maliyet ve Kapasite", expanded=True):
    sabit_maliyet_varsayilan = st.number_input("Sabit Ofis Maliyeti (TL)", value=120000, step=1000)
    maas = st.number_input("Personel Maaşı (TL)", value=40000, step=1000)
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=120, step=10)
    big_m = 1000  # Büyük M sayısı

# --- VARSAYILAN VERİLERİN OLUŞTURULMASI ---
if uploaded_file is None:
    # 1. İlçe Listesi
    ilceler_listesi = [
        "Kadışehri", "Sorgun", "Çayıralan", "Boğazlıyan", "Şefaatli", 
        "Çiçekdağı", "Kaman", "Mucur", "Sarıyahşi", "Ortaköy", 
        "Güzelyurt", "Eskil"
    ]
    
    # 2. Talepler
    talepler_listesi = [150, 200, 150, 180, 120, 150, 360, 230, 180, 310, 240, 170]
    
    # 3. Hizmet Süreleri Matrisi (12x12)
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
                # Talep Karşılama
                prob += pulp.lpSum([x[i][j] for i in ilceler]) == talepler[j]

            for i in ilceler:
                # Kapasite
                harcanan_sure = pulp.lpSum([x[i][j] * edited_matrix.loc[i, j] for j in ilceler])
                prob += harcanan_sure <= p[i] * kapasite
                # Bağlantı (Ofis-Personel)
                prob += p[i] <= big_m * y[i]

            # Çöz
            prob.solve()
            status = pulp.LpStatus[prob.status]

            # --- SONUÇLAR ---
            if status == "Optimal":
                toplam_maliyet = pulp.value(prob.objective)
                st.success(f"✅ Çözüm Bulundu! Toplam Maliyet: **{toplam_maliyet:,.2f} TL**")

                sonuc_data = []
                toplam_pers = 0
                acilan_ofis = 0

                for i in ilceler:
                    if y[i].varValue == 1:
                        durum = "✅ AÇIK"
                        per_say = p[i].varValue
                        toplam_pers += per_say
                        acilan_ofis += 1
                        
                        hizmet_listesi = []
                        for j in ilceler:
                            val = x[i][j].varValue
                            if val > 0:
                                hizmet_listesi.append(f"{j} ({int(val)})")
                        hizmet_str = ", ".join(hizmet_listesi)
                    else:
                        durum = "❌ KAPALI"
                        per_say = 0
                        hizmet_str = "-"
                    
                    sonuc_data.append({
                        "İlçe": i,
                        "Ofis Durumu": durum,
                        "Personel Sayısı": int(per_say),
                        "Hizmet Verilen Bölgeler": hizmet_str
                    })

                m1, m2, m3 = st.columns(3)
                m1.metric("Açılan Ofis Sayısı", int(acilan_ofis))
                m2.metric("Toplam Personel", int(toplam_pers))
                if sum(talepler.values()) > 0:
                     m3.metric(
                         "Müşteri Başı Maliyet", 
                         f"{toplam_maliyet / sum(talepler.values()):,.0f} TL"
                     )

                # Düzeltilmiş Satır (Parantez Hatasını Önlemek İçin Bölünmüş)
                st.dataframe(
                    pd.DataFrame(sonuc_data), 
                    use_container_width=True
                )

            else:
                st.error("Çözüm Bulunamadı! (Infeasible). Lütfen personel kapasitesini artırın.")
        
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
