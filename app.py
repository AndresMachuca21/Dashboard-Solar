import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State

# Función para cargar y preparar datos
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

# Función para crear figura con efecto pulso
def crear_figura(df, pulso_on):
    hora_final = df["hora"][df["energia_MWh"].last_valid_index()]
    valor_final = df["energia_MWh"].dropna().iloc[-1]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6, color="#84B113"),
        showlegend=False
    ))

    # Punto con pulso
    size = 12 if pulso_on else 8
    opacity = 1 if pulso_on else 0.4

    fig.add_trace(go.Scatter(
        x=[hora_final],
        y=[valor_final],
        mode="markers",
        marker=dict(size=size, color="#84B113", opacity=opacity, symbol="circle"),
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

# Inicializar la app
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
            "marginBottom": "5px"
        }),
        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False}),
        html.Div([
            html.H4("Producción acumulada", style={"color": "#000000"}),
            html.P(id="kpi-generacion", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"
        }),
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),  # cada minuto
        dcc.Interval(id='interval-pulse', interval=500, n_intervals=0),        # cada 0.5s
        dcc.Store(id='pulso-estado', data=True),
        dcc.Store(id='datos-generacion')  # datos compartidos
    ]
)

# Callback para cargar datos cada minuto
@app.callback(
    Output('datos-generacion', 'data'),
    Output('kpi-generacion', 'children'),
    Output('ultima-actualizacion', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def actualizar_datos(n):
    df = cargar_datos()
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    total = df["energia_MWh"].sum(skipna=True)
    return df.to_dict('records'), f"{total:.1f} MWh", f"Última actualización: {ahora} hora Colombia"

# Callback para animar el gráfico con pulso cada 0.5s
@app.callback(
    Output('grafico-generacion', 'figure'),
    Output('pulso-estado', 'data'),
    Input('interval-pulse', 'n_intervals'),
    State('pulso-estado', 'data'),
    State('datos-generacion', 'data')
)
def actualizar_grafico(n_pulse, pulso_on, data):
    if data is None:
        return go.Figure(), pulso_on
    df = pd.DataFrame(data)
    fig = crear_figura(df, pulso_on)
    return fig, not pulso_on

if __name__ == "__main__":
    app.run_server(debug=True)
