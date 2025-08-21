import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State

# ------------------ Zona horaria y constantes ------------------
TZ = ZoneInfo('America/Bogota')

# Columnas esperadas en Ardobela.csv
HORA_COLS = [f"HORA {i:02d}" for i in range(1, 25)]  # HORA 01 ... HORA 24

# Etiquetas fijas para el eje X: 00:00 ... 23:00
LABELS_00_23 = [f"{h:02d}:00" for h in range(24)]


def horas_transcurridas_labels():
    """
    Devuelve las etiquetas de horas COMPLETADAS hasta la hora anterior a la actual en Bogotá.
    Ej.: Si son 21:15, devuelve hasta "20:00".
    """
    ahora = datetime.now(TZ)
    last_hour = max(0, ahora.hour - 1)
    return LABELS_00_23[: last_hour + 1]


# ------------------ Carga de datos Sunnorte (tu lógica base) ------------------
def cargar_sunnorte():
    # Lee tu archivo de Sunnorte
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    # Último día disponible
    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

    # Selección y renombre
    df_por_hora = df_ultimo_dia[["hora", "Power MW"]].rename(columns={"Power MW": "energia_MWh"})

    # Marco completo fijo 00:00..23:00
    base = pd.DataFrame({"hora": LABELS_00_23})
    df_final = base.merge(df_por_hora, on="hora", how="left")

    # Filtrar a horas ya transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df_final = df_final[df_final["hora"].isin(labels_ok)].copy()

    return df_final  # columnas: hora, energia_MWh (MWh)


# ------------------ Carga de datos Ardobela (sumar I+II) ------------------
def cargar_ardobela():
    """
    Lee Ardobela.csv (sep=';'), filtra CODIGO SIC en [Frt76855, Frt76857],
    suma por hora y convierte kWh -> MWh.
    """
    df = pd.read_csv("Ardobela.csv", sep=';')

    df_sel = df[df["CODIGO SIC"].isin(["Frt76855", "Frt76857"])].copy()

    # Asegurar columnas de hora en orden; si no existen, retornar NaN con marco horario
    cols = [c for c in HORA_COLS if c in df_sel.columns]
    if not cols:
        return pd.DataFrame({"hora": horas_transcurridas_labels(), "energia_MWh": float("nan")})

    # Suma de kWh por hora entre ambas plantas
    suma_kwh = df_sel[cols].sum(axis=0)  # Serie indexada por HORA 01 ... HORA 24

    # Mapear HORA 01 -> 00:00, ..., HORA 24 -> 23:00
    mapping = {f"HORA {i:02d}": f"{i-1:02d}:00" for i in range(1, 25)}

    # Convertir a MWh
    s_mwh = (suma_kwh / 1000.0).rename(index=mapping)  # kWh → MWh

    # Llevar a DataFrame con eje horario fijo
    df_hora = pd.DataFrame({"hora": LABELS_00_23})
    df_hora["energia_MWh"] = df_hora["hora"].map(s_mwh)

    # Filtrar a horas ya transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df_hora = df_hora[df_hora["hora"].isin(labels_ok)].copy()

    return df_hora  # columnas: hora, energia_MWh (MWh)


# ------------------ Total combinado (Sunnorte + Ardobela) ------------------
def combinar_total(df_sun, df_ard):
    df = pd.DataFrame({"hora": LABELS_00_23})
    df = df.merge(df_sun[["hora", "energia_MWh"]].rename(columns={"energia_MWh": "sun"}),
                  on="hora", how="left")
    df = df.merge(df_ard[["hora", "energia_MWh"]].rename(columns={"energia_MWh": "ard"}),
                  on="hora", how="left")
    df["energia_MWh"] = df[["sun", "ard"]].sum(axis=1, skipna=True)

    # Limitar a horas transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df = df[df["hora"].isin(labels_ok)].copy()
    return df  # columnas: hora, sun, ard, energia_MWh(=total)


# ------------------ Figura multi-serie con pulso en Total ------------------
def crear_figura_multi(df_sun, df_ard, df_tot, pulso_on):
    sun = pd.DataFrame(df_sun) if isinstance(df_sun, list) else df_sun.copy()
    ard = pd.DataFrame(df_ard) if isinstance(df_ard, list) else df_ard.copy()
    tot = pd.DataFrame(df_tot) if isinstance(df_tot, list) else df_tot.copy()

    # Si no hay datos en total, figura vacía
    if tot.empty or tot["energia_MWh"].dropna().empty:
        # Eje X fijo aunque esté vacío
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(
                categoryorder='array',
                categoryarray=LABELS_00_23,  # EJE X FIJO
                showgrid=False,
                showline=True,
                linecolor="#000000",
            ),
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
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    fig = go.Figure()

    # Sunnorte
    if not sun.empty and not sun["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=sun["hora"], y=sun["energia_MWh"],
            mode="lines+markers",
            name="Sunnorte",
            line=dict(width=2, color="#1f77b4"),   # azul
            marker=dict(size=5, color="#1f77b4"),
            showlegend=True
        ))

    # Ardobela (I+II)
    if not ard.empty and not ard["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=ard["hora"], y=ard["energia_MWh"],
            mode="lines+markers",
            name="Ardobela (I+II)",
            line=dict(width=3, color="#84B113"),
            marker=dict(size=6, color="#84B113"),
            fill='tozeroy',
            fillcolor='rgba(132, 177, 19, 0.05)',
            showlegend=True
        ))

    # Total
    if not tot.empty and not tot["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=tot["hora"], y=tot["energia_MWh"],
            mode="lines",
            name="Total",
            line=dict(width=2.5, color="#000000", dash="dot"),
            showlegend=True
        ))

        # Punto con pulso en TOTAL
        hora_final = tot["hora"][tot["energia_MWh"].last_valid_index()]
        valor_final = tot["energia_MWh"].dropna().iloc[-1]
        size = 12 if pulso_on else 8
        opacity = 1 if pulso_on else 0.4
        fig.add_trace(go.Scatter(
            x=[hora_final], y=[valor_final],
            mode="markers",
            marker=dict(size=size, color="#000000", opacity=opacity, symbol="circle"),
            showlegend=False
        ))

    # Layout con eje X FIJO
    fig.update_layout(
        autosize=True,
        xaxis_title=None,
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            categoryorder='array',
            categoryarray=LABELS_00_23,  # EJE X SIEMPRE FIJO 00:00..23:00
            showgrid=False,
            showline=True,
            linecolor="#000000",
        ),
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


