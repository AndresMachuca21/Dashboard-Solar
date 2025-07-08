import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import os
from zoneinfo import ZoneInfo


st.set_page_config(page_title="Dashboard Planta Solar", layout="wide")
# st.title("☀️ Producción Sunnorte")


#st.image("https://www.issuersolutions.com/wp-content/uploads/2022/02/ECOENER-2.png", width=300)
st.title("Producción Sunnorte")

# col1, col2 = st.columns([1, 0.15])
# with col1:
#     st.title("Producción Sunnorte")
# with col2:
#     st.image("https://www.issuersolutions.com/wp-content/uploads/2022/02/ECOENER-2.png", width=300)


archivo_csv = "generacion_actual.csv"

# Verifica que el archivo exista
if not os.path.exists(archivo_csv):
    st.error("No se encuentra el archivo más reciente.")
    st.stop()

try:
    # Leer el archivo
    df = pd.read_csv(archivo_csv, sep=";", skiprows=1)

    if "Ends dd/mm/YYYY HH:MM" not in df.columns or "Power MW" not in df.columns:
        st.error("Las columnas necesarias no se encuentran en el archivo.")
        st.stop()

    # Convertir hora
    df["end_datetime"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], errors="coerce")
    fecha_max = df["end_datetime"].dt.date.max()
    df_hoy = df[df["end_datetime"].dt.date == fecha_max].copy()
    df_hoy["hora"] = df_hoy["end_datetime"].dt.strftime("%H:%M")
    df_hoy = df_hoy[["hora", "Power MW"]].rename(columns={"Power MW": "potencia_MW"})

    # Crear rango de horas fijas
    horas_completas = pd.DataFrame({
        "hora": [(datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=i)).strftime("%H:%M") for i in range(24)]
    })
    df_merge = pd.merge(horas_completas, df_hoy, on="hora", how="left")

    # Altair para gráfico interactivo con punto resaltado
    base = alt.Chart(df_merge).encode(
        x=alt.X("hora", title="Hora"),
        y=alt.Y("potencia_MW", title="Potencia (MW)")
    )

    linea = base.mark_line(color="#1f77b4")
    ultimo_index = df_merge["potencia_MW"].last_valid_index()
    ultimo_punto = df_merge.iloc[[ultimo_index]]

    punto_resaltado = alt.Chart(ultimo_punto).encode(
        x="hora",
        y="potencia_MW"
    ).mark_point(color="blue", size=150, shape="circle", filled=True).encode(
        tooltip=["hora", "potencia_MW"]
    )

    st.subheader(f"Hoy: {fecha_max.strftime('%m/%d/%Y')}")
    st.altair_chart(linea + punto_resaltado, use_container_width=True)

    if df_merge["potencia_MW"].notna().any():
        potencia_total = df_merge["potencia_MW"].sum(skipna=True)
        max_row = df_merge[df_merge["potencia_MW"] == df_merge["potencia_MW"].max()]
        max_hora = max_row["hora"].values[0]
        max_valor = max_row["potencia_MW"].values[0]
        st.metric("Potencia Acumulada", f"{potencia_total:.1f} MW")



except Exception as e:
    st.error(f"Error al procesar el archivo: {e}")


st.markdown("""
    <meta http-equiv="refresh" content="300">
""", unsafe_allow_html=True)



st.caption(f"Última actualización (UTC-5): {datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')}")
