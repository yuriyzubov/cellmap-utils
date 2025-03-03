# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'cellmap-utils'
copyright = '2025, Yurii Zubov'
author = 'Yurii Zubov'
release = '0.0.16'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys
sys.path.insert(0, os.path.abspath("../src"))  # Ensure Sphinx finds your code

extensions = [
    "sphinx.ext.autodoc",      # Extracts docstrings
    "sphinx.ext.napoleon",     # Supports Google-style and NumPy-style docstrings
    "sphinx.ext.viewcode",     # Adds links to source code
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
