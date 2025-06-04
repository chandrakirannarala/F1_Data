import plotly.graph_objects as go

# Central color schemes used across visualizers
TEAM_COLORS = {
    "Red Bull Racing": "#1E41FF",
    "Mercedes": "#00D2BE",
    "Ferrari": "#DC143C",
    "McLaren": "#FF8700",
    "Alpine": "#0090FF",
    "Aston Martin": "#006F62",
    "Williams": "#005AFF",
    "AlphaTauri": "#2B4562",
    "Alfa Romeo": "#900000",
    "Haas": "#FFFFFF",
}

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFD700",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#00FF00",
    "WET": "#0066FF",
}


def apply_plot_style(
    fig: go.Figure, *, showlegend: bool = True, hovermode: str = "x unified"
) -> go.Figure:
    """Apply common layout styling to a Plotly figure."""
    fig.update_layout(
        template="plotly_white", hovermode=hovermode, showlegend=showlegend
    )
    return fig