# ------------------ App Dash ------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"position": "relative", "fontFamily": "Sans serif, Roboto", "padding": "10px",
           "backgroundColor": "#F2F2F2", "maxWidth": "100%", "overflowX": "hidden"},
    children=[
        # Logo
        html.Img(
            src="/assets/logo.png",
            style={"position": "absolute", "top": "10px", "right": "10px", "height": "20px", "zIndex": "10"}
        ),
        # Mapa
        html.Img(
            src="/assets/gif_colombia.gif",
            style={"position": "absolute", "bottom": "10px", "right": "30px", "height": "120px", "zIndex": "1000"}
        ),

        # Título
        html.H1("Generación Ecoener Colombia", style={
            "textAlign": "center", "color": "#000000", "marginBottom": "0px"
        }),

        # Fecha actual (dinámica)
        html.H4(id="fecha-actual", style={
            "textAlign": "left", "color": "#000000",
            "marginBottom": "15px", "marginTop": "0px",
            "marginLeft": "60px", "fontSize": "20px",
        }),

        # Gráfico
        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False},
                  style={"width": "100%", "height": "54vh"}),

        # KPIs: Sunnorte, Ardobela, Total
        html.Div([
            html.Div([
                html.H4("Sunnorte acumulado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-sunnorte", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Ardobela (I+II) acumulado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-ardobela", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Total combinado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-total", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),
        ], style={"display": "flex", "gap": "10px", "marginTop": "0px", "marginBottom": "0px"}),

        # Última actualización
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "-10px", "fontSize": "12px", "color": "#777"
        }),

        # Intervalos
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),  # cada minuto recarga datos/KPI/fecha
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),       # cada 1s pulso
        dcc.Store(id='pulso-estado', data=True),

        # Stores de datos
        dcc.Store(id='datos-ardobela'),    # serie Ardobela I+II por hora
        dcc.Store(id='datos-sunnorte'),    # serie Sunnorte por hora
        dcc.Store(id='datos-total')        # combinada (para KPI total y gráfico)
    ]
)


# ------------------ Callbacks ------------------
@app.callback(
    Output('datos-ardobela', 'data'),
    Output('datos-sunnorte', 'data'),
    Output('datos-total', 'data'),
    Output('kpi-sunnorte', 'children'),
    Output('kpi-ardobela', 'children'),
    Output('kpi-total', 'children'),
    Output('ultima-actualizacion', 'children'),
    Output('fecha-actual', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def actualizar_datos(n):
    df_sun = cargar_sunnorte()
    df_ard = cargar_ardobela()
    df_tot = combinar_total(df_sun, df_ard)

    kpi_sun = df_sun["energia_MWh"].sum(skipna=True)
    kpi_ard = df_ard["energia_MWh"].sum(skipna=True)
    kpi_tot = df_tot["energia_MWh"].sum(skipna=True)

    ahora_txt = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    fecha_txt = "Hoy: " + datetime.now(TZ).strftime('%d/%m/%Y')

    return (
        df_ard.to_dict('records'),
        df_sun.to_dict('records'),
        df_tot.to_dict('records'),
        f"{kpi_sun:.1f} MWh",
        f"{kpi_ard:.1f} MWh",
        f"{kpi_tot:.1f} MWh",
        f"Última actualización: {ahora_txt} hora Colombia",
        fecha_txt
    )


@app.callback(
    Output('grafico-generacion', 'figure'),
    Output('pulso-estado', 'data'),
    Input('interval-pulse', 'n_intervals'),
    State('pulso-estado', 'data'),
    State('datos-sunnorte', 'data'),
    State('datos-ardobela', 'data'),
    State('datos-total', 'data'),
)
def actualizar_grafico(n_pulse, pulso_on, data_sun, data_ard, data_tot):
    try:
        fig = crear_figura_multi(data_sun or [], data_ard or [], data_tot or [], pulso_on)
    except Exception:
        return go.Figure(), pulso_on
    return fig, not pulso_on


if __name__ == "__main__":
    app.run_server(debug=True)
