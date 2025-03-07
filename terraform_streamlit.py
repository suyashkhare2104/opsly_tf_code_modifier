#!/usr/bin/env python3
"""
Terraform Code Modification Streamlit App

This script provides a web interface for modifying Terraform code based on
natural language requests, using the TerraformRepoAnalyzer and TerraformCodeModifier.
"""

import os
import sys
import re
import streamlit as st
import tempfile
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.colors import LinearSegmentedColormap

# Import the analyzer and modifier
from terraform_analyzer import TerraformRepoAnalyzer
from terraform_modifier import TerraformCodeModifier

# Import constants
from constants import (
    PROJECT_ID, LOCATION, MODEL_NAME, GENERATION_CONFIG,
    DEFAULT_OUTPUT_DIR, DEFAULT_LOCAL_DIR, DEFAULT_BRANCH,
    PAGE_TITLE, PAGE_ICON, PAGE_LAYOUT, SIDEBAR_STATE,
    CUSTOM_CSS, REQUIRED_DEPENDENCIES, INSTALL_INSTRUCTIONS,
    EXAMPLE_REPOS, VIZ_COLORS
)

# Set page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=PAGE_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE
)

# Add custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Define the read_file_content function first
def read_file_content(analyzer, file_path):
    """
    Read the content of a file.
    
    Args:
        analyzer: The TerraformRepoAnalyzer instance
        file_path (str): Path to the file (relative to repository root)
        
    Returns:
        str: Content of the file
    """
    # Handle both absolute and relative paths
    if os.path.isabs(file_path):
        full_path = file_path
    else:
        # Remove any leading slashes to ensure it's treated as relative
        file_path = file_path.lstrip('/')
        full_path = os.path.join(analyzer.local_dir, file_path)
    
    try:
        # Check if the file exists
        if not os.path.exists(full_path):
            # Try to find the file by searching the repository
            possible_matches = []
            for root, dirs, files in os.walk(analyzer.local_dir):
                for file in files:
                    if file == os.path.basename(file_path):
                        possible_matches.append(os.path.join(root, file))
            
            if possible_matches:
                # Use the first match
                full_path = possible_matches[0]
                return f"File found at alternative location: {os.path.relpath(full_path, analyzer.local_dir)}\n\n" + open(full_path, 'r').read()
            else:
                return f"Error: File not found: {file_path}"
        
        with open(full_path, 'r') as f:
            return f.read()
    except Exception as e:
        # Try to find similar files as a fallback
        try:
            base_name = os.path.basename(file_path)
            similar_files = []
            for root, dirs, files in os.walk(analyzer.local_dir):
                for file in files:
                    if file.endswith('.tf') and (base_name in file or file in base_name):
                        similar_files.append(os.path.join(root, file))
            
            if similar_files:
                similar_files_text = "\n".join([f"- {os.path.relpath(f, analyzer.local_dir)}" for f in similar_files[:5]])
                return f"Error reading file: {str(e)}\n\nSimilar files found:\n{similar_files_text}"
        except:
            pass
        
        return f"Error reading file: {str(e)}"

def check_dependencies():
    """Check if all required dependencies are installed."""
    missing_deps = []
    installation_needed = False
    
    for module, package in REQUIRED_DEPENDENCIES.items():
        try:
            __import__(module)
        except ImportError:
            missing_deps.append(package)
            installation_needed = True
    
    if installation_needed:
        st.error(f"Missing dependencies: {', '.join(missing_deps)}")
        st.info(INSTALL_INSTRUCTIONS)
        st.stop()

# Call the dependency check at the start
check_dependencies()

def clean_github_url(url):
    """
    Clean a GitHub URL to make it suitable for cloning.
    
    Args:
        url (str): GitHub URL that might contain web UI elements
        
    Returns:
        str: Clean URL suitable for git clone
    """
    # Remove /tree/{branch} from GitHub URLs
    url = re.sub(r'/tree/[^/]+/?$', '', url)
    url = re.sub(r'/tree/[^/]+/', '/', url)
    
    # Remove /blob/{branch} from GitHub URLs
    url = re.sub(r'/blob/[^/]+/?$', '', url)
    url = re.sub(r'/blob/[^/]+/', '/', url)
    
    # Ensure the URL doesn't end with .git if it's a GitHub URL (GitHub adds this automatically)
    if 'github.com' in url and url.endswith('.git'):
        url = url[:-4]
    
    # Ensure the URL doesn't end with a slash
    url = url.rstrip('/')
    
    return url

