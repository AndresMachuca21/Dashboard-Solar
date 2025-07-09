from dash.dependencies import Input, Output

app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "30px", "backgroundColor": "#F2F2F2"},
    children=[
        html.Div([
            html.Img(
                src="/assets/logo.png",
                style={"height": "40px", "marginRight": "15px"}
            ),
            html.H1("Dashboard Planta Solar", style={"margin": "0", "color": "#84B113"})
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "30px", "justifyContent": "flex-start"}),

        dcc.Graph(id="graph"),

        html.Div([
            html.H4("Energía Total Generada Hoy", style={"color": "#000000"}),
            html.P(id="energia-total", style={
                "fontSize": "32px",
                "fontWeight": "bold",
                "color": "#84B113"
            })
        ], style={"textAlign": "center", "marginTop": "30px"}),

        html.Div(id="ultima-actualizacion", style={"textAlign": "center", "marginTop": "20px", "fontSize": "12px", "color": "#777"}),

        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # 5 minutos
            n_intervals=0
        )
    ]
)


@app.callback(
    [Output("graph", "figure"),
     Output("energia-total", "children"),
     Output("ultima-actualizacion", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    df = pd.read_csv("generacion_actual.csv", skiprows=1, sep=';')
    df["Ends"] = pd.to_datetime(df["Ends dd/mm/YYYY HH:MM"], dayfirst=True)
    df["Ends_col"] = df["Ends"].dt.tz_localize("UTC").dt.tz_convert("America/Bogota")
    df["hora"] = df["Ends_col"].dt.strftime("%H:%M")
    ultimo_dia = df["Ends_col"].dt.date.max()
    df_ultimo_dia = df[df["Ends_col"].dt.date == ultimo_dia].copy()

    df_ultimo_dia = df_ultimo_dia[["hora", "Power MW"]]
    df_ultimo_dia.rename(columns={"Power MW": "energia_MWh"}, inplace=True)

    fig = px.line(
        df_ultimo_dia,
        x="hora",
        y="energia_MWh",
        title="Generación Sunnorte",
        markers=True,
    )

    fig.update_traces(line=dict(color="#84B113", width=3))
    fig.update_layout(
        title_x=0.5,
        title_font_color="#000000",
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#FFFFFF",
        font=dict(color="#000000", family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis_title="Hora",
        yaxis_title="Energía (MWh)",
    )

    energia_total = df_ultimo_dia["energia_MWh"].sum()

    ultima_actualizacion = f"Última actualización: {datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M:%S')} hora Colombia"

    return fig, f"{energia_total:.1f} kWh", ultima_actualizacion


if __name__ == "__main__":
    app.run_server(debug=True)
