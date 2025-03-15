# TODO.md

## Human Tasks

-Set up the initial project repository on Git.
-Create the `.gitignore` file based on the conventions.md.
xReview the generated `conventions.md` file and make any necessary adjustments.
-Set up the `config/` directory and create initial placeholder files (e.g., `api_keys.yaml`, `database.yaml`).
xEnsure the correct Python version is installed and `uv` is set up.
xDecide on the first core module to start building (e.g., CRM, Accounting).

## LLM Tasks
### NOTE FROM THE USER: if you need context or have questions, you can always ask me for guidance once you've created the decisions.md

-Generate the initial `pyproject.toml` file with the following dependencies: `ibis-framework`, `duckdb`, `python-dotenv`, `ruff`, `pytest`.
-Create the basic directory structure for the `src/dewey/core/crm/` module, including an empty `__init__.py` file.
-In `src/dewey/utils.py`, write a simple Python function using Ibis to read a CSV file into an Ibis table expression. The function should take a file path as input.
-Create a basic `ui/screens/crm_screen.py` file with a placeholder function to display CRM information (can be just a print statement for now).
-In the `tests/core/`, create a `test_crm.py` file with a basic unit test example (e.g., testing the existence of a function in the CRM module).
-Generate a placeholder `docs/decisions.md` file.
-get to work on the llm helper function and setup helper functions for deepinfra and the google gemini api. the google gemini api is used to train models, so ensure that it is not used to interact with our databases and csvs, only python code
-make a plan to go step by step through my existing repositories and move our scripts/logic into our new project. folders in my home directory  with relevant info include bin, books, crm, ecic-compliance, grotius, lake, and Data

## Completed Tasks
