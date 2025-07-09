import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px
from dash import Dash, html, dcc
import os

# Leer CSV
df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)

# Convertir a hora Colombia (UTC-5)
df["Ends_col"] = df["Ends"].dt.tz_localize("UTC").dt.tz_convert("America/Bogota")
df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

# Filtrar solo el último día en Colombia
ultimo_dia = df["Ends_col"].dt.date.max()
df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

# --- Quitamos el filtro entre 06:00 y 19:00 para mostrar todo el día ---
# df_ultimo_dia = df_ultimo_dia[
#     (df_ultimo_dia["Ends_col"].dt.hour >= 6) & (df_ultimo_dia["Ends_col"].dt.hour <= 19)
# ]

# Preparar columnas
df_ultimo_dia = df_ultimo_dia[["hora", "Power MW"]]
df_ultimo_dia.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

# Gráfico con estilo
fig = px.line(
    df_ultimo_dia,
    x="hora",
    y="energia_MWh",
    title="Generación Sunnorte",
    markers=True,
)

fig.update_traces(line=dict(color="#84B113", width=3))
fig.update_layout(
    title_x=0.5,
    title_font_color="#000000",
    plot_bgcolor="#F2F2F2",
    paper_bgcolor="#FFFFFF",
    font=dict(color="#000000", family="Arial"),
    margin=dict(l=40, r=40, t=50, b=40),
    xaxis_title="Hora",
    yaxis_title="Energía (MWh)",
    # --- Quitamos el rango fijo para que muestre todas las horas ---
    # xaxis=dict(range=["06:00", "19:00"])
)

# KPI
energia_total = df_ultimo_dia["energia_MWh"].sum()

# App Dash
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        # Logo más pequeño arriba a la izquierda
        html.Div([
            html.Img(
                src="/assets/logo.png",
                style={"height": "40px", "marginRight": "15px"}  # tamaño reducido (antes 60px)
            ),
            html.H1("Dashboard Planta Solar", style={"margin": "0", "color": "#84B113"})
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "30px", "justifyContent": "flex-start"}),

        dcc.Graph(figure=fig),

        html.Div([
            html.H4("Energía Total Generada Hoy", style={"color": "#000000"}),
            html.P(f"{energia_total:.1f} kWh", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),

        html.Div([
            html.P(f"Última actualización: {datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')} hora Colombia")
        ], style={"textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"}),

        # Agregar refresco automático cada 5 minutos (300000 ms)
        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # 5 minutos en milisegundos
            n_intervals=0
        )
    ]
)

# Callback para refrescar la página (solo actualiza el layout para recargar gráficos)
from dash.dependencies import Input, Output

@app.callback(
    Output(component_id='interval-component', component_property='n_intervals'),
    [Input(component_id='interval-component', component_property='n_intervals')]
)
def refresh_data(n):
    # Aquí podrías recargar datos si quieres que el gráfico se actualice dinámicamente.
    # En tu caso, solo permitimos que el componente 'interval-component' se actualice.
    return n

if __name__ == "__main__":
    app.run_server(debug=True)
