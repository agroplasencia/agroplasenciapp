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
    
    # Buscar la fila donde están los nombres de columna (Polígono, Parcela...)
    for idx, row in df_raw.iterrows():
        row_values = [str(val).upper() for val in row.values if pd.notna(val)]
        if any("POLÍGONO" in v or "POLIGONO" in v or "PARCELA" in v for v in row_values):
            header_idx = idx
            break
            
    if header_idx is not None:
        df = pd.read_excel(file, skiprows=header_idx + 1)
        # Asignar nombres limpios a las columnas
        raw_headers = pd.read_excel(file, skiprows=header_idx, nrows=1).columns
        df.columns = [str(c).strip() for c in raw_headers]
    else:
        df = df_raw

    # Eliminar filas de títulos secundarios o vacías
    df = df.dropna(how='all')
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
            st.markdown("### Ubicación General de Recintos")
            # Centro aproximado en Castrojeriz (Burgos)
            m = folium.Map(location=[42.2881, -4.1378], zoom_start=12)
            
            # Buscar referencias para poner alfileres en la zona
            for idx, row in df_total.iterrows():
                poli = row.get("Polígono", row.get("POLIGONO", "S/N"))
                parc = row.get("Parcela", row.get("PARCELA", "S/N"))
                rec = row.get("Recinto", row.get("RECINTO", "S/N"))
                
                if str(poli) != "S/N" and str(parc) != "S/N":
                    # Marca ilustrativa en el término municipal
                    folium.Marker(
                        location=[42.2881 + (idx * 0.002), -4.1378 + (idx * 0.002)],
                        popup=f"Polígono: {poli} | Parcela: {parc} | Recinto: {rec}",
                        icon=folium.Icon(color="green", icon="leaf")
                    ).add_to(m)
                    
            st_folium(m, width="100%", height=500)
            
        with tab2:
            st.markdown("### Resumen de Parcelas Cargadas")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
