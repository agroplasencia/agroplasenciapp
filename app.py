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
def get_catastro_geojson(provincia, municipio, poligono, parcela):
    """Obtiene el GeoJSON con los lindes oficiales del Catastro/SIGPAC"""
    try:
        # Formatear códigos con ceros a la izquierda
        p = str(int(provincia)).zfill(2) if str(provincia).isdigit() else "09" # 09 Burgos por defecto
        m = str(int(municipio)).zfill(3) if str(municipio).isdigit() else "082" # 082 Castrojeriz por defecto
        pol = str(int(poligono)).zfill(3)
        par = str(int(parcela)).zfill(5)
        
        # Consulta al servicio WFS de Catastro España
        url = (
            f"https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?"
            f"service=wfs&v=2.0.0&request=getfeature&"
            f"STOREDQUERY_ID=GetParcel&srsname=EPSG:4326&"
            f"padd={p}{m}0A{pol}{par}&outputformat=application/json"
        )
        
        r = requests.get(url, timeout=5)
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
            st.sidebar.error(f"Error al procesar {file.name}: {e}")
    
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        st.success(f"Se han cargado {len(uploaded_files)} archivo(s) PAC con éxito.")
        
        tab1, tab2, tab3 = st.tabs(["🗺️ Mapa de Recintos", "📊 Resumen Recintos", "📋 Datos PAC"])
        
        with tab1:
            st.markdown("### Mapa de Parcelas Delimitadas")
            
            # Centro en Castrojeriz (Burgos)
            m = folium.Map(location=[42.2881, -4.1378], zoom_start=13)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite Esri',
                overlay=False
            ).add_to(m)

            cols = {str(c).upper(): c for c in df_total.columns}
            col_poli = next((cols[k] for k in cols if "POLI" in k), None)
            col_parc = next((cols[k] for k in cols if "PARC" in k), None)
            col_muni = next((cols[k] for k in cols if "MUNI" in k), None)
            col_prov = next((cols[k] for k in cols if "PROV" in k), None)

            if col_poli and col_parc:
                colores = ["#00a8ff", "#e1b12c", "#44bd32", "#e84118", "#9c88ff"]
                cargadas = 0
                
                with st.spinner("Descargando contornos de las parcelas..."):
                    for idx, row in df_total.iterrows():
                        poli = row[col_poli]
                        parc = row[col_parc]
                        muni = row[col_muni] if col_muni else 82
                        prov = row[col_prov] if col_prov else 9
                        
                        if pd.notna(poli) and pd.notna(parc):
                            geom = get_catastro_geojson(prov, muni, poli, parc)
                            if geom:
                                color = colores[idx % len(colores)]
                                folium.GeoJson(
                                    geom,
                                    style_function=lambda x, c=color: {
                                        'fillColor': c,
                                        'color': c,
                                        'weight': 3,
                                        'fillOpacity': 0.4
                                    },
                                    tooltip=f"Polígono {poli} | Parcela {parc}"
                                ).add_to(m)
                                cargadas += 1
                
                if cargadas > 0:
                    st.success(f"📍 Se han dibujado {cargadas} contornos de parcelas en el mapa.")
                else:
                    st.warning("⚠️ No se pudieron obtener los contornos. Comprueba la pestaña 'Resumen Recintos' para ver los números de provincia/municipio.")

            st_folium(m, width="100%", height=650)
            
        with tab2:
            st.markdown("### Resumen de Datos")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
