import plotly.express as px

def plot_lap_trend(df):
    return px.line(df, x="lap_number", y="lap_duration",
                   title="Lap Time Trend")

def plot_delta(df):
    return px.bar(df, x="lap_number", y="delta",
                  title="Lap-by-Lap Delta vs. Teammate")

def plot_distribution(df):
    return px.histogram(df, x="lap_duration",
                       nbins=20, title="Lap Time Distribution")
