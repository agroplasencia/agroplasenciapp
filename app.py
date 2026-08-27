import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import requests
import json

st.set_page_config(
    page_title="Control Agrícola PAC",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Control de Explotación Agrícola y PAC")
st.subheader("Castilla y León")

st.sidebar.header("📁 Cargar Declaraciones PAC")
uploaded_files = st.sidebar.file_uploader(
    "Sube tus archivos Excel (.xlsx) de la Junta de CyL", 
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

@st.cache_data(ttl=3600)
def get_parcela_geometry(provincia, municipio, poligono, parcela):
    """Consulta la geometría GeoJSON del Catastro / WFS público"""
    try:
        # Formatear números
        prov = str(provincia).zfill(2)
        muni = str(municipio).zfill(3)
        poli = str(poligono).zfill(3)
        parc = str(parcela).zfill(5)
        
        # API WFS de Catastro para obtener los limites de la parcela
        url = (
            f"https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?"
            f"service=wfs&v=2.0.0&request=getfeature&"
            f"STOREDQUERY_ID=GetParcel&srsname=EPSG:4326&"
            f"padd=34{muni}{poli}{parc}&outputformat=application/json"
        )
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
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
            st.sidebar.error(f"Error al procesar {file.name}: {e}")
    
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        st.success(f"Se han cargado {len(uploaded_files)} archivo(s) PAC con éxito.")
        
        tab1, tab2, tab3 = st.tabs(["🗺️ Mapa de Recintos", "📊 Resumen Recintos", "📋 Datos PAC"])
        
        with tab1:
            st.markdown("### Mapa de Parcelas Delimitadas")
            
            # Crear mapa satélite ESRI por defecto
            m = folium.Map(location=[42.19, -4.29], zoom_start=13)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite Esri',
                overlay=False
            ).add_to(m)

            # Detectar columnas
            cols = {str(c).upper(): c for c in df_total.columns}
            col_poli = next((cols[k] for k in cols if "POLI" in k), None)
            col_parc = next((cols[k] for k in cols if "PARC" in k), None)
            col_muni = next((cols[k] for k in cols if "MUNI" in k), None)

            if col_poli and col_parc:
                features = []
                colores = ["#0088ff", "#ff8800", "#00ff88", "#ff0088", "#9900ff"]
                
                with st.spinner("Cargando contornos de las parcelas desde el Catastro..."):
                    for idx, row in df_total.iterrows():
                        poli = row[col_poli]
                        parc = row[col_parc]
                        muni = row[col_muni] if col_muni else "001"
                        
                        if pd.notna(poli) and pd.notna(parc):
                            geom = get_parcela_geometry(34, muni, poli, parc) # 34 = Palencia (o ajustar según provincia)
                            if geom:
                                color = colores[idx % len(colores)]
                                folium.GeoJson(
                                    geom,
                                    style_function=lambda x, c=color: {
                                        'fillColor': c,
                                        'color': c,
                                        'weight': 2,
                                        'fillOpacity': 0.4
                                    },
                                    tooltip=f"Polígono {poli} - Parcela {parc}"
                                ).add_to(m)
                                
            st_folium(m, width="100%", height=650)
            
        with tab2:
            st.markdown("### Resumen de Datos")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
