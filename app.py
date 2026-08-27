import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(
    page_title="Control Agrícola PAC",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Mi Control Agrícola Personal")
st.subheader("Visor de Parcelas y Recintos PAC")

st.sidebar.header("📁 Cargar Declaración PAC")
uploaded_files = st.sidebar.file_uploader(
    "Sube tu archivo Excel (.xlsx) de la PAC", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

def clean_pac_dataframe(file):
    df_raw = pd.read_excel(file)
    header_idx = None
    
    for idx, row in df_raw.iterrows():
        row_values = [str(val).upper() for val in row.values if pd.notna(val)]
        if any("MUNICIPIO" in v or "POLÍGONO" in v or "POLIGONO" in v or "PARCELA" in v for v in row_values):
            header_idx = idx
            break
            
    if header_idx is not None:
        df = pd.read_excel(file, skiprows=header_idx)
    else:
        df = df_raw

    df = df.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(ttl=86400)
def get_catastro_polygon(provincia, municipio, poligono, parcela):
    """Obtiene los lindes geométricos reales desde la API del Catastro/SIGPAC"""
    try:
        p = str(int(provincia)).zfill(2) if str(provincia).isdigit() else "09"
        m = str(int(municipio)).zfill(3) if str(municipio).isdigit() else "082"
        pol = str(int(poligono)).zfill(3)
        par = str(int(parcela)).zfill(5)
        
        # Referencia catastral de rústica de 20 caracteres: Prov(2) + Muni(3) + Clase(A) + Poli(3) + Parc(5) + 0000 + Control(2)
        # Probamos consulta directa por atributos WFS
        url = f"https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=wfs&v=2.0.0&request=getfeature&STOREDQUERY_ID=GetParcel&srsname=EPSG:4326&padd={p}{m}0A{pol}{par}&outputformat=application/json"
        
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            if "features" in data and len(data["features"]) > 0:
                return data["features"][0]
    except Exception:
        pass
    return None

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        try:
            df = clean_pac_dataframe(file)
            dfs.append(df)
        except Exception as e:
            st.sidebar.error(f"Error al leer {file.name}: {e}")
    
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        st.success(f" Se han cargado {len(uploaded_files)} archivo(s) correctamente.")
        
        tab1, tab2 = st.tabs(["🗺️ Mapa de Fincas", "📋 Listado y Resumen"])
        
        with tab1:
            st.markdown("### Tus Parcelas sobre Satélite")
            
            # Centro por defecto en Castrojeriz
            m = folium.Map(location=[42.2881, -4.1378], zoom_start=13)
            
            # Capa Ortofoto Satélite HD
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri World Imagery',
                name='Foto Satélite',
                overlay=False
            ).add_to(m)

            cols = {str(c).upper(): c for c in df_total.columns}
            col_poli = next((cols[k] for k in cols if "POLI" in k), None)
            col_parc = next((cols[k] for k in cols if "PARC" in k), None)
            col_muni = next((cols[k] for k in cols if "MUNI" in k), None)
            col_prov = next((cols[k] for k in cols if "PROV" in k), None)
            col_uso = next((cols[k] for k in cols if "USO" in k), None)

            if col_poli and col_parc:
                colores_uso = {
                    "TA": "#e1b12c", # Tierra Arable (Amarillo)
                    "FO": "#44bd32", # Forestal (Verde)
                    "PA": "#00a8ff", # Pastos (Azul)
                    "PR": "#9c88ff", # Pastizal (Morado)
                    "DEFAULT": "#e84118" # Naranja
                }
                
                cargadas = 0
                with st.spinner("Buscando y dibujando lindes de tus fincas..."):
                    for idx, row in df_total.iterrows():
                        poli = row[col_poli]
                        parc = row[col_parc]
                        muni = row[col_muni] if col_muni else 82
                        prov = row[col_prov] if col_prov else 9
                        uso = str(row[col_uso]).strip().upper() if col_uso and pd.notna(row[col_uso]) else "DEFAULT"
                        
                        if pd.notna(poli) and pd.notna(parc):
                            geom = get_catastro_polygon(prov, muni, poli, parc)
                            if geom:
                                color = colores_uso.get(uso, colores_uso["DEFAULT"])
                                folium.GeoJson(
                                    geom,
                                    style_function=lambda x, c=color: {
                                        'fillColor': c,
                                        'color': '#ffffff', # Borde blanco
                                        'weight': 2.5,
                                        'fillOpacity': 0.45
                                    },
                                    tooltip=f"<b>Polígono {poli} | Parcela {parc}</b><br>Uso: {uso}"
                                ).add_to(m)
                                cargadas += 1
                
                if cargadas > 0:
                    st.success(f"📍 ¡Conseguido! Se han pintado {cargadas} parcelas en el mapa.")
                else:
                    st.info("📌 Si no se cargan automáticamente por red, utiliza la pestaña de datos para revisar los números de finca.")

            st_folium(m, width="100%", height=650)
            
        with tab2:
            st.markdown("### Datos Unificados")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube tu archivo Excel de la PAC en el menú de la izquierda para ver el mapa.")
