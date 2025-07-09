import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State

# Función para cargar datos
def cargar_datos():
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()
    df_por_hora = df_ultimo_dia[["hora", "Power MW"]]
    df_por_hora.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

    horas_completas = pd.date_range("00:00", "23:00", freq="h").strftime("%H:%M")
    df_completo = pd.DataFrame({"hora": horas_completas})
    df_final = df_completo.merge(df_por_hora, on="hora", how="left")

    return df_final

# Función para crear figura con pulso en último punto
def crear_figura(df, pulso_on):
    hora_final = df["hora"][df["energia_MWh"].last_valid_index()]
    valor_final = df["energia_MWh"].dropna().iloc[-1]

    fig = go.Figure()

    # Línea base
    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6, color="#84B113"),
        showlegend=False
    ))

    # Punto último con pulso alternando tamaño y opacidad
    size = 12 if pulso_on else 8
    opacity = 1 if pulso_on else 0.4

    fig.add_trace(go.Scatter(
        x=[hora_final],
        y=[valor_final],
        mode="markers",
        marker=dict(
            size=size,
            color="#84B113",
            opacity=opacity,
            symbol="circle"
        ),
        showlegend=False
    ))

    fig.update_layout(
        xaxis_title="Hora",
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            categoryorder='array',
            categoryarray=df["hora"].tolist(),
            showgrid=False,
            showline=True,
            linecolor="#000000"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#DDDDDD",
            zeroline=False,
            range=[0, 36]
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40),
    )

    return fig

# App Dash
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"position": "relative", "fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        # Logo arriba a la derecha
        html.Img(
            src="/assets/logo.png",
            style={
                "position": "absolute",
                "top": "20px",
                "right": "30px",
                "height": "40px",
                "zIndex": "10"
            }
        ),

        # Título principal
        html.H1("Generación Sunnorte", style={
            "textAlign": "center",
            "color": "#000000",
            "marginBottom": "10px"
        }),

        # Gráfico con id para actualizar
        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False}),

        # KPI
        html.Div([
            html.H4("Energía Total Generada Hoy", style={"color": "#000000"}),
            html.P(id="kpi-generacion", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),

        # Última actualización
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"
        }),

        # Intervalo para refresco de datos cada 5 minutos
        dcc.Interval(id='interval-refresh', interval=5*60*1000, n_intervals=0),

        # Intervalo para animación cada 500 ms
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),

        # Guardar estado del pulso
        dcc.Store(id='pulso-estado', data=True)
    ]
)

# Callback para actualizar gráfico con efecto pulso
@app.callback(
    Output("grafico-generacion", "figure"),
    Output("pulso-estado", "data"),
    Input("interval-pulse", "n_intervals"),
    State("pulso-estado", "data"),
    State("interval-refresh", "n_intervals")
)
def actualizar_grafico_pulso(n_pulse, pulso_on, n_refresh):
    df = cargar_datos()
    fig = crear_figura(df, pulso_on)
    return fig, not pulso_on

# Callback para actualizar KPI y última actualización cada 5 minutos
@app.callback(
    Output("kpi-generacion", "children"),
    Output("ultima-actualizacion", "children"),
    Input("interval-refresh", "n_intervals")
)
def actualizar_kpi(n):
    df = cargar_datos()
    total = df["energia_MWh"].sum(skipna=True)
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    return f"{total:.1f} MWh", f"Última actualización: {ahora} hora Colombia"


if __name__ == "__main__":
    app.run_server(debug=True)
