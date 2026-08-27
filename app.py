import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

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
        
        tab1, tab2, tab3 = st.tabs(["🗺️ Mapa SIGPAC", "📊 Resumen Recintos", "📋 Datos PAC"])
        
        with tab1:
            st.markdown("### Mapa con Parcelas y Capa SIGPAC")
            
            # Crear mapa centrado en la zona de Castrojeriz (Burgos)
            m = folium.Map(location=[42.2881, -4.1378], zoom_start=14)
            
            # Capa 1: Ortofoto Satélite de España (PNOA)
            folium.TileLayer(
                tiles='https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&REQUEST=GetMap&LAYERS=OI.OrthoimageCoverage&STYLES=&FORMAT=image/png&TRANSPARENT=TRUE&VERSION=1.3.0&WIDTH=256&HEIGHT=256&CRS=EPSG:3857&BBOX={bbox}',
                attr='IGN - PNOA',
                name='Foto Satélite (PNOA)',
                overlay=False
            ).add_to(m)

            # Capa 2: Capa oficial del SIGPAC (Líneas y Recintos del Ministerio)
            folium.WmsTileLayer(
                url='https://wms.mapama.gob.es/wms/wms.aspx',
                layers='PARCELA,RECINTO',
                fmt='image/png',
                transparent=True,
                name='Líneas del SIGPAC',
                overlay=True,
                control=True
            ).add_to(m)

            folium.LayerControl().add_to(m)
            
            st.info("💡 La capa de parcelas del SIGPAC se dibuja automáticamente en el mapa. Haz zoom en la zona de tus fincas para ver los lindes amarillos/rojos.")
            st_folium(m, width="100%", height=600)
            
        with tab2:
            st.markdown("### Resumen de Datos")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