def visualize_dependency_graph(graph):
    """
    Create a visualization of the dependency graph.
    
    Args:
        graph (nx.DiGraph): The dependency graph
        
    Returns:
        str: Base64 encoded PNG image of the graph
    """
    plt.figure(figsize=(12, 8))
    
    # Create a custom colormap for nodes
    cmap = LinearSegmentedColormap.from_list("terraform_cmap", VIZ_COLORS, N=100)
    
    # Use a spring layout for the graph
    pos = nx.spring_layout(graph, seed=42)
    
    # Get node types for coloring
    node_types = {}
    for node, data in graph.nodes(data=True):
        node_type = data.get('type', 'unknown')
        if node_type not in node_types:
            node_types[node_type] = []
        node_types[node_type].append(node)
    
    # Draw nodes by type with different colors
    for i, (node_type, nodes) in enumerate(node_types.items()):
        nx.draw_networkx_nodes(
            graph, pos, 
            nodelist=nodes,
            node_color=[cmap(i/max(1, len(node_types)-1))],
            node_size=300,
            alpha=0.8,
            label=node_type
        )
    
    # Draw edges with arrows
    nx.draw_networkx_edges(
        graph, pos,
        width=1.0,
        alpha=0.5,
        arrowsize=15,
        arrowstyle='->'
    )
    
    # Draw labels with smaller font
    nx.draw_networkx_labels(
        graph, pos,
        font_size=8,
        font_family='sans-serif'
    )
    
    plt.title("Terraform Module Dependencies")
    plt.axis('off')
    plt.tight_layout()
    plt.legend()
    
    # Save the figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close()
    
    # Encode the image to base64
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    
    return img_str

