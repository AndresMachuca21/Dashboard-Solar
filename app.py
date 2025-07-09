import pandas as pd
from datetime import datetime
import plotly.express as px
from dash import Dash, html, dcc
import os

# Cargar CSV
df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
df["hora"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True).dt.strftime("%H:%M")
df = df[["hora", "Power MW"]].copy()
df.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

# Filtrar solo datos del último día
ultima_fecha = pd.to_datetime(df["hora"], format="%H:%M").max().date()
df_filtrado = df.copy()

# Gráfico
fig = px.line(df_filtrado, x="hora", y="energia_MWh", title="Producción por hora")

# KPIs
energia_total = df_filtrado["energia_MWh"].sum()
max_row = df_filtrado.loc[df_filtrado["energia_MWh"].idxmax()]
max_hora = max_row["hora"]
max_valor = max_row["energia_MWh"]

# App
app = Dash(__name__)
server = app.server  # para Render

app.layout = html.Div(children=[
    html.Img(src='https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Solar_panel_icon.svg/1200px-Solar_panel_icon.svg.png',
             style={"height": "60px", "margin": "10px"}),

    html.H1("Dashboard Planta Solar", style={"textAlign": "center"}),

    dcc.Graph(figure=fig),

    html.Div([
        html.Div([
            html.H4("Energía Total Generada"),
            html.P(f"{energia_total:.1f} kWh")
        ], style={"width": "30%", "display": "inline-block"}),
    ], style={"textAlign": "center"}),

    html.Div([
        html.P(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    ], style={"textAlign": "center", "marginTop": "20px"})
])

if __name__ == "__main__":
    app.run_server(debug=True)
