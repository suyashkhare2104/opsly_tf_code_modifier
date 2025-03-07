# Terraform Code Modifier

A powerful tool that uses AI to analyze and modify Terraform code based on natural language requests.

## Overview

This application provides a web interface for analyzing Terraform repositories and generating code modifications based on natural language instructions. It leverages Google's Gemini AI models to understand your Terraform codebase and implement requested changes.

## Features

- **Repository Analysis**: Clone and analyze Terraform repositories to build dependency graphs
- **Intelligent File Identification**: Identify relevant files for a specific modification request
- **AI-Powered Code Generation**: Generate code modifications using Gemini AI models
- **Interactive Visualization**: View dependency graphs of your Terraform modules
- **Web Interface**: User-friendly Streamlit interface for easy interaction

## How It Works

### 1. Repository Analysis

The application first clones the specified Terraform repository and analyzes its structure:

- Identifies all `.tf` and `.tf.json` files
- Parses each file to extract module dependencies
- Builds a dependency graph showing relationships between files
- Generates descriptions for each file using AI

### 2. File Identification

When you submit a modification request:

- The system uses AI to identify which files need to be modified
- It analyzes the dependency graph to understand relationships between files
- It presents the relevant files for review

### 3. Code Modification

Based on your natural language request:

- The AI generates modifications for each relevant file
- It maintains the structure and style of your existing code
- It presents the modified code for review
- You can apply the changes to the repository

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Git
- Google Cloud account with Vertex AI API enabled
- Google Cloud credentials (JSON key file)

### Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/yourusername/terraform-code-modifier.git
   cd terraform-code-modifier
   ```

2. **Set up a virtual environment** (optional but recommended):
   ```bash
   # Using the provided setup script
   python setup_venv.py
   
   # Activate the virtual environment
   # On Windows:
   terraform_analyzer_venv\Scripts\activate
   # On macOS/Linux:
   source terraform_analyzer_venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google Cloud credentials**:
   - Create a service account in Google Cloud Console
   - Grant it access to Vertex AI
   - Download the JSON key file
   - You'll upload this file in the web interface

### Running the Application

1. **Start the Streamlit web interface**:
   ```bash
   streamlit run terraform_streamlit.py
   ```

2. **Access the web interface**:
   - Open your browser and go to `http://localhost:8501`
   - The interface will guide you through the process

### Using the Application

1. **Enter repository information**:
   - Paste the GitHub URL of your Terraform repository
   - Specify the branch (defaults to "master")
   - Upload your Google Cloud credentials JSON file

2. **Analyze the repository**:
   - Click "Analyze Repository"
   - The system will clone the repository and build a dependency graph
   - You can explore the files and visualize dependencies

3. **Submit a modification request**:
   - Enter your request in natural language (e.g., "Add a new S3 bucket with versioning enabled")
   - Click "Identify Relevant Files" to see which files need to be modified
   - Click "Generate Modifications" to create the code changes

4. **Review and apply changes**:
   - Review the generated code modifications
   - Click "Apply Modifications" to write the changes to the files

## Command Line Usage

You can also use the tool from the command line:

```bash
python terraform_modifier.py https://github.com/username/repo "Add a new S3 bucket with versioning enabled" --branch main
```

## Configuration

You can customize the application by modifying the `constants.py` file:

- `PROJECT_ID`: Your Google Cloud project ID
- `LOCATION`: Google Cloud region for Vertex AI
- `MODEL_NAME`: Gemini model to use (defaults to "gemini-1.5-flash-002")
- Other UI and application settings

## Troubleshooting

- **Repository not found**: Ensure the GitHub URL is correct and publicly accessible
- **No Terraform files found**: Check if the repository contains `.tf` files
- **Authentication errors**: Verify your Google Cloud credentials have access to Vertex AI
- **Dependency errors**: Make sure all required packages are installed

## License

[MIT License](LICENSE)