def create_plotly_graph(graph):
    """
    Create an interactive Plotly graph of the dependency graph.
    
    Args:
        graph (nx.DiGraph): The dependency graph
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    try:
        import plotly.graph_objects as go
        
        # Use a spring layout for the graph
        pos = nx.spring_layout(graph, seed=42)
        
        # Create edge traces
        edge_x = []
        edge_y = []
        edge_text = []
        
        for edge in graph.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Add edge information
            edge_type = edge[2].get('type', 'unknown')
            module_name = edge[2].get('module_name', '')
            edge_text.append(f"Type: {edge_type}<br>Module: {module_name}")
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='text',
            text=edge_text,
            mode='lines')
        
        # Create node traces
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        
        # Get node types for coloring
        node_types = {}
        for node, data in graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            if node_type not in node_types:
                node_types[node_type] = len(node_types)
        
        for node, data in graph.nodes(data=True):
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Add node information
            node_type = data.get('type', 'unknown')
            node_text.append(f"{node}<br>Type: {node_type}")
            
            # Color by node type
            node_color.append(node_types.get(node_type, 0))
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                color=node_color,
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Node Type',
                    xanchor='left',
                ),
                line_width=2))
        
        # Create the figure with corrected layout properties
        fig = go.Figure(data=[edge_trace, node_trace],
                      layout=go.Layout(
                          title=dict(
                              text='Terraform Module Dependencies',
                              font=dict(size=16)
                          ),
                          showlegend=False,
                          hovermode='closest',
                          margin=dict(b=20,l=5,r=5,t=40),
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                          )
        
        return fig
    except Exception as e:
        st.error(f"Error creating Plotly graph: {str(e)}")
        return None

# Initialize session state variables
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None
if 'repo_analyzed' not in st.session_state:
    st.session_state.repo_analyzed = False
if 'relevant_files' not in st.session_state:
    st.session_state.relevant_files = []
if 'modifications' not in st.session_state:
    st.session_state.modifications = {}

# Title and description
st.title("🔧 Terraform Code Modifier")
st.markdown("""
This app allows you to modify Terraform code based on natural language requests.
First, analyze a Terraform repository to build a dependency graph, then specify your modification request.
""")

# Sidebar for repository configuration
with st.sidebar:
    st.header("Repository Configuration")
    
    # Repository information
    st.subheader("Repository Information")
    repo_url = st.text_input(
        "Repository URL", 
        placeholder="https://github.com/username/repo",
        help="Enter the URL of the GitHub repository containing Terraform code. Use the base repository URL without /tree/ or /blob/ paths."
    )
    
    # Add example URLs
    with st.expander("Example Repository URLs"):
        st.markdown(EXAMPLE_REPOS)
    
    branch = st.text_input("Branch", DEFAULT_BRANCH, help="Branch to analyze")
    
    # Google Cloud credentials
    st.subheader("Google Cloud Credentials")
    credentials_file = st.file_uploader("Upload Google Cloud credentials JSON file", type=["json"])
    
    if credentials_file:
        # Save the credentials to a temporary file
        temp_creds = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_creds.write(credentials_file.getvalue())
        temp_creds.close()
        
        # Set the environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds.name
        st.success("Credentials uploaded successfully!")
    
    # Model configuration
    st.subheader("Model Configuration")
    model_name = st.selectbox(
        "Gemini Model",
        options=["gemini-2.0-flash-001", "gemini-1.5-pro-002"],
        index=0,
        help="Select the Gemini model to use for code modification"
    )
    
    # Analyze button
    analyze_button = st.button("Analyze Repository", help="Clone and analyze the repository")

# Handle repository analysis
if analyze_button and repo_url:
    with st.spinner("Analyzing repository..."):
        try:
            # Clean the repository URL
            cleaned_repo_url = clean_github_url(repo_url)
            if cleaned_repo_url != repo_url:
                st.info(f"Cleaned repository URL: {cleaned_repo_url}")
                repo_url = cleaned_repo_url
            
            # Create a temporary directory for the repository
            temp_dir = tempfile.mkdtemp()
            
            # Initialize and run the analyzer
            analyzer = TerraformRepoAnalyzer(repo_url, branch, temp_dir)
            
            # Try to clone the repository
            try:
                analyzer.clone_repository()
            except Exception as clone_error:
                st.error(f"Error cloning repository: {str(clone_error)}")
                
                # Suggest alternative URLs
                if 'github.com' in repo_url:
                    base_url = repo_url.split('github.com/')[-1]
                    suggestions = [
                        f"https://github.com/{base_url}",
                        f"https://github.com/{base_url.split('/')[0]}/{base_url.split('/')[1]}"
                    ]
                    
                    st.warning("The repository URL might be incorrect. Try one of these instead:")
                    for suggestion in suggestions:
                        if suggestion != repo_url:
                            st.code(suggestion)
                
                st.stop()
            
            # Check if any files were found
            tf_files = analyzer.find_terraform_files()
            if len(tf_files) == 0:
                st.error(f"No Terraform files found in the repository. Please check the URL and branch.")
                st.session_state.repo_analyzed = False
                
                # Allow manual file upload as a fallback
                st.subheader("Manual Terraform File Upload")
                st.write("If your repository structure is unusual, you can upload Terraform files directly:")
                
                uploaded_files = st.file_uploader("Upload Terraform Files", accept_multiple_files=True, type=["tf", "json"])
                
                if uploaded_files:
                    # Create a directory for the uploaded files
                    upload_dir = os.path.join(temp_dir, "uploaded_files")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save the uploaded files
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(upload_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    
                    st.success(f"Uploaded {len(uploaded_files)} files. Analyzing...")
                    
                    # Re-run the analysis with the uploaded files
                    analyzer = TerraformRepoAnalyzer("manual_upload", "main", upload_dir)
                    analyzer.build_dependency_graph()
                    
                    if analyzer.dependency_graph.number_of_nodes() > 0:
                        st.session_state.analyzer = analyzer
                        st.session_state.repo_analyzed = True
                        st.success(f"Analysis successful! Found {analyzer.dependency_graph.number_of_nodes()} files in the dependency graph.")
                    else:
                        st.error("Could not build dependency graph from uploaded files.")
                        st.session_state.repo_analyzed = False
                
                st.stop()
            
            analyzer.build_dependency_graph()
            
            # Verify the graph has nodes
            if analyzer.dependency_graph.number_of_nodes() == 0:
                st.error("No files were added to the dependency graph. Please check if the repository contains valid Terraform files.")
                st.session_state.repo_analyzed = False
                st.stop()
            
            # Store the analyzer in session state
            st.session_state.analyzer = analyzer
            st.session_state.repo_analyzed = True
            
            st.success(f"Repository analyzed successfully! Found {analyzer.dependency_graph.number_of_nodes()} files.")
        except Exception as e:
            st.error(f"Error analyzing repository: {str(e)}")
            st.session_state.repo_analyzed = False

# Main content area - only show if repository is analyzed
if st.session_state.repo_analyzed:
    # Display repository information
    st.header("Repository Analysis")
    
    # Show basic stats about the repository
    analyzer = st.session_state.analyzer
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Files", analyzer.dependency_graph.number_of_nodes())
    with col2:
        st.metric("Dependencies", analyzer.dependency_graph.number_of_edges())
    
    # Add tabs for different views
    repo_tabs = st.tabs(["Files", "Dependencies", "Visualization"])
    
    # Files tab
    with repo_tabs[0]:
        files = sorted([n for n in analyzer.dependency_graph.nodes()])
        if files:
            st.subheader(f"Repository Files ({len(files)})")
            for file in files[:20]:  # Show first 20 files
                description = analyzer.dependency_graph.nodes[file].get('description', "No description available")
                with st.expander(file):
                    st.write(f"**Description:** {description}")
                    st.code(read_file_content(analyzer, file), language="hcl")
            if len(files) > 20:
                st.write(f"... and {len(files) - 20} more files")
        else:
            st.warning("No files found in the repository.")
    
    # Dependencies tab
    with repo_tabs[1]:
        dependencies = list(analyzer.dependency_graph.edges(data=True))
        if dependencies:
            st.subheader(f"Module Dependencies ({len(dependencies)})")
            
            # Create a table of dependencies
            dependency_data = []
            for source, target, data in dependencies:
                dependency_data.append({
                    "Source": source,
                    "Target": target,
                    "Type": data.get('type', 'unknown'),
                    "Module Name": data.get('module_name', '')
                })
            
            # Display as a dataframe
            st.dataframe(dependency_data)
        else:
            st.warning("No dependencies found in the repository.")
    
    # Visualization tab
    with repo_tabs[2]:
        if analyzer.dependency_graph.number_of_nodes() > 0:
            st.subheader("Dependency Graph Visualization")
            
            # Choose visualization type
            viz_type = st.radio(
                "Visualization Type",
                options=["Static Image", "Interactive (Plotly)"],
                horizontal=True
            )
            
            if viz_type == "Static Image":
                # Generate and display the static image
                img_str = visualize_dependency_graph(analyzer.dependency_graph)
                st.image(f"data:image/png;base64,{img_str}", use_column_width=True)
            else:
                # Try to generate the interactive graph
                fig = create_plotly_graph(analyzer.dependency_graph)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Fall back to static image
                    img_str = visualize_dependency_graph(analyzer.dependency_graph)
                    st.image(f"data:image/png;base64,{img_str}", use_column_width=True)
        else:
            st.warning("No nodes in the dependency graph to visualize.")
    
    # Modification request
    st.header("Modification Request")
    
    modification_request = st.text_area("Enter your modification request in natural language",
                                       placeholder="Example: Add a new S3 bucket with versioning enabled",
                                       height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        identify_button = st.button("Identify Relevant Files", 
                                   help="Identify files that need to be modified based on your request.")
    with col2:
        modify_button = st.button("Generate Modifications", 
                                 help="Generate code modifications based on your request.")
    
    # Identify relevant files
    if identify_button and modification_request:
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            st.error("Please upload your Google Cloud credentials first.")
        else:
            with st.spinner("Identifying relevant files..."):
                try:
                    # Initialize the modifier
                    modifier = TerraformCodeModifier(analyzer, model_name=model_name)
                    
                    # Identify relevant files
                    relevant_files = modifier.identify_relevant_files(modification_request)
                    
                    # Store the relevant files in session state
                    st.session_state.relevant_files = relevant_files
                    
                    if relevant_files:
                        st.success(f"Identified {len(relevant_files)} relevant files.")
                    else:
                        st.warning("No relevant files identified.")
                except Exception as e:
                    st.error(f"Error identifying relevant files: {str(e)}")
    
    # Display relevant files
    if st.session_state.relevant_files:
        st.subheader("Relevant Files")
        
        for file_path in st.session_state.relevant_files:
            with st.expander(file_path):
                content = read_file_content(analyzer, file_path)
                st.code(content, language="hcl")
    
    # Generate modifications
    if modify_button and modification_request and st.session_state.relevant_files:
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            st.error("Please upload your Google Cloud credentials first.")
        else:
            with st.spinner("Generating modifications..."):
                try:
                    # Initialize the modifier
                    modifier = TerraformCodeModifier(analyzer, model_name=model_name)
                    
                    # Generate modifications
                    modifications = modifier.modify_files(modification_request, st.session_state.relevant_files)
                    
                    # Store the modifications in session state
                    st.session_state.modifications = modifications
                    
                    if modifications:
                        st.success(f"Generated modifications for {len(modifications)} files.")
                    else:
                        st.warning("No modifications generated.")
                except Exception as e:
                    st.error(f"Error generating modifications: {str(e)}")
    
    # Display modifications
    if st.session_state.modifications:
        st.header("Generated Modifications")
        
        # Create tabs for each modified file
        tabs = st.tabs([f"{file_path}" for file_path in st.session_state.modifications.keys()])
        
        for i, (file_path, content) in enumerate(st.session_state.modifications.items()):
            with tabs[i]:
                st.code(content, language="hcl")
        
        # Apply modifications button
        apply_button = st.button("Apply Modifications", 
                               help="Write the modifications to the files in the repository.")
        
        if apply_button:
            with st.spinner("Applying modifications..."):
                try:
                    # Initialize the modifier
                    modifier = TerraformCodeModifier(analyzer, model_name=model_name)
                    
                    # Apply modifications
                    modified_files = modifier.apply_modifications(st.session_state.modifications)
                    
                    if modified_files:
                        st.success(f"Applied modifications to {len(modified_files)} files.")
                    else:
                        st.warning("No files were modified.")
                except Exception as e:
                    st.error(f"Error applying modifications: {str(e)}")
else:
    # Display instructions when no repository is analyzed
    st.info("👈 Please enter repository information and click 'Analyze Repository' to get started.") 