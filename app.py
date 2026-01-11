{\rtf1\ansi\ansicpg1254\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pulp\
import pandas as pd\
import numpy as np\
\
# --- SAYFA AYARLARI ---\
st.set_page_config(page_title="Sat\uc0\u305 \u351  G\'fcc\'fc Optimizasyonu", layout="wide")\
\
st.title("\uc0\u55357 \u56525  Sat\u305 \u351  G\'fcc\'fc ve Ofis Yeri Atama Modeli")\
st.markdown("""\
Bu uygulama, **Anadolu Teknoloji \'c7\'f6z\'fcmleri A.\uc0\u350 .** i\'e7in en az maliyetli ofis ve personel da\u287 \u305 l\u305 m\u305 n\u305  hesaplar.\
Sol taraftaki men\'fcden maliyetleri ve talepleri de\uc0\u287 i\u351 tirip **"Modeli \'c7\'f6z"** butonuna basarak sonucu g\'f6rebilirsiniz.\
""")\
\
# --- 1. VER\uc0\u304  G\u304 R\u304 \u350 \u304  (SOL PANEL) ---\
st.sidebar.header("\uc0\u9881 \u65039  Parametre Ayarlar\u305 ")\
\
# Maliyetler\
with st.sidebar.expander("\uc0\u55357 \u56496  Maliyet ve Kapasite", expanded=True):\
    maas = st.number_input("Personel Maa\uc0\u351 \u305  (TL)", value=35000, step=1000)\
    kapasite = st.number_input("Personel Kapasitesi (Saat/Ay)", value=160, step=10)\
    big_m = 100  # B\'fcy\'fck say\uc0\u305 \
\
# \uc0\u304 l\'e7eler Listesi\
ilceler = [\
    "Kad\uc0\u305 \u351 ehri", "Sorgun", "\'c7ay\u305 ralan", "Bo\u287 azl\u305 yan", "\u350 efaatli", \
    "\'c7i\'e7ekda\uc0\u287 \u305 ", "Kaman", "Mucur", "Sar\u305 yah\u351 i", "Ortak\'f6y", \
    "G\'fczelyurt", "Eskil"\
]\
\
# Talep ve Ofis Maliyeti Giri\uc0\u351 i\
st.sidebar.subheader("\uc0\u55356 \u57305 \u65039  \u304 l\'e7e Verileri")\
df_input = pd.DataFrame(\{\
    '\uc0\u304 l\'e7e': ilceler,\
    'Talep (M\'fc\uc0\u351 teri)': [45, 120, 40, 90, 50, 45, 80, 60, 30, 95, 35, 70],\
    'Ofis Maliyeti (TL)': [18000, 30000, 17000, 25000, 19000, 18000, 22000, 20000, 15000, 26000, 16000, 21000]\
\})\
edited_df = st.sidebar.data_editor(df_input, num_rows="fixed")\
\
# Mesafe Matrisi (Otomatik Sim\'fclasyon)\
# Ger\'e7ek hayatta bu veriyi Excel'den okutabiliriz, burada sim\'fcle ediyoruz.\
@st.cache_data\
def get_distance_matrix():\
    # Rastgele ama tutarl\uc0\u305  s\'fcreler (Kendi il\'e7esi 2 saat, di\u287 erleri 3-9 saat aras\u305 )\
    np.random.seed(42)\
    matrix = pd.DataFrame(\
        np.random.randint(3, 10, size=(12, 12)), \
        columns=ilceler, index=ilceler\
    )\
    np.fill_diagonal(matrix.values, 2) # Kendi kendine hizmet s\'fcresi\
    return matrix\
\
mesafe_matrisi = get_distance_matrix()\
\
# --- 2. OPT\uc0\u304 M\u304 ZASYON MODEL\u304  ---\
\
col1, col2 = st.columns([1, 2])\
\
with col1:\
    st.info("\uc0\u55357 \u56391  Verileri ayarlad\u305 ktan sonra butona bas\u305 n.")\
    solve_btn = st.button("\uc0\u55357 \u56960  Modeli \'c7\'f6z ve Optimize Et", type="primary")\
\
if solve_btn:\
    with st.spinner('Solver en uygun ofis yerlerini hesapl\uc0\u305 yor...'):\
        # Modeli Kur\
        prob = pulp.LpProblem("Satis_Gucu_Modeli", pulp.LpMinimize)\
\
        # De\uc0\u287 i\u351 kenler\
        # y[i]: Ofis a\'e7\uc0\u305 ls\u305 n m\u305 ? (0/1)\
        y = pulp.LpVariable.dicts("Ofis_Acma", ilceler, cat='Binary')\
        # p[i]: Personel say\uc0\u305 s\u305  (Tamsay\u305 )\
        p = pulp.LpVariable.dicts("Personel_Sayisi", ilceler, lowBound=0, cat='Integer')\
        # x[i][j]: i ofisinden j il\'e7esine ka\'e7 m\'fc\uc0\u351 teriye bak\u305 l\u305 yor?\
        x = pulp.LpVariable.dicts("Atama", (ilceler, ilceler), lowBound=0, cat='Integer')\
\
        # Parametreleri Al\
        talepler = dict(zip(edited_df['\uc0\u304 l\'e7e'], edited_df['Talep (M\'fc\u351 teri)']))\
        ofis_maliyetleri = dict(zip(edited_df['\uc0\u304 l\'e7e'], edited_df['Ofis Maliyeti (TL)']))\
\
        # AMA\'c7 FONKS\uc0\u304 YONU: Min (Ofis Maliyeti + Personel Maa\u351 \u305 )\
        prob += pulp.lpSum([ofis_maliyetleri[i] * y[i] + maas * p[i] for i in ilceler])\
\
        # KISITLAR\
        \
        # 1. Talep Kar\uc0\u351 \u305 lama: Her il\'e7enin talebi tamamen kar\u351 \u305 lanmal\u305 \
        for j in ilceler:\
            prob += pulp.lpSum([x[i][j] for i in ilceler]) == talepler[j]\
\
        # 2. Kapasite K\uc0\u305 s\u305 t\u305 : Bir ofisteki personel, atand\u305 \u287 \u305  i\u351 lere yeti\u351 ebilmeli\
        for i in ilceler:\
            harcanan_sure = pulp.lpSum([x[i][j] * mesafe_matrisi.loc[i, j] for j in ilceler])\
            prob += harcanan_sure <= p[i] * kapasite\
\
        # 3. Ba\uc0\u287 lant\u305  K\u305 s\u305 t\u305 : Ofis yoksa personel olamaz (veya personel varsa ofis a\'e7\u305 lmal\u305 )\
        for i in ilceler:\
            prob += p[i] <= big_m * y[i]\
\
        # \'c7\'f6z\
        prob.solve()\
        durum = pulp.LpStatus[prob.status]\
\
    # --- 3. SONU\'c7 EKRANI ---\
    if durum == "Optimal":\
        st.success(f"\uc0\u9989  \'c7\'f6z\'fcm Bulundu! Toplam Maliyet: **\{pulp.value(prob.objective):,.2f\} TL**")\
        \
        # Sonu\'e7lar\uc0\u305  Tablola\u351 t\u305 r\
        sonuc_listesi = []\
        for i in ilceler:\
            acik_mi = y[i].varValue\
            per_say = p[i].varValue\
            if acik_mi == 1:\
                # Bu ofis nerelere hizmet veriyor?\
                hizmet_verilenler = []\
                for j in ilceler:\
                    if x[i][j].varValue > 0:\
                        hizmet_verilenler.append(f"\{j\} (\{int(x[i][j].varValue)\})")\
                \
                sonuc_listesi.append(\{\
                    "\uc0\u304 l\'e7e Ofisi": i,\
                    "Durum": "A\'c7IK \uc0\u55357 \u57314 ",\
                    "Personel": int(per_say),\
                    "Hizmet Verilen Yerler": ", ".join(hizmet_verilenler)\
                \})\
            else:\
                sonuc_listesi.append(\{\
                    "\uc0\u304 l\'e7e Ofisi": i,\
                    "Durum": "KAPALI \uc0\u55357 \u56628 ",\
                    "Personel": "-",\
                    "Hizmet Verilen Yerler": "-"\
                \})\
        \
        st.dataframe(pd.DataFrame(sonuc_listesi))\
        \
        # Grafiksel G\'f6sterim (Basit Metrikler)\
        m1, m2, m3 = st.columns(3)\
        toplam_ofis = sum([y[i].varValue for i in ilceler])\
        toplam_personel = sum([p[i].varValue for i in ilceler])\
        \
        m1.metric("A\'e7\uc0\u305 lacak Ofis Say\u305 s\u305 ", int(toplam_ofis))\
        m2.metric("Toplam Personel", int(toplam_personel))\
        m3.metric("Ortalama Hizmet Maliyeti", f"\{pulp.value(prob.objective)/sum(talepler.values()):,.0f\} TL/M\'fc\uc0\u351 teri")\
\
    else:\
        st.error("\'c7\'f6z\'fcm bulunamad\uc0\u305 . L\'fctfen kapasiteyi art\u305 r\u305 n veya k\u305 s\u305 tlar\u305  gev\u351 etin.")\
\
else:\
    st.write("\uc0\u55357 \u56392  Sonu\'e7lar\u305  g\'f6rmek i\'e7in 'Modeli \'c7\'f6z' butonuna bas\u305 n.")}