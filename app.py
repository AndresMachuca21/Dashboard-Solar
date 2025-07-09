import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

# Función para cargar y procesar datos
def cargar_datos():
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)

    # Convertir a hora Colombia (UTC-5)
    df["Ends_col"] = df["Ends"].dt.tz_localize("UTC").dt.tz_convert("America/Bogota")
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    # Filtrar solo el último día en Colombia
    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

    # Agrupar por hora exacta (redondeada hacia abajo a la hora completa)
    df_ultimo_dia["hora_redondeada"] = df_ultimo_dia["Ends_col"].dt.floor("H").dt.strftime("%H:%M")
    df_por_hora = df_ultimo_dia.groupby("hora_redondeada")["Power MW"].mean().reset_index()
    df_por_hora.rename(columns={"hora_redondeada": "hora", "Power MW": "energia_MWh"}, inplace=True)

    # Crear rango completo de 00:00 a 23:00
    horas_completas = pd.date_range("00:00", "23:00", freq="H").strftime("%H:%M")
    df_completo = pd.DataFrame({"hora": horas_completas})
    df_final = df_completo.merge(df_por_hora, on="hora", how="left")

    return df_final

# Inicializar datos
df_ultimo = cargar_datos()
energia_total = df_ultimo["energia_MWh"].sum(skipna=True)

# Crear figura inicial
def crear_figura(df):
    fig = px.line(
        df,
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
        paper_bgcolor="#F2F2F2",
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
        html.Div([
            html.Img(
                src="/assets/logo.png",
                style={"height": "40px", "marginLeft": "15px"}
            ),
            html.H1("Dashboard Planta Solar", style={"margin": "0", "color": "#000000"})
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "30px", "justifyContent": "flex-start"}),

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
            interval=5 * 60 * 1000,  # 5 minutos en milisegundos
            n_intervals=0
        )
    ]
)

# Callback que actualiza gráfica, KPI y fecha
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
    kpi = f"{total:.1f} kWh"
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    return fig, kpi, f"Última actualización: {ahora} hora Colombia"

if __name__ == "__main__":
    app.run_server(debug=True)
