
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

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
        
        tab1, tab2, tab3 = st.tabs(["🗺️ Visor SIGPAC", "📊 Resumen Recintos", "📋 Datos PAC"])
        
        with tab1:
            st.markdown("### Visor Oficial SIGPAC (Junta de CyL / MAPA)")
            st.info("💡 Usa este visor oficial interactivo para buscar polígonos y parcelas directamente con los lindes oficiales.")
            
            # Cargar visor interactivo de mapas de forma estable
            components.iframe("https://sga.jcyl.es/visor/", height=600, scrolling=True)
            
        with tab2:
            st.markdown("### Resumen de Datos")
            st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla Completa de Datos")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
