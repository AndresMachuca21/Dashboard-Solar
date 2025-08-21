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
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

    df_por_hora = df_ultimo_dia[["hora", "Power MW"]].rename(columns={"Power MW": "energia_MWh"})

    # Marco completo fijo 00:00..23:00
    base = pd.DataFrame({"hora": LABELS_00_23})
    df_final = base.merge(df_por_hora, on="hora", how="left")

    # Filtrar a horas ya transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df_final = df_final[df_final["hora"].isin(labels_ok)].copy()

    return df_final  # columnas: hora, energia_MWh (MWh)


# ------------------ Carga de datos Ardobela (sumar I+II con HORA 01 -> 01:00) ------------------
def cargar_ardobela():
    """
    Lee Ardobela.csv (sep=';'), filtra CODIGO SIC en [Frt76855, Frt76857],
    suma por hora y convierte kWh -> MWh.

    IMPORTANTE: Se mapea HORA 01 -> 01:00, ..., HORA 23 -> 23:00.
    HORA 24 (que sería 24:00) NO se mapea para mantener el eje 00..23.
    """
    df = pd.read_csv("Ardobela.csv", sep=';')
    df_sel = df[df["CODIGO SIC"].isin(["Frt76855", "Frt76857"])].copy()

    cols_presentes = [c for c in HORA_COLS if c in df_sel.columns]
    if not cols_presentes:
        return pd.DataFrame({"hora": horas_transcurridas_labels(), "energia_MWh": float("nan")})

    suma_kwh = df_sel[cols_presentes].sum(axis=0)  # Serie por 'HORA xx'

    # Construir serie kWh solo para HORA 01..23, mapeando a 01:00..23:00
    items = []
    for i in range(1, 24):  # 1..23
        col = f"HORA {i:02d}"
        if col in suma_kwh.index:
            items.append((f"{i:02d}:00", float(suma_kwh[col])))

    # Serie a DataFrame en MWh
    s_pairs = dict(items)  # {'01:00': kWh, ...}
    df_hora = pd.DataFrame({"hora": LABELS_00_23})
    df_hora["energia_MWh"] = df_hora["hora"].map(lambda h: (s_pairs.get(h, None) / 1000.0) if (h in s_pairs) else None)

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

    labels_ok = set(horas_transcurridas_labels())
    df = df[df["hora"].isin(labels_ok)].copy()
    return df


# ------------------ Figura con dos series (verdes), sin leyenda y pulso doble ------------------
def crear_figura_dos_series(df_sun, df_ard, pulso_on):
    sun = pd.DataFrame(df_sun) if isinstance(df_sun, list) else df_sun.copy()
    ard = pd.DataFrame(df_ard) if isinstance(df_ard, list) else df_ard.copy()

    fig = go.Figure()

    # === Trazo base invisible para fijar SIEMPRE las 24 categorías ===
    fig.add_trace(go.Scatter(
        x=LABELS_00_23,
        y=[0]*24,
        mode="lines",
        showlegend=False,
        hoverinfo="skip",
        opacity=0,
        line=dict(width=0)
    ))

    # Colores intercambiados:
    #   - Sunnorte ahora usa el verde Ecoener
    #   - Ardobela usa el verde oscuro
    verde_sunnorte = "#84B113"
    verde_ardobela = "#2E7D32"

    # Sunnorte
    if not sun.empty and not sun["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=sun["hora"], y=sun["energia_MWh"],
            mode="lines+markers",
            name="Sunnorte",
            line=dict(width=3, color=verde_sunnorte),
            marker=dict(size=6, color=verde_sunnorte),
            showlegend=False  # sin leyenda
        ))

    # Ardobela (I+II)
    if not ard.empty and not ard["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=ard["hora"], y=ard["energia_MWh"],
            mode="lines+markers",
            name="Ardobela (I+II)",
            line=dict(width=3, color=verde_ardobela),
            marker=dict(size=6, color=verde_ardobela),
            showlegend=False  # sin leyenda
        ))

    # ---- Pulso en AMBAS series (en su último punto válido) ----
    size = 12 if pulso_on else 8
    opacity = 1 if pulso_on else 0.4

    # Pulso Sunnorte
    if not sun.empty and not sun["energia_MWh"].dropna().empty:
        idx = sun["energia_MWh"].last_valid_index()
        hora_final = sun.loc[idx, "hora"]
        valor_final = float(sun["energia_MWh"].dropna().iloc[-1])
        fig.add_trace(go.Scatter(
            x=[hora_final], y=[valor_final],
            mode="markers",
            marker=dict(size=size, color=verde_sunnorte, opacity=opacity, symbol="circle"),
            showlegend=False,
            cliponaxis=False
        ))

    # Pulso Ardobela
    if not ard.empty and not ard["energia_MWh"].dropna().empty:
        idx = ard["energia_MWh"].last_valid_index()
        hora_final = ard.loc[idx, "hora"]
        valor_final = float(ard["energia_MWh"].dropna().iloc[-1])
        fig.add_trace(go.Scatter(
            x=[hora_final], y=[valor_final],
            mode="markers",
            marker=dict(size=size, color=verde_ardobela, opacity=opacity, symbol="circle"),
            showlegend=False,
            cliponaxis=False
        ))

    # Layout con EJE X FIJO de 24 horas y SIN leyenda
    fig.update_layout(
        autosize=True,
        showlegend=False,  # sin leyenda global
        xaxis_title=None,
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=LABELS_00_23,  # 00:00..23:00 siempre
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

        # KPIs: Sunnorte, Ardobelas, Total (gap reducido)
        html.Div([
            html.Div([
                html.H4("Sunnorte acumulado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-sunnorte", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Ardobelas acumulado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-ardobela", style={"fontSize": "28px", "color": "#2E7D32", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Total combinado", style={"fontSize": "18px", "color": "#000000", "marginBottom": "5px"}),
                html.P(id="kpi-total", style={"fontSize": "28px", "color": "#000000", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),
        ], style={"display": "flex", "gap": "4px", "marginTop": "0px", "marginBottom": "0px"}),

        # Última actualización
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "-10px", "fontSize": "12px", "color": "#777"
        }),

        # Intervalos
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),
        dcc.Store(id='pulso-estado', data=True),

        # Stores de datos
        dcc.Store(id='datos-ardobela'),
        dcc.Store(id='datos-sunnorte'),
        dcc.Store(id='datos-total')
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
)
def actualizar_grafico(n_pulse, pulso_on, data_sun, data_ard):
    try:
        fig = crear_figura_dos_series(data_sun or [], data_ard or [], pulso_on)
    except Exception:
        return go.Figure(), pulso_on
    return fig, not pulso_on


if __name__ == "__main__":
    app.run_server(debug=True)
