import marimo as mo

__generated_with = "0.1.0"
app = mo.App()


@app.cell
def imports():
    import json
    from datetime import datetime

    import pandas as pd

    return pd.DataFrame, json, datetime


@app.cell
def intro() -> None:
    mo.md(
        """
    # Company Analysis Input Manager

    This notebook helps manage the input data for the company analysis pipeline.
    You can:
    - Upload a CSV file of companies
    - Configure analysis parameters
    - Preview and validate the data
    - Trigger the analysis workflow
    """,
    )


@app.cell
def file_upload():
    mo.md("## Upload Companies CSV")
    return mo.file("Upload your companies CSV file", kind="text/csv")


@app.cell
def process_csv(file: mo.File, pd):
    if not file:
        return None

    df = pd.read_csv(file.data)
    required_cols = ["Company", "Symbol", "ISIN", "Category", "Sector"]

    # Validate columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        mo.md(f"⚠️ Missing required columns: {', '.join(missing_cols)}")
        return None

    return df


@app.cell
def display_preview(df):
    if df is None:
        mo.md("Please upload a CSV file to continue.")
        return None

    mo.md("## Data Preview")
    mo.md(f"Found {len(df)} companies")
    return df.head()


@app.cell
def analysis_params():
    mo.md("## Analysis Parameters")

    return {
        "batch_size": mo.slider(label="Batch Size", value=25, min=1, max=100),
        "confidence_threshold": mo.slider(
            label="Confidence Threshold",
            value=0.7,
            min=0,
            max=1,
            step=0.1,
        ),
        "model": mo.select(
            label="LLM Model",
            options=["gemini-pro", "deepseek-chat", "claude-2"],
        ),
        "include_sources": mo.checkbox(label="Include Sources", value=True),
    }


@app.cell
def validate_and_prepare(df, params, json, datetime):
    if df is None:
        mo.md("⚠️ Please upload data first")
        return None

    # Create configuration object
    config = {
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "batch_size": params["batch_size"].value,
            "confidence_threshold": params["confidence_threshold"].value,
            "model": params["model"].value,
            "include_sources": params["include_sources"].value,
        },
        "companies": df.to_dict(orient="records"),
    }

    mo.md("## Configuration Summary")
    mo.md(
        f"""
    - Batch Size: {config['parameters']['batch_size']}
    - Confidence Threshold: {config['parameters']['confidence_threshold']}
    - Model: {config['parameters']['model']}
    - Include Sources: {config['parameters']['include_sources']}
    - Total Companies: {len(config['companies'])}
    """,
    )

    return config


@app.cell
def trigger_flow(config, json, datetime):
    if config is None:
        return None

    # Save configuration to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_config_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(config, f, indent=2)

    mo.md(
        f"""
    ## Ready to Start Analysis

    Configuration saved to: `{filename}`

    To start the analysis:
    1. The configuration has been saved and is ready for the Prefect workflow
    2. The workflow will process companies in batches of {config['parameters']['batch_size']}
    3. Results will be available in the data structure notebook

    [View Analysis Progress](https://flow.sloane-collective.com)
    """,
    )
    return filename


if __name__ == "__main__":
    app.run()
