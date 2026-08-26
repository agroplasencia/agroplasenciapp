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

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
            dfs.append(df)
        except Exception as e:
            st.sidebar.error(f"Error al leer {file.name}: {e}")
    
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        st.success(f"Se han cargado {len(uploaded_files)} archivo(s) PAC con éxito.")
        
        tab1, tab2, tab3 = st.tabs(["🗺️ Mapa SIGPAC", "📊 Resumen Recintos", "📋 Datos PAC"])
        
        with tab1:
            st.markdown("### Visor de Parcelas y Recintos")
            m = folium.Map(location=[41.6521, -4.7285], zoom_start=9)
            st_folium(m, width="100%", height=500)
            
        with tab2:
            st.markdown("### Suma de Superficies por Uso SIGPAC")
            if "Uso_SIGPAC" in df_total.columns and "Sup_Declarada_Ha" in df_total.columns:
                resumen = df_total.groupby("Uso_SIGPAC")["Sup_Declarada_Ha"].sum().reset_index()
                st.dataframe(resumen, use_container_width=True)
            else:
                st.dataframe(df_total, use_container_width=True)

        with tab3:
            st.markdown("### Tabla de Datos Unificada")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube al menos un archivo Excel de la PAC desde el menú lateral para empezar.")
