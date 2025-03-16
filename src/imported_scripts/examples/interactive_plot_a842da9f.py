import marimo as mo
import numpy as np
import pandas as pd
import plotly.express as px

# Create the app
app = mo.App(name="Welcome")


@app.cell
def __imports():
    import marimo as mo

    return mo, np, pd, px


@app.cell
def intro(mo) -> None:
    mo.md("# Welcome to Marimo! 🌿")
    mo.md(
        """
    This is a sample notebook demonstrating some basic Marimo features.
    Let's create a simple interactive visualization.
    """,
    )


@app.cell
def create_data(np, pd):
    # Create sample data
    np.random.seed(42)
    n_points = 1000
    return pd.DataFrame(
        {
            "x": np.random.normal(0, 1, n_points),
            "y": np.random.normal(0, 1, n_points),
            "category": np.random.choice(["A", "B", "C"], n_points),
        },
    )


@app.cell
def plot(mo, px, data) -> None:
    # Create an interactive scatter plot
    fig = px.scatter(
        data,
        x="x",
        y="y",
        color="category",
        title="Interactive Scatter Plot",
    )

    mo.hstack([mo.md("## Interactive Plot"), mo.as_html(fig)])


if __name__ == "__main__":
    app.run()
