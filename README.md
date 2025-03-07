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

## Future Scope and QUESTIONS:

## 1. How can we store these entire codebases from the customer that we import?

The current implementation uses a temporary local file system approach:
- Repositories are cloned to a local directory (using `tempfile.mkdtemp()` in the Streamlit app)
- No persistent storage is implemented

**Recommended storage solutions:**
- **Object Storage**: Store repositories in cloud object storage (AWS S3, GCP Cloud Storage)
  - Each repository could be stored as a compressed archive
  - Metadata about repositories (structure, file paths, descriptions) stored separately
- **Document Database**: MongoDB or Firestore to store file contents and metadata
  - Each file as a document with path, content, description, and relationships
- **Graph Database**: Neo4j or Amazon Neptune for storing the dependency relationships
  - Nodes represent files, edges represent dependencies

For a complete solution, you'd need:
- A database for user accounts and repository metadata
- Object storage for raw repository content
- A caching layer for frequently accessed repositories

## 2. How do we fetch the relevant files from a massive codebase?

The current implementation has a basic approach:
- `identify_relevant_files()` in `TerraformCodeModifier` uses Gemini to identify relevant files
- It sends file information (paths, descriptions, dependencies) to the LLM

**Improved approaches:**
- **Semantic Search**: Embed file contents and descriptions using embeddings models
  - Store these embeddings in a vector database (Pinecone, Weaviate, etc.)
  - Search for relevant files based on the modification request
- **Dependency-Aware Retrieval**: Use the dependency graph to expand the set of relevant files
  - If a file is identified as relevant, also include its direct dependencies
- **Hierarchical Retrieval**: First identify relevant modules, then relevant files within those modules
- **Chunking Strategy**: Break large files into semantic chunks for more precise retrieval

## 3. Could we utilize an architecture like knowledge graphs, tree structure to represent and store the code?

The current implementation already uses a graph structure:
- `dependency_graph` (NetworkX DiGraph) in `TerraformRepoAnalyzer` 
- Nodes represent files, edges represent module dependencies

**Enhanced knowledge graph approach:**
- **Richer Node Types**: Expand beyond just files to include:
  - Resources (AWS, Azure, GCP resources)
  - Variables
  - Outputs
  - Providers
- **Richer Edge Types**: More relationship types:
  - "references" (when one resource references another)
  - "inherits from" (for module inheritance)
  - "configures" (when a variable configures a resource)
- **Property Graph**: Store properties on nodes and edges (e.g., resource types, variable values)
- **Hierarchical Structure**: Represent the module hierarchy explicitly

## 4. How will RAG be used here? Graph RAG perhaps?

The current implementation uses a basic RAG approach:
- It retrieves relevant files based on the modification request
- It provides these files as context to the LLM for generating modifications

**Enhanced RAG approaches:**
- **Graph RAG**: Use the dependency graph for context-aware retrieval
  - Traverse the graph to find related files based on dependencies
  - Use graph algorithms (PageRank, centrality) to identify important files
- **Multi-hop Retrieval**: Follow dependencies multiple hops to gather related context
- **Hybrid Retrieval**: Combine semantic search with graph-based retrieval
- **Chunked RAG**: Break files into semantic chunks for more precise retrieval
- **Recursive Retrieval**: Start with a small context, then recursively retrieve more context as needed

## 5. How can we utilize agent building here?

The current implementation has a monolithic approach with limited agent-like behavior:
- `TerraformRepoAnalyzer` analyzes repositories
- `TerraformCodeModifier` generates modifications

**Multi-agent architecture:**
1. **Repository Analyzer Agent**: Clones and analyzes repositories, builds dependency graphs
2. **File Identification Agent**: Identifies relevant files for a modification request
3. **Code Generation Agent**: Generates code modifications
4. **Code Review Agent**: Reviews generated code for correctness, security issues
5. **Testing Agent**: Generates and runs tests for the modified code
6. **Integration Agent**: Handles GitHub integration (PRs, comments)
7. **Orchestration Agent**: Coordinates the other agents, manages workflow

**Implementation approach:**
- Use a framework like LangChain or AutoGPT for agent orchestration
- Define clear interfaces between agents
- Implement a message-passing system for agent communication
- Use tools like GitHub API, Terraform CLI for specific tasks
- Implement feedback loops between agents (e.g., review → modify → review)

**Example workflow:**
```
User Request → Orchestrator → Analyzer → File Identifier → 
Code Generator → Code Reviewer → Tester → 
Integration Agent → GitHub PR → User Review
```

Each agent could be implemented as a separate service, allowing for better scaling and maintenance of the system.
