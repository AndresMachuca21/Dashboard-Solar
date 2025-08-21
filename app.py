def crear_figura_dos_series(df_sun, df_ard, pulso_on):
    sun = pd.DataFrame(df_sun) if isinstance(df_sun, list) else df_sun.copy()
    ard = pd.DataFrame(df_ard) if isinstance(df_ard, list) else df_ard.copy()

    fig = go.Figure()

    # === Trazo base invisible para fijar SIEMPRE las 24 categorías ===
    # Esto garantiza que el eje X tenga 00:00..23:00, aunque no haya datos aún.
    fig.add_trace(go.Scatter(
        x=LABELS_00_23,
        y=[0]*24,                 # puede ser 0; no afecta porque y-axis está fijado [0,36]
        mode="lines",
        showlegend=False,
        hoverinfo="skip",
        opacity=0,                # completamente invisible
        line=dict(width=0)
    ))

    # Colores (dos tonos de verde)
    verde_oscuro = "#2E7D32"   # Sunnorte
    verde_ecoener = "#84B113"  # Ardobela

    # Sunnorte
    if not sun.empty and not sun["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=sun["hora"], y=sun["energia_MWh"],
            mode="lines+markers",
            name="Sunnorte",
            line=dict(width=3, color=verde_oscuro),
            marker=dict(size=6, color=verde_oscuro),
            showlegend=True
        ))

    # Ardobela (I+II)
    if not ard.empty and not ard["energia_MWh"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=ard["hora"], y=ard["energia_MWh"],
            mode="lines+markers",
            name="Ardobela (I+II)",
            line=dict(width=3, color=verde_ecoener),
            marker=dict(size=6, color=verde_ecoener),
            showlegend=True
        ))

    # ---- Pulso en la serie con mayor último valor (para alejarlo del eje X) ----
    candidatos = []
    if not sun.empty and not sun["energia_MWh"].dropna().empty:
        idx_sun = sun["energia_MWh"].last_valid_index()
        candidatos.append(("sun", sun.loc[idx_sun, "hora"], float(sun["energia_MWh"].dropna().iloc[-1]), verde_oscuro))
    if not ard.empty and not ard["energia_MWh"].dropna().empty:
        idx_ard = ard["energia_MWh"].last_valid_index()
        candidatos.append(("ard", ard.loc[idx_ard, "hora"], float(ard["energia_MWh"].dropna().iloc[-1]), verde_ecoener))

    if candidatos:
        serie_pulso = max(candidatos, key=lambda t: t[2])
        _, hora_final, valor_final, color_pulso = serie_pulso

        size = 12 if pulso_on else 8
        opacity = 1 if pulso_on else 0.4
        fig.add_trace(go.Scatter(
            x=[hora_final], y=[valor_final],
            mode="markers",
            marker=dict(size=size, color=color_pulso, opacity=opacity, symbol="circle"),
            showlegend=False,
            cliponaxis=False  # evita que el pulso "choque" visualmente con el eje
        ))

    # Layout con EJE X FIJO de 24 horas
    fig.update_layout(
        autosize=True,
        xaxis_title=None,
        yaxis_title="Energía (MWh)",
        xaxis=dict(
            type='category',
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
