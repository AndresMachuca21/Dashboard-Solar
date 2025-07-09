import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

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

def crear_figura(df):
    fig = go.Figure()

    # Línea principal sin leyenda
    fig.add_trace(go.Scatter(
        x=df["hora"],
        y=df["energia_MWh"],
        mode="lines+markers",
        line=dict(color="#84B113", width=3),
        marker=dict(size=6),
        showlegend=False
    ))

    # Punto final parpadeante sin leyenda
    ultimo_valor = df["energia_MWh"].dropna().iloc[-1]
    ultima_hora = df["hora"][df["energia_MWh"].last_valid_index()]

    fig.add_trace(go.Scatter(
        x=[ultima_hora],
        y=[ultimo_valor],
        mode="markers",
        marker=dict(
            size=14,
            color="#84B113",
            opacity=1,
            line=dict(color="#000", width=2),
            symbol="circle"
        ),
        showlegend=False
    ))

    fig.update_layout(
        title=None,
        xaxis_title="Hora",
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            categoryorder='array',
            categoryarray=df["hora"].tolist(),
            showgrid=True,
            gridcolor="#CCCCCC"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#CCCCCC"
        ),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#F2F2F2",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40),
    )

    return fig

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

        html.H1("Generación Sunnorte", style={
            "textAlign": "center",
            "color": "#000000",
            "marginBottom": "40px"
        }),

        dcc.Graph(id="grafico-generacion", figure=crear_figura(cargar_datos())),

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

        dcc.Interval(
            id='interval-component',
            interval=5 * 60 * 1000,
            n_intervals=0
        )
    ]
)

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
    return fig, f"{total:.1f} kWh", f"Última actualización: {ahora} hora Colombia"

if __name__ == "__main__":
    app.run_server(debug=True)
