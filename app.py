import streamlit as st
import pulp
import pandas as pd
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Gücü Optimizasyonu", layout="wide")

st.title("📍 Satış Gücü ve Ofis Yeri Atama Modeli")
st.markdown("""
Bu uygulama, **Anadolu Teknoloji Çözümleri A.Ş.** için en az maliyetli ofis ve personel dağılımını hesaplar.
Sol taraftaki menüden maliyetleri ve talepleri değiştirip **"Modeli Çöz"** butonuna basarak sonucu görebilirsiniz.
""")

# --- 1. VERİ GİRİŞİ (SOL PANEL) ---
st.sidebar.header("⚙️ Parametre Ayarları")

# Maliyetler
with st.sidebar.expander("💰 Maliyet ve Kapasite", expanded=True):
    maas = st.number_input("Personel Maaşı (TL)", value=35000, step=1000)
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=160, step=10)
    big_m = 100  # Büyük sayı

# İlçeler Listesi
ilceler = [
    "Kadışehri", "Sorgun", "Çayıralan", "Boğazlıyan", "Şefaatli", 
    "Çiçekdağı", "Kaman", "Mucur", "Sarıyahşi", "Ortaköy", 
    "Güzelyurt", "Eskil"
]

# Talep ve Ofis Maliyeti Girişi
st.sidebar.subheader("🏙️ İlçe Verileri")
df_input = pd.DataFrame({
    'İlçe': ilceler,
    'Talep (Müşteri)': [45, 120, 40, 90, 50, 45, 80, 60, 30, 95, 35, 70],
    'Ofis Maliyeti (TL)': [18000, 30000, 17000, 25000, 19000, 18000, 22000, 20000, 15000, 26000, 16000, 21000]
})
edited_df = st.sidebar.data_editor(df_input, num_rows="fixed")

# Mesafe Matrisi (Otomatik Simülasyon)
# Gerçek hayatta bu veriyi Excel'den okutabiliriz, burada simüle ediyoruz.
@st.cache_data
def get_distance_matrix():
    # Rastgele ama tutarlı süreler (Kendi ilçesi 2 saat, diğerleri 3-9 saat arası)
    np.random.seed(42)
    matrix = pd.DataFrame(
        np.random.randint(3, 10, size=(12, 12)), 
        columns=ilceler, index=ilceler
    )
    np.fill_diagonal(matrix.values, 2) # Kendi kendine hizmet süresi
    return matrix

mesafe_matrisi = get_distance_matrix()

# --- 2. OPTİMİZASYON MODELİ ---

col1, col2 = st.columns([1, 2])

with col1:
    st.info("👇 Verileri ayarladıktan sonra butona basın.")
    solve_btn = st.button("🚀 Modeli Çöz ve Optimize Et", type="primary")

if solve_btn:
    with st.spinner('Solver en uygun ofis yerlerini hesaplıyor...'):
        # Modeli Kur
        prob = pulp.LpProblem("Satis_Gucu_Modeli", pulp.LpMinimize)

        # Değişkenler
        # y[i]: Ofis açılsın mı? (0/1)
        y = pulp.LpVariable.dicts("Ofis_Acma", ilceler, cat='Binary')
        # p[i]: Personel sayısı (Tamsayı)
        p = pulp.LpVariable.dicts("Personel_Sayisi", ilceler, lowBound=0, cat='Integer')
        # x[i][j]: i ofisinden j ilçesine kaç müşteriye bakılıyor?
        x = pulp.LpVariable.dicts("Atama", (ilceler, ilceler), lowBound=0, cat='Integer')

        # Parametreleri Al
        talepler = dict(zip(edited_df['İlçe'], edited_df['Talep (Müşteri)']))
        ofis_maliyetleri = dict(zip(edited_df['İlçe'], edited_df['Ofis Maliyeti (TL)']))

        # AMAÇ FONKSİYONU: Min (Ofis Maliyeti + Personel Maaşı)
        prob += pulp.lpSum([ofis_maliyetleri[i] * y[i] + maas * p[i] for i in ilceler])

        # KISITLAR
        
        # 1. Talep Karşılama: Her ilçenin talebi tamamen karşılanmalı
        for j in ilceler:
            prob += pulp.lpSum([x[i][j] for i in ilceler]) == talepler[j]

        # 2. Kapasite Kısıtı: Bir ofisteki personel, atandığı işlere yetişebilmeli
        for i in ilceler:
            harcanan_sure = pulp.lpSum([x[i][j] * mesafe_matrisi.loc[i, j] for j in ilceler])
            prob += harcanan_sure <= p[i] * kapasite

        # 3. Bağlantı Kısıtı: Ofis yoksa personel olamaz (veya personel varsa ofis açılmalı)
        for i in ilceler:
            prob += p[i] <= big_m * y[i]

        # Çöz
        prob.solve()
        durum = pulp.LpStatus[prob.status]

    # --- 3. SONUÇ EKRANI ---
    if durum == "Optimal":
        st.success(f"✅ Çözüm Bulundu! Toplam Maliyet: **{pulp.value(prob.objective):,.2f} TL**")
        
        # Sonuçları Tablolaştır
        sonuc_listesi = []
        for i in ilceler:
            acik_mi = y[i].varValue
            per_say = p[i].varValue
            if acik_mi == 1:
                # Bu ofis nerelere hizmet veriyor?
                hizmet_verilenler = []
                for j in ilceler:
                    if x[i][j].varValue > 0:
                        hizmet_verilenler.append(f"{j} ({int(x[i][j].varValue)})")
                
                sonuc_listesi.append({
                    "İlçe Ofisi": i,
                    "Durum": "AÇIK 🟢",
                    "Personel": int(per_say),
                    "Hizmet Verilen Yerler": ", ".join(hizmet_verilenler)
                })
            else:
                sonuc_listesi.append({
                    "İlçe Ofisi": i,
                    "Durum": "KAPALI 🔴",
                    "Personel": "-",
                    "Hizmet Verilen Yerler": "-"
                })
        
        st.dataframe(pd.DataFrame(sonuc_listesi))
        
        # Grafiksel Gösterim (Basit Metrikler)
        m1, m2, m3 = st.columns(3)
        toplam_ofis = sum([y[i].varValue for i in ilceler])
        toplam_personel = sum([p[i].varValue for i in ilceler])
        
        m1.metric("Açılacak Ofis Sayısı", int(toplam_ofis))
        m2.metric("Toplam Personel", int(toplam_personel))
        m3.metric("Ortalama Hizmet Maliyeti", f"{pulp.value(prob.objective)/sum(talepler.values()):,.0f} TL/Müşteri")

    else:
        st.error("Çözüm bulunamadı. Lütfen kapasiteyi artırın veya kısıtları gevşetin.")

else:
    st.write("👈 Sonuçları görmek için 'Modeli Çöz' butonuna basın.")
