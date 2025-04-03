"""Configuration file for the Sphinx documentation builder.

For the full list of configuration options, see:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import sys
from datetime import datetime
from pathlib import Path

# -- Path Setup --------------------------------------------------------------

# Add project directory to Python path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

# -- Project Information -----------------------------------------------------

project = "Dewey"
copyright = f"{datetime.now().year}, Sloane Ortel"
author = "Sloane Ortel"
release = "0.1.0"

# -- General Configuration ---------------------------------------------------

# Extensions
extensions = [
    # Core
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    # Additional
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
    # Third-party
    "myst_parser",
    "sphinxcontrib.mermaid",
]

# Source file types
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
    ".txt": "restructuredtext",
}

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Autodoc Configuration ---------------------------------------------------

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
}

autodoc_typehints = "description"
autoclass_content = "both"

# -- Intersphinx Configuration -----------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

# -- HTML Output Options -----------------------------------------------------

html_theme = "alabaster"

# Mermaid diagram support
extensions.append("sphinxcontrib.mermaid")
mermaid_output_format = "png"
mermaid_version = "10.6.1"
mermaid_cmd = "mmdc"
mermaid_params = ["-t", "neutral", "-p", "puppeteer-config.json"]
mermaid_init_js = "mermaid.initialize({startOnLoad:true});"
html_static_path = ["_static"]
html_theme_options = {
    "github_button": True,
    "github_user": "yourusername",
    "github_repo": "dewey",
}

# -- Extension Settings ------------------------------------------------------

# MyST Parser
myst_enable_extensions = ["colon_fence", "deflist", "linkify", "attrs_inline"]

myst_heading_anchors = 3
myst_heading_slug_func = "lower"

# TODO extension
todo_include_todos = True
