"""Shared Plotly chart styling helpers to reduce repetition across tabs."""

import plotly.express as px


def apply_default_layout(fig, height=350, **kwargs):
    """Apply standard chart styling to a Plotly figure."""
    defaults = dict(
        template="plotly_white",
        height=height,
    )
    defaults.update(kwargs)
    fig.update_layout(**defaults)
    return fig


def make_pie_chart(data, values, names, height=350, **kwargs):
    """Create a consistently styled donut chart."""
    color_seq = kwargs.pop('color_discrete_sequence', px.colors.qualitative.Prism)
    fig = px.pie(
        data, values=values, names=names, hole=0.6,
        color_discrete_sequence=color_seq,
    )
    fig.update_layout(
        height=height,
        showlegend=kwargs.pop('showlegend', True),
        margin=kwargs.pop('margin', dict(t=10, b=0, l=0, r=0)),
        **kwargs,
    )
    return fig
