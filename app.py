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
st.subheader("Visor de Parcelas (Burgos y Palencia)")

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
    """Obtiene los lindes geométricos reales desde Catastro soportando Burgos (09) y Palencia (34)"""
    try:
        # Extraer solo números por si viene con texto
        p_num = ''.join(filter(str.isdigit, str(provincia)))
        m_num = ''.join(filter(str.isdigit, str(municipio)))
        pol_num = ''.join(filter(str.isdigit, str(poligono)))
        par_num = ''.join(filter(str.isdigit, str(parcela)))
        
        p = p_num.zfill(2) if p_num else "09"
        m = m_num.zfill(3) if m_num else "082"
        pol = pol_num.zfill(3)
        par = par_num.zfill(5)
        
        # Petición a Catastro INSPIRE WFS
        url = (
            f"https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?"
            f"service=wfs&v=2.0.0&request=getfeature&"
            f"STOREDQUERY_ID=GetParcel&srsname=EPSG:4326&"
            f"padd={p}{m}0A{pol}{par}&outputformat=application/json"
        )
        
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
        st.success(f"Se han cargado {len(uploaded_files)} archivo(s) correctamente.")
        
        tab1, tab2 = st.tabs(["🗺️ Mapa de Fincas", "📋 Listado y Resumen"])
        
        with tab1:
            st.markdown("### Tus Parcelas sobre Satélite")
            
            # Centro en el límite entre Burgos y Palencia (zona Castrojeriz - Astudillo)
            m = folium.Map(location=[42.23, -4.20], zoom_start=12)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri World Imagery',
                name='Foto Satélite',
                overlay=False
            ).add_to(m)

            # Mapeo de columnas
            cols = {str(c).upper(): c for c in df_total.columns}
            col_poli = next((cols[k] for k in cols if "POLI" in k), None)
            col_parc = next((cols[k] for k in cols if "PARC" in k), None)
            col_muni = next((cols[k] for k in cols if "MUNI" in k), None)
            col_prov = next((cols[k] for k in cols if "PROV" in k), None)

            if col_poli and col_parc:
                colores = ["#00a8ff", "#e1b12c", "#44bd32", "#e84118", "#9c88ff", "#f5cd79"]
                cargadas = 0
                
                with st.spinner("Cargando parcelas de Burgos y Palencia desde Catastro..."):
                    for idx, row in df_total.iterrows():
                        poli = row[col_poli]
                        parc = row[col_parc]
                        muni = row[col_muni] if col_muni else 82
                        prov = row[col_prov] if col_prov else 9
                        
                        if pd.notna(poli) and pd.notna(parc):
                            geom = get_catastro_polygon(prov, muni, poli, parc)
                            if geom:
                                color = colores[idx % len(colores)]
                                folium.GeoJson(
                                    geom,
                                    style_function=lambda x, c=color: {
                                        'fillColor': c,
                                        'color': '#ffffff',
                                        'weight': 2.5,
                                        'fillOpacity': 0.5
                                    },
                                    tooltip=f"<b>Prov: {prov} | Muni: {muni}</b><br>Polígono {poli} | Parcela {parc}"
                                ).add_to(m)
                                cargadas += 1
                
                if cargadas > 0:
                    st.success(f"📍 ¡Conseguido! Se han dibujado {cargadas} parcelas de Burgos/Palencia.")
                else:
                    st.warning("⚠️ No se han podido obtener los contornos automáticamente. Revisa la pestaña 'Listado' para verificar los códigos de provincia/municipio del Excel.")

            st_folium(m, width="100%", height=650)
            
        with tab2:
            st.markdown("### Datos Unificados")
            st.dataframe(df_total, use_container_width=True)
else:
    st.info("👈 Sube tu archivo Excel de la PAC en el menú de la izquierda para ver el mapa.")
