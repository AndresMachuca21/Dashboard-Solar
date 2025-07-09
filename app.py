import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

def cargar_datos():
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)

    # ❗ Si el archivo ya viene en hora Colombia, NO debemos hacer tz_localize("UTC")
    # Usamos simplemente tz_localize(None) para asegurarnos de que no tenga zona horaria
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    # Último día
    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

    df_por_hora = df_ultimo_dia[["hora", "Power MW"]]
    df_por_hora.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

    # Crear rango de horas de 00:00 a 23:00
    horas_completas = pd.date_range("00:00", "23:00", freq="h").strftime("%H:%M")
    df_completo = pd.DataFrame({"hora": horas_completas})
    df_final = df_completo.merge(df_por_hora, on="hora", how="left")

    return df_final

df_ultimo = cargar_datos()
energia_total = df_ultimo["energia_MWh"].sum(skipna=True)

def crear_figura(df):
    fig = px.line(
        df,
        x="hora",
        y="energia_MWh",
        title=None,  # ❌ Quitar título de la gráfica
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
        xaxis=dict(categoryorder='array', categoryarray=df["hora"].tolist()),
    )
    return fig

app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        html.H1("Generación Sunnorte", style={
            "textAlign": "center",
            "color": "#000000",
            "marginBottom": "40px"
        }),

        html.Div([
            html.Div(style={"flex": "1"}),  # Espacio vacío a la izquierda
            html.Img(
                src="/assets/logo.png",
                style={"height": "40px"}
            ),
        ], style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "20px"}),

        dcc.Graph(id="grafico-generacion", figure=crear_figura(df_ultimo)),

        html.Div([
            html.H4("Energía Total Generada Hoy", style={"color": "#000000"}),
            html.P(f"{energia_total:.1f} kWh", id="kpi-generacion", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),

        html.Div(id="ultima-actualizacion", children=[
            html.P(f"Última actualización: {datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')} hora Colombia")
        ], style={"textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"}),

        dcc.Interval(
            id='interval-component',
            interval=5 * 60 * 1000,
            n_intervals=0
        )
    ]
)

@app.callback(
    [
        Output("grafico-generacion", "figure"),
        Output("kpi-generacion", "children"),
        Output("ultima-actualizacion", "children")
    ],
    [Input("interval-component", "n_intervals")]
)
def actualizar_datos(n):
    df_actual = cargar_datos()
    fig = crear_figura(df_actual)
    total = df_actual["energia_MWh"].sum(skipna=True)
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    return fig, f"{total:.1f} kWh", f"Última actualización: {ahora} hora Colombia"

if __name__ == "__main__":
    app.run_server(debug=True)
