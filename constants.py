#!/usr/bin/env python3
"""
Constants for the Terraform Code Modifier application.

This file contains configuration values and constants used throughout the application.
"""

import os

# Google Cloud and Vertex AI configuration
PROJECT_ID = os.getenv("PROJECT_ID", "top-vial-429221-p6")
LOCATION = os.getenv("LOCATION", "us-central1")
API_ENDPOINT = os.getenv("API_ENDPOINT", "us-central1-aiplatform.googleapis.com")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-002")

# Generation configuration for Gemini
GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# Default paths
DEFAULT_OUTPUT_DIR = "./terraform_analysis"
DEFAULT_LOCAL_DIR = "./terraform_repo"
DEFAULT_BRANCH = "master"

# UI Configuration
PAGE_TITLE = "Terraform Code Modifier"
PAGE_ICON = "🔧"
PAGE_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

# Custom CSS for the Streamlit app
CUSTOM_CSS = """
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stButton button {
        width: 100%;
    }
    .file-header {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin-bottom: 0.5rem;
    }
    .file-content {
        margin-bottom: 1.5rem;
    }
</style>
"""

# Required dependencies
REQUIRED_DEPENDENCIES = {
    "networkx": "networkx",
    "git": "GitPython",
    "hcl2": "python-hcl2",
    "vertexai": "google-cloud-aiplatform",
    "matplotlib": "matplotlib",
    "plotly": "plotly",
}

# Installation instructions
INSTALL_INSTRUCTIONS = """
Please install the required dependencies:
```
pip install networkx GitPython python-hcl2 google-cloud-aiplatform streamlit matplotlib plotly
```

Or install from requirements.txt:
```
pip install -r requirements.txt
```
"""

# Example repository URLs
EXAMPLE_REPOS = """
**Correct format:**
- https://github.com/terraform-aws-modules/terraform-aws-vpc
- https://github.com/hashicorp/terraform-provider-aws

**Incorrect format:**
- https://github.com/terraform-aws-modules/terraform-aws-vpc/tree/master
- https://github.com/terraform-aws-modules/terraform-aws-vpc/blob/master/main.tf
"""

# Visualization colors
VIZ_COLORS = ["#4CAF50", "#2196F3", "#FFC107", "#F44336"]

# Update the PLOTLY_COLORBAR_CONFIG constant if it exists
PLOTLY_COLORBAR_CONFIG = {
    "thickness": 15,
    "title": "Node Type",
    "xanchor": "left",
    # No titleside property
} 