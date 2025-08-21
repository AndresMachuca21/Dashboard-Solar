import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State

TZ = ZoneInfo('America/Bogota')

# ---- Utilidades de horas ----
HORA_COLS = [f"HORA {i:02d}" for i in range(1, 25)]  # HORA 01 ... HORA 24
# En XM, HORA 01 = 00:00-00:59, HORA 02 = 01:00-01:59, ..., HORA 24 = 23:00-23:59
LABELS_00_23 = [f"{h:02d}:00" for h in range(24)]     # "00:00"..."23:00"

def horas_transcurridas_labels():
    ahora = datetime.now(TZ)
    # incluir solo horas COMPLETADAS: hasta (ahora.hour - 1)
    last_hour = max(0, ahora.hour - 1)
    return LABELS_00_23[: last_hour + 1]

# ---- Datos Sunnorte (igual a tu lógica, restringido a horas transcurridas) ----
def cargar_sunnorte():
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize(None)
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")

    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()
    df_por_hora = df_ultimo_dia[["hora", "Power MW"]].rename(columns={"Power MW": "energia_MWh"})

    # Marco completo "00:00" .. "23:00"
    base = pd.DataFrame({"hora": LABELS_00_23})
    df_final = base.merge(df_por_hora, on="hora", how="left")

    # Dejar solo horas ya transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df_final = df_final[df_final["hora"].isin(labels_ok)].copy()

    return df_final  # columnas: hora, energia_MWh (puede haber NaN si aún no hay dato)

# ---- Datos Ardobela (sumar Frt76855 + Frt76857; kWh -> MWh) ----
def cargar_ardobela():
    # Archivo subido con separador ';'
    df = pd.read_csv("Ardobela.csv", sep=';')

    # Filtrar dos filas requeridas y sumar por hora
    df_sel = df[df["CODIGO SIC"].isin(["Frt76855", "Frt76857"])].copy()
    # Asegurar columnas de hora en orden
    cols = [c for c in HORA_COLS if c in df_sel.columns]
    if not cols:
        # Si por alguna razón no están las columnas esperadas, devolver vacío con el marco horario
        return pd.DataFrame({"hora": horas_transcurridas_labels(), "energia_MWh": float("nan")})

    suma_kwh = df_sel[cols].sum(axis=0)  # Serie indexada por 'HORA 01'...'HORA 24'
    # Mapear 'HORA 01' → '00:00', ..., 'HORA 24' → '23:00'
    mapping = {f"HORA {i:02d}": f"{i-1:02d}:00" for i in range(1, 25)}
    s_mwh = (suma_kwh / 1000.0).rename(index=mapping)  # kWh → MWh y renombrar índice

    df_hora = pd.DataFrame({"hora": LABELS_00_23})
    df_hora["energia_MWh"] = df_hora["hora"].map(s_mwh)

    # Dejar solo horas ya transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df_hora = df_hora[df_hora["hora"].isin(labels_ok)].copy()

    return df_hora  # columnas: hora, energia_MWh (MWh)

# ---- Combinar Sunnorte + Ardobela para KPI total ----
def combinar_total(df_sun, df_ard):
    df = pd.DataFrame({"hora": LABELS_00_23})
    df = df.merge(df_sun[["hora", "energia_MWh"]].rename(columns={"energia_MWh": "sun"}),
                  on="hora", how="left")
    df = df.merge(df_ard[["hora", "energia_MWh"]].rename(columns={"energia_MWh": "ard"}),
                  on="hora", how="left")
    df["energia_MWh"] = df[["sun", "ard"]].sum(axis=1, skipna=True)
    # limitar a horas transcurridas
    labels_ok = set(horas_transcurridas_labels())
    df = df[df["hora"].isin(labels_ok)].copy()
    return df

