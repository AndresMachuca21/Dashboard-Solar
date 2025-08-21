import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State

# Función para cargar y preparar datos
def cargar_datos():
    # Datos de generación en tiempo real (Sunnorte)
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()
    df_por_hora = df_ultimo_dia[["hora", "Power MW"]]
    df_por_hora.rename(columns={"Power MW": "sunnorte_MWh"}, inplace=True)

    horas_completas = pd.date_range("00:00", "23:00", freq="h").strftime("%H:%M")
    df_completo = pd.DataFrame({"hora": horas_completas})
    df_final = df_completo.merge(df_por_hora, on="hora", how="left")

    # Datos de Ardobela (suma de plantas Frt76855 y Frt76857)
    df_ar = pd.read_csv("Ardobela.csv", sep=';')
    df_ar = df_ar[df_ar["CODIGO SIC"].isin(["Frt76855", "Frt76857"])]
    horas_cols = sorted([c for c in df_ar.columns if c.startswith("HORA")],
                        key=lambda x: int(x.split()[1]))
    energia_ar = df_ar[horas_cols].sum()
    df_ar_horas = pd.DataFrame({
        "hora": [f"{h:02d}:00" for h in range(24)],
        "ardobela_MWh": energia_ar.values
    })

    # Mostrar únicamente los datos hasta la hora actual
    hora_actual = datetime.now(ZoneInfo('America/Bogota')).hour
    df_ar_horas.loc[hora_actual:, "ardobela_MWh"] = pd.NA

    df_final = df_final.merge(df_ar_horas, on="hora", how="left")

    return df_final

# Función para crear la figura con efecto pulso
def crear_figura(df, pulso_on):
    if df[["sunnorte_MWh", "ardobela_MWh"]].dropna(how="all").empty:
        return go.Figure()

    fig = go.Figure()

    # Línea Sunnorte
    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["sunnorte_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6, color="#84B113"),
        fill="tozeroy",
        fillcolor="rgba(132, 177, 19, 0.05)",
        name="Sunnorte",
    ))

    # Línea Ardobela
    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["ardobela_MWh"],
        mode="lines+markers",
        line=dict(color="#FF7F0E", width=2),
        marker=dict(size=6, color="#FF7F0E"),
        name="Ardobela",
    ))

    # Variables para el efecto pulso
    size = 12 if pulso_on else 8
    opacity = 1 if pulso_on else 0.4

    # creación del punto final con efecto pulso para Sunnorte
    if df["sunnorte_MWh"].notna().any():
        hora_final_sn = df["hora"][df["sunnorte_MWh"].last_valid_index()]
        valor_final_sn = df["sunnorte_MWh"].dropna().iloc[-1]
        fig.add_trace(go.Scatter(
            x=[hora_final_sn],
            y=[valor_final_sn],
            mode="markers",
            marker=dict(size=size, color="#84B113", opacity=opacity, symbol="circle"),
            showlegend=False
        ))

    # creación del punto final con efecto pulso para Ardobela
    if df["ardobela_MWh"].notna().any():
        hora_final_ar = df["hora"][df["ardobela_MWh"].last_valid_index()]
        valor_final_ar = df["ardobela_MWh"].dropna().iloc[-1]
        fig.add_trace(go.Scatter(
            x=[hora_final_ar],
            y=[valor_final_ar],
            mode="markers",
            marker=dict(size=size, color="#FF7F0E", opacity=opacity, symbol="circle"),
            showlegend=False
        ))

    # layout
    fig.update_layout(
        autosize=True,
        xaxis_title=None,
        yaxis_title="Energía (MWh)",

        # Eje x
        xaxis=dict(
            categoryorder='array',
            categoryarray=df["hora"].tolist(),
            showgrid=False,
            showline=True,
            linecolor="#000000",

        ),

        # Eje y
        yaxis=dict(
            showgrid=True,
            gridcolor="#DDDDDD",
            zeroline=True,
            zerolinecolor="#000000",
            range=[0, 36]
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=10, b=0),
    )

    return fig

# Inicializar la app
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"position": "relative", "fontFamily": "Sans serif, Roboto", "padding": "10px", "backgroundColor": "#F2F2F2",
@@ -123,82 +162,109 @@ app.layout = html.Div(
                "zIndex": "1000"
            }
        ),
        
        # Título
        html.H1("Generación Sunnorte", style={
            "textAlign": "center",
            "color": "#000000",
            "marginBottom": "0px"
        }),

        # Fecha actual
        html.H4( "Hoy: " + datetime.now(ZoneInfo('America/Bogota')).strftime('%d/%m/%Y'), style={
            "textAlign": "left",
            "color": "#000000",
            "marginBottom": "15px",
            "marginTop": "0px",
            "marginLeft": "60px",
            "fontSize": "20px",

        }),
        
        # Gráfico de generación
        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False},style={"width": "100%", "height": "54vh"}),
        
        #KPIs
        html.Div([
            html.Div([
                html.H4("Sunnorte", style={"fontSize": "20px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-sunnorte", style={
                    "fontSize": "32px",
                    "color": "#84B113",
                    "marginTop": "5px"
                })
            ], style={"textAlign": "center"}),
            html.Div([
                html.H4("Ardobela", style={"fontSize": "20px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-ardobela", style={
                    "fontSize": "32px",
                    "color": "#FF7F0E",
                    "marginTop": "5px"
                })
            ], style={"textAlign": "center"}),
            html.Div([
                html.H4("Total", style={"fontSize": "20px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-total", style={
                    "fontSize": "32px",
                    "color": "#000000",
                    "marginTop": "5px"
                })
            ], style={"textAlign": "center"})
        ], style={"display": "flex", "justifyContent": "space-around", "marginTop": "0px", "marginBottom": "0px"}),
        
        # Última actualización
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "-10px", "fontSize": "12px", "color": "#777"
        }),

        # Intervalos para actualización y efecto pulso
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),  # cada minuto Grafica, KPI y hora
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),       # cada 1 segundo pulso
        dcc.Store(id='pulso-estado', data=True),
        dcc.Store(id='datos-generacion')
    ]
)

# Callback que actualiza datos, KPI y hora cada minuto
@app.callback(
    Output('datos-generacion', 'data'),
    Output('kpi-sunnorte', 'children'),
    Output('kpi-ardobela', 'children'),
    Output('kpi-total', 'children'),
    Output('ultima-actualizacion', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def actualizar_datos(n):
    df = cargar_datos()
    ahora = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')
    sunnorte_total = df["sunnorte_MWh"].sum(skipna=True)
    ardobela_total = df["ardobela_MWh"].sum(skipna=True)
    total = sunnorte_total + ardobela_total
    return (
        df.to_dict('records'),
        f"{sunnorte_total:.1f} MWh",
        f"{ardobela_total:.1f} MWh",
        f"{total:.1f} MWh",
        f"Última actualización: {ahora} hora Colombia"
    )

# Callback que actualiza la gráfica con efecto pulso cada segundo
@app.callback(
    Output('grafico-generacion', 'figure'),
    Output('pulso-estado', 'data'),
    Input('interval-pulse', 'n_intervals'),
    State('pulso-estado', 'data'),
    State('datos-generacion', 'data')
)
def actualizar_grafico(n_pulse, pulso_on, data):
    if not data or not isinstance(data, list):
        return go.Figure(), pulso_on
    try:
        df = pd.DataFrame(data)
    except Exception:
        return go.Figure(), pulso_on
    fig = crear_figura(df, pulso_on)
    return fig, not pulso_on

if __name__ == "__main__":
    app.run_server(debug=True)
