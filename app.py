import pandas as pd
from datetime import datetime
import plotly.express as px
from dash import Dash, html, dcc
import os

# Leer CSV
df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)

# Filtrar solo el último día
ultimo_dia = df["Ends"].dt.date.max()
df_ultimo_dia = df[df["Ends"].dt.date == ultimo_dia].copy()

# Procesar columnas
df_ultimo_dia["hora"] = df_ultimo_dia["Ends"].dt.strftime("%H:%M")
df_ultimo_dia = df_ultimo_dia[["hora", "Power MW"]]
df_ultimo_dia.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

# Gráfico con estilo
fig = px.line(
    df_ultimo_dia,
    x="hora",
    y="energia_MWh",
    title="Generación por hora",
    markers=True,
)
fig.update_traces(line=dict(color="#84B113", width=3))
fig.update_layout(
    title_x=0.5,
    plot_bgcolor="#F2F2F2",
    paper_bgcolor="#FFFFFF",
    font=dict(color="#000000", family="Arial"),
    margin=dict(l=40, r=40, t=50, b=40),
    xaxis_title="Hora",
    yaxis_title="Energía (MWh)",
)

# KPI
energia_total = df_ultimo_dia["energia_MWh"].sum()

# App Dash
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        html.Div([
            html.Img(
                src="/assets/logo.png",  # 🔁 asegúrate de subir el logo en la carpeta 'assets'
                style={"height": "60px", "marginRight": "15px"}
            ),
            html.H1("Dashboard Planta Solar", style={"margin": "0", "color": "#84B113"})
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "30px"}),

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
            html.P(f"Última actualización: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC-5")
        ], style={"textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"})
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)