# ---- Figura (graficamos Ardobela I+II como una sola) ----
def crear_figura(df, pulso_on):
    if df["energia_MWh"].dropna().empty:
        return go.Figure()

    hora_final = df["hora"][df["energia_MWh"].last_valid_index()]
    valor_final = df["energia_MWh"].dropna().iloc[-1]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6, color="#84B113"),
        fill='tozeroy',
        fillcolor='rgba(132, 177, 19, 0.05)',
        showlegend=False
    ))

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
        autosize=True,
        xaxis_title=None,
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            categoryorder='array',
            categoryarray=df["hora"].tolist(),
            showgrid=False,
            showline=True,
            linecolor="#000000",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#DDDDDD",
            zeroline=True,
            zerolinecolor="#000000",
            range=[0, 36]  # ajusta si tu escala típica cambia
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=10, b=0),
    )

    return fig

# ------------------ APP ------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"position": "relative", "fontFamily": "Sans serif, Roboto", "padding": "10px",
           "backgroundColor": "#F2F2F2", "maxWidth": "100%", "overflowX": "hidden"},
    children=[
        # Logo
        html.Img(
            src="/assets/logo.png",
            style={"position": "absolute","top": "10px","right": "10px","height": "20px","zIndex": "10"}
        ),
        # Mapa
        html.Img(
            src="/assets/gif_colombia.gif",
            style={"position": "absolute","bottom": "10px","right": "30px","height": "120px","zIndex": "1000"}
        ),

        # Título (aclaramos que el gráfico es Ardobela I+II)
        html.H1("Generación Ardobela (I+II)", style={
            "textAlign": "center", "color": "#000000", "marginBottom": "0px"
        }),

        # Fecha actual (dinámica)
        html.H4(id="fecha-actual", style={
            "textAlign": "left", "color": "#000000",
            "marginBottom": "15px", "marginTop": "0px",
            "marginLeft": "60px", "fontSize": "20px",
        }),

        # Gráfico (Ardobela I+II)
        dcc.Graph(id="grafico-generacion", config={"displayModeBar": False},
                  style={"width": "100%", "height": "54vh"}),

        # KPIs: Sunnorte, Ardobela, Total
        html.Div([
            html.Div([
                html.H4("Sunnorte acumulado", style={"fontSize": "18px", "color": "#000000","marginBottom": "5px"}),
                html.P(id="kpi-sunnorte", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Ardobela (I+II) acumulado", style={"fontSize": "18px", "color": "#000000","marginBottom": "5px"}),
                html.P(id="kpi-ardobela", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),

            html.Div([
                html.H4("Total combinado", style={"fontSize": "18px", "color": "#000000","marginBottom": "5px"}),
                html.P(id="kpi-total", style={"fontSize": "28px", "color": "#84B113", "marginTop": "5px"})
            ], style={"textAlign": "center", "flex": "1"}),
        ], style={"display": "flex", "gap": "10px", "marginTop": "0px", "marginBottom": "0px"}),

        # Última actualización
        html.Div(id="ultima-actualizacion", style={
            "textAlign": "center", "marginTop": "-10px", "fontSize": "12px", "color": "#777"
        }),

        # Intervalos (igual que tenías)
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dcc.Interval(id='interval-pulse', interval=1000, n_intervals=0),
        dcc.Store(id='pulso-estado', data=True),

        # Stores de datos
        dcc.Store(id='datos-ardobela'),    # serie Ardobela I+II por hora
        dcc.Store(id='datos-sunnorte'),    # serie Sunnorte por hora
        dcc.Store(id='datos-total')        # combinada (para KPI total)
    ]
)

# ---- Callback principal: carga datos + KPIs + fecha ----
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

# ---- Callback del gráfico (usa Ardobela I+II) con pulso ----
@app.callback(
    Output('grafico-generacion', 'figure'),
    Output('pulso-estado', 'data'),
    Input('interval-pulse', 'n_intervals'),
    State('pulso-estado', 'data'),
    State('datos-ardobela', 'data')
)
def actualizar_grafico(n_pulse, pulso_on, data_ard):
    if not data_ard or not isinstance(data_ard, list):
        return go.Figure(), pulso_on
    try:
        df = pd.DataFrame(data_ard)
    except Exception:
        return go.Figure(), pulso_on
    fig = crear_figura(df, pulso_on)
    return fig, not pulso_on

if __name__ == "__main__":
    app.run_server(debug=True)
