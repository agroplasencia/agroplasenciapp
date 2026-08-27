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
    
    # Buscar la fila donde están las cabeceras reales
    for idx, row in df_raw.iterrows():
        row_values = [str(val).upper() for val in row.values if pd.notna(val)]
        if any("MUNICIPIO" in v or "POLÍGONO" in v or "POLIGONO" in v or "PARCELA" in v for v in row_values):
            header_idx = idx
            break
            
    if header_idx is not None:
        df = pd.read_excel(file, skiprows=header_idx)
    else:
        df = df_raw

    # Limpiar columnas sin nombre y filas vacías
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
            st.markdown("### Ubicación General de Recintos")
            # Centro en Castrojeriz / provincia de Burgos
            m = folium.Map(location=[42.2881, -4.1378], zoom_start=12)
            
            # Detectar columnas de polígono y parcela ignorando mayúsculas/minúsculas
            cols = {str(c).upper(): c for c in df_total.columns}
            col_poli = next((cols[k] for k in cols if "POLI" in k), None)
            col_parc = next((cols[k] for k in cols if "PARC" in k), None)
            col_muni = next((cols[k] for k in cols if "MUNI" in k), None)
            
            if col_poli and col_parc:
                count = 0
                for idx, row in df_total.iterrows():
                    p_val = row[col_poli]
                    pa_val = row[col_parc]
                    m_val = row[col_muni] if col_muni else "Castrojeriz"
                    
                    if pd.notna(p_val) and pd.notna(pa_val):
                        # Puntos aproximados distribuidos por la zona
                        lat = 42.2881 + ((idx % 10) * 0.005)
                        lon = -4.1378 + ((idx // 10) * 0.005)
                        
                        folium.Marker(
                            location=[lat, lon],
                            popup=f"<b>{m_val}</b><br>Polígono: {p_val}<br>Parcela: {pa_val}",
                            icon=folium.Icon(color="green", icon="leaf")
                        ).add_to(m)
                        count += 1
                
                st.caption(f"📍 Mostrando {count} parcelas detectadas en la lista.")
            
            st_folium(m, width="100%", height=500)
            
        with tab2:
            st.markdown("### Resumen de Datos")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
