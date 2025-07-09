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

# Crear figura con animación de pulso
def crear_figura(df, pulso_activo=True):
    fig = go.Figure()

    # Línea base
    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6),
        showlegend=False
    ))

    # Último punto
    idx_final = df["energia_MWh"].last_valid_index()
    if idx_final is not None:
        hora_final = df["hora"].iloc[idx_final]
        valor_final = df["energia_MWh"].iloc[idx_final]

        punto_size = 18 if pulso_activo else 8
        punto_opacity = 1 if pulso_activo else 0.3

        fig.add_trace(go.Scatter(
            x=[hora_final],
            y=[valor_final],
            mode="markers",
            marker=dict(size=punto_size, color="#84B113", opacity=punto_opacity, line=dict(color="#000", width=2)),
            showlegend=False
        ))

    # Estilo
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
            range=[0, 35]
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40)
    )

    return fig

# App Dash
app = Dash(__name__)
server = app.server

# Layout
app.layout = html.Div(
    style={"position": "relative", "fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        # Logo
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

        html.H1("Generación Sunnorte", style={
            "textAlign": "center",
            "color": "#000000",
            "marginBottom": "40px"
        }),

        dcc.Graph(id="grafico-generacion", animate=False, config={"displayModeBar": False}),
        
        html.Div([
            html.H4("Energía Total Generada Hoy", style={"color": "#000000"}),
            html.P(id="kpi-generacion", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),

        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"
        }),

        # Refrescar datos cada 5 minutos
        dcc.Interval(
            id='interval-refresh',
            interval=5 * 60 * 1000,
            n_intervals=0
        ),

        # Animar punto cada 500ms
        dcc.Interval(
            id='interval-pulso',
            interval=500,
            n_intervals=0
        ),

        # Estado de animación del pulso
        dcc.Store(id='pulso-estado', data=True)
    ]
)

# Callback para animar el punto (cambiar tamaño)
@app.callback(
    Output("grafico-generacion", "figure"),
    Output("pulso-estado", "data"),
    Input("interval-pulso", "n_intervals"),
    State("pulso-estado", "data")
)
def actualizar_pulso(n, pulso_activo):
    df = cargar_datos()
    fig = crear_figura(df, pulso_activo)
    return fig, not pulso_activo  # alterna entre True/False

# Callback para actualizar datos y KPI cada 5 minutos
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

# Cargar gráfico por primera vez
@app.callback(
    Output("grafico-generacion", "figure"),
    Input("grafico-generacion", "id")
)
def cargar_inicial(_):
    df = cargar_datos()
    return crear_figura(df, pulso_activo=True)

# Ejecutar servidor
if __name__ == "__main__":
    app.run_server(debug=True)
