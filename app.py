import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

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

# Función para crear figura animada sin botón visible
def crear_figura(df):
    hora_final = df["hora"][df["energia_MWh"].last_valid_index()]
    valor_final = df["energia_MWh"].dropna().iloc[-1]

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

    # Punto animado ON
    frame_on = go.Scatter(
        x=[hora_final],
        y=[valor_final],
        mode="markers",
        marker=dict(size=18, color="#84B113", opacity=1, line=dict(color="#000", width=2)),
        showlegend=False
    )

    # Punto animado OFF
    frame_off = go.Scatter(
        x=[hora_final],
        y=[valor_final],
        mode="markers",
        marker=dict(size=8, color="#84B113", opacity=0.2),
        showlegend=False
    )

    # Agregar primer punto
    fig.add_trace(frame_on)

    # Agregar animación
    fig.frames = [
        go.Frame(data=[frame_on], name="pulse-on"),
        go.Frame(data=[frame_off], name="pulse-off")
    ]

    # Configurar animación automática al cargar
    fig.update_layout(
        xaxis_title="Hora",
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            categoryorder='array',
            categoryarray=df["hora"].tolist(),
            showgrid=False,
            gridcolor="#DDDDDD",
            showline=True,
            linecolor="#000000"
        ),
        yaxis=dict(
            showgrid=True,
            zeroline=False
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40),
        updatemenus=[],  # ← elimina el botón de animación
        sliders=[]       # ← elimina slider si existía
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
            "marginBottom": "40px"
        }),

        # Gráfico animado
        dcc.Graph(id="grafico-generacion", figure=crear_figura(cargar_datos()), animate=True),

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

        # Refrescar datos cada 5 minutos
        dcc.Interval(
            id='interval-component',
            interval=5 * 60 * 1000,  # 5 minutos en milisegundos
            n_intervals=0
        )
    ]
)

# Callback para actualizar datos
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
    return fig, f"{total:.1f} MWh", f"Última actualización: {ahora} hora Colombia"

# Ejecutar app
if __name__ == "__main__":
    app.run_server(debug=True)
