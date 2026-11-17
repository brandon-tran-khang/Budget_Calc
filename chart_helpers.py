"""Shared Plotly chart styling helpers to reduce repetition across tabs."""



def apply_default_layout(fig, height=350, time_series=False, **kwargs):
    """Apply standard chart styling to a Plotly figure (theme adapts via st.plotly_chart's streamlit theme)."""
    defaults = dict(
        height=height,
        font=dict(family="Public Sans, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=24, l=8, r=8, b=8),
        title=dict(text=""),
    )
    if time_series:
        defaults["hovermode"] = "x unified"
    defaults.update(kwargs)
    fig.update_layout(**defaults)
    fig.update_xaxes(gridcolor="rgba(128,140,134,.18)")
    fig.update_yaxes(gridcolor="rgba(128,140,134,.18)")
    return fig
