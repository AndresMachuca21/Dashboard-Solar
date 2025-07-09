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

# Función para crear figura con pulso
def crear_figura(df, pulso_on):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6, color="#84B113"),
        showlegend=False
    ))

    idx = df["energia_MWh"].last_valid_index()
    if idx is not None:
        hora_final = df.loc[idx, "hora"]
        valor_final = df.loc[idx, "energia_MWh"]

        size = 12 if pulso_on else 8
        opacity = 1 if pulso_on else 0.4

        fig.add_trace(go.Scatter(
            x=[hora_final],
            y=[valor_final],
            mode="markers",
            marker=dict(size=size, color="#84B113", opacity=opacity),
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

        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False}),

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

        # Intervalos
        dcc.Interval(id='interval-refresh', interval=5*60*1000, n_intervals=0),
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),

        # Estados
        dcc.Store(id='pulso-estado', data=True),
        dcc.Store(id='datos-guardados')
    ]
)

# Callback: Recarga datos cada 5 minutos
@app.callback(
    Output("datos-guardados", "data"),
    Output("kpi-generacion", "children"),
    Output("ultima-actualizacion", "children"),
    Input("interval-refresh", "n_intervals")
)
def recargar_datos(n):
    df = cargar_datos()
    total = df["energia_MWh"].sum(skipna=True)
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    return df.to_json(date_format="iso", orient="split"), f"{total:.1f} MWh", f"Última actualización: {ahora} hora Colombia"

# Callback: Actualiza gráfico con efecto pulso
@app.callback(
    Output("grafico-generacion", "figure"),
    Output("pulso-estado", "data"),
    Input("interval-pulse", "n_intervals"),
    State("pulso-estado", "data"),
    State("datos-guardados", "data")
)
def actualizar_grafico_pulso(n_pulse, pulso_on, datos_guardados):
    if datos_guardados is None:
        return go.Figure(), pulso_on  # evitar error en primer ciclo

    df = pd.read_json(datos_guardados, orient="split")
    fig = crear_figura(df, pulso_on)
    return fig, not pulso_on

# Ejecutar app
if __name__ == "__main__":
    app.run_server(debug=True)
