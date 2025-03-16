import marimo as mo
import numpy as np
import pandas as pd
import plotly.express as px


def create_sample_data(n_points: int = 1000) -> pd.DataFrame:
    """Creates a Pandas DataFrame with sample data for a scatter plot.

    Args:
    ----
        n_points: The number of data points to generate.

    Returns:
    -------
        A Pandas DataFrame containing 'x', 'y', and 'category' columns.

    """
    np.random.seed(42)
    return pd.DataFrame(
        {
            "x": np.random.normal(0, 1, n_points),
            "y": np.random.normal(0, 1, n_points),
            "category": np.random.choice(["A", "B", "C"], n_points),
        },
    )


def create_scatter_plot(data: pd.DataFrame) -> px.scatter:
    """Creates an interactive scatter plot using Plotly Express.

    Args:
    ----
        data: The Pandas DataFrame containing the data for the plot.

    Returns:
    -------
        A Plotly Express scatter plot figure.

    """
    return px.scatter(
        data,
        x="x",
        y="y",
        color="category",
        title="Interactive Scatter Plot",
    )


if __name__ == "__main__":
    mo.md("# Welcome to Marimo! 🌿")

    mo.md(
        """
    This is a sample notebook demonstrating some basic Marimo features.
    Let's create a simple interactive visualization.
    """,
    )

    # Create sample data
    data = create_sample_data()

    # Create an interactive scatter plot
    fig = create_scatter_plot(data)

    mo.hstack([mo.md("## Interactive Plot"), mo.as_html(fig)])
