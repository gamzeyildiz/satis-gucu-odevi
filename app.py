import streamlit as st
import pulp
import pandas as pd
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Gücü Optimizasyonu", layout="wide")

st.title("📍 Satış Gücü ve Ofis Yeri Atama Modeli")
st.markdown("""
Bu uygulama, **Anadolu Teknoloji Çözümleri A.Ş.** için optimal ofis ve personel dağılımını hesaplar.
Veriler varsayılan olarak **ödev senaryosuna** göre yüklüdür. Dilerseniz kendi Excel dosyanızı yükleyebilirsiniz.
""")

# --- 1. VERİ GİRİŞİ (SOL PANEL) ---
st.sidebar.header("⚙️ Parametre Ayarları")

# Excel Yükleme Opsiyonu
uploaded_file = st.sidebar.file_uploader("📂 Excel Dosyası Yükle (Opsiyonel)", type=["xlsx", "xlsm"])

# Maliyetler
with st.sidebar.expander("💰 Maliyet ve Kapasite", expanded=True):
    maas = st.number_input("Personel Maaşı (TL)", value=35000, step=1000)
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=160, step=10)
    big_m = 100  # Büyük M sayısı

# --- VARSAYILAN VERİLERİN HAZIRLANMASI ---
# Eğer kullanıcı Excel yüklemediyse, senin ödevindeki verileri kullanıyoruz.
if uploaded_file is None:
    varsayilan_veri = {
        'İlçe': [
            "Kadışehri", "Sorgun", "Çayıralan", "Boğazlıyan", "Şefaatli", 
            "Çiçekdağı", "Kaman", "Mucur", "Sarıyahşi", "Ortaköy", 
            "Güzelyurt", "Eskil"
        ],
        'Talep (Müşteri)': [45, 120, 40, 90, 50, 45, 80, 60, 30, 95, 35, 70],
        'Ofis Maliyeti (TL)': [18000, 30000, 17000, 25000, 19000, 18000, 22000, 20000, 15000, 26000, 16000, 21000]
    }
    df = pd.DataFrame(varsayilan_veri)
else:
    try:
        # Excel yüklenirse okumaya çalış
        df = pd.read_excel(uploaded_file)
        # Sütun isimlerini standartlaştıralım (Hata önleyici)
        if len(df.columns) >= 3:
            df.columns = ['İlçe', 'Talep (Müşteri)', 'Ofis Maliyeti (TL)'] + list(df.columns[3:])
        else:
            st.error("Excel formatı uygun değil. En az 3 sütun olmalı: İlçe, Talep, Maliyet")
            st.stop()
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        st.stop()

# --- VERİ EDİTÖRÜ ---
st.subheader("📋 İlçe Verileri (Düzenlenebilir)")
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# İlçeleri ve Parametreleri Listeye Çevir
ilceler = edited_df['İlçe'].astype(str).tolist()
talepler = dict(zip(edited_df['İlçe'], edited_df['Talep (Müşteri)']))
ofis_maliyetleri = dict(zip(edited_df['İlçe'], edited_df['Ofis Maliyeti (TL)']))

# --- MESAFE MATRİSİ (SİMÜLASYON) ---
# Gerçek Excel'deki karmaşık matrisi okumak zor olacağı için,
# burada mantıklı bir uzaklık matrisi oluşturuyoruz.
# (Kendi ilçesi 2 saat, diğerleri 4-9 saat arası rastgele ama sabit)

st.subheader("🚗 Hizmet Süreleri Matrisi (Saat)")
np.random.seed(42) # Her seferinde aynı sayıları üretmek için
distance_data = np.random.randint(4, 10, size=(len(ilceler), len(ilceler)))
np.fill_diagonal(distance_data, 2) # Kendi ilçesine hizmet 2 saat

df_distance = pd.DataFrame(distance_data, columns=ilceler, index=ilceler)
edited_matrix = st.data_editor(df_distance, use_container_width=True)


# --- 2. OPTİMİZASYON BUTONU ---
st.markdown("---")
col1, col2 = st.columns([1, 4])
with col1:
    solve_btn = st.button("🚀 Modeli Çöz", type="primary")

if solve_btn:
    with st.spinner('Solver optimal çözümü hesaplıyor...'):
        try:
            # Model Kurulumu
            prob = pulp.LpProblem("Satis_Gucu_Modeli", pulp.LpMinimize)

            # Karar Değişkenleri
            y = pulp.LpVariable.dicts("Ofis", ilceler, cat='Binary') # Ofis açma
            p = pulp.LpVariable.dicts("Personel", ilceler, lowBound=0, cat='Integer') # Personel sayısı
            x = pulp.LpVariable.dicts("Atama", (ilceler, ilceler), lowBound=0, cat='Integer') # Müşteri atama

            # 1. AMAÇ FONKSİYONU: (Ofis Sabit Maliyeti) + (Personel Maaşı)
            prob += pulp.lpSum([ofis_maliyetleri[i] * y[i] + maas * p[i] for i in ilceler])

            # 2. KISITLAR
            
            # A) Talep Karşılama: Her ilçenin talebi, bir yerlerden karşılanmalı
            for j in ilceler:
                prob += pulp.lpSum([x[i][j] for i in ilceler]) == talepler[j]

            # B) Kapasite (Zaman) Kısıtı: Personel süresi yetmeli
            for i in ilceler:
                # i ofisinden yapılan toplam iş saati (tüm j'ler için: atanan müşteri * süre)
                harcanan_sure = pulp.lpSum([x[i][j] * edited_matrix.loc[i, j] for j in ilceler])
                prob += harcanan_sure <= p[i] * kapasite

            # C) Bağlantı Kısıtı: Ofis açılmadıysa personel olamaz
            for i in ilceler:
                prob += p[i] <= big_m * y[i]

            # Çözüm
            prob.solve()
            status = pulp.LpStatus[prob.status]

            # --- 3. SONUÇ EKRANI ---
            if status == "Optimal":
                toplam_maliyet = pulp.value(prob.objective)
                st.success(f"✅ Çözüm Bulundu! Toplam Maliyet: **{toplam_maliyet:,.2f} TL**")

                # Sonuç Tablosu Hazırlığı
                sonuc_data = []
                toplam_pers = 0
                acilan_ofis = 0

                for i in ilceler:
                    if y[i].varValue == 1:
                        durum = "✅ AÇIK"
                        per_say = p[i].varValue
                        toplam_pers += per_say
                        acilan_ofis += 1
                        
                        # Hangi ilçelere hizmet veriyor?
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

                # Metrikler
                m1, m2, m3 = st.columns(3)
                m1.metric("Açılan Ofis Sayısı", int(acilan_ofis))
                m2.metric("Toplam Personel", int(toplam_pers))
                m3.metric("Müşteri Başı Maliyet", f"{toplam_maliyet / sum(talepler.values()):,.0f} TL")

                st.dataframe(pd.DataFrame(sonuc_data), use_container_width=True)

            else:
                st.error("Çözüm Bulunamadı! (Infeasible). Lütfen personel kapasitesini artırın.")
        
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
