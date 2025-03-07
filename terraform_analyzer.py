#!/usr/bin/env python3
"""
Terraform Repository Analyzer

This script clones a Terraform repository and analyzes its structure,
building a dependency graph of Terraform files and modules.
"""

import os
import subprocess
import glob
import re
import networkx as nx
import json
from pathlib import Path
import hcl2  # For parsing Terraform HCL files
import argparse
from git import Repo  # Using GitPython for more robust git operations

class TerraformRepoAnalyzer:
    def __init__(self, repo_url, branch="master", local_dir="./terraform_repo"):
        """
        Initialize the analyzer with repository details.
        
        Args:
            repo_url (str): GitHub repository URL
            branch (str): Branch to clone
            local_dir (str): Local directory to clone the repository into
        """
        # Clean the repository URL
        self.repo_url = self._clean_github_url(repo_url)
        self.branch = branch
        self.local_dir = local_dir
        self.dependency_graph = nx.DiGraph()
        
    def _clean_github_url(self, url):
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
    
    def clone_repository(self):
        """Clone the GitHub repository to the local directory."""
        try:
            if os.path.exists(self.local_dir):
                print(f"Directory {self.local_dir} already exists.")
                
                # Check if it's actually a git repository
                if not os.path.exists(os.path.join(self.local_dir, '.git')):
                    print("Directory exists but is not a git repository. Removing and cloning again.")
                    import shutil
                    shutil.rmtree(self.local_dir)
                    Repo.clone_from(self.repo_url, self.local_dir, branch=self.branch)
                    print("Repository cloned successfully.")
                else:
                    # Update the repository instead of skipping
                    print("Updating existing repository...")
                    repo = Repo(self.local_dir)
                    origin = repo.remotes.origin
                    origin.fetch()
                    origin.pull()
                    print("Repository updated successfully.")
            else:
                print(f"Cloning repository {self.repo_url} to {self.local_dir}...")
                Repo.clone_from(self.repo_url, self.local_dir, branch=self.branch)
                print("Repository cloned successfully.")
                
            # Verify that files were actually cloned
            files = os.listdir(self.local_dir)
            print(f"Files in repository directory: {len(files)}")
            if len(files) <= 1:  # Only .git directory or empty
                raise Exception("Repository appears to be empty after cloning")
            
        except Exception as e:
            print(f"Error with repository: {e}")
            raise
    
    def find_terraform_files(self):
        """Find all Terraform files in the repository."""
        # Look for .tf files
        tf_files = glob.glob(f"{self.local_dir}/**/*.tf", recursive=True)
        
        # Also look for .tf.json files
        tf_json_files = glob.glob(f"{self.local_dir}/**/*.tf.json", recursive=True)
        
        all_files = tf_files + tf_json_files
        
        # Print some debug information
        print(f"Repository directory: {self.local_dir}")
        print(f"Directory exists: {os.path.exists(self.local_dir)}")
        print(f"Files in directory: {len(os.listdir(self.local_dir)) if os.path.exists(self.local_dir) else 0}")
        print(f"Found {len(all_files)} Terraform files.")
        
        if len(all_files) == 0:
            # Try listing all files to see what's there
            all_repo_files = []
            for root, dirs, files in os.walk(self.local_dir):
                for file in files:
                    all_repo_files.append(os.path.join(root, file))
            
            print(f"Total files in repository: {len(all_repo_files)}")
            print("Sample of files found:")
            for file in all_repo_files[:10]:  # Show first 10 files
                print(f"- {file}")
        
        return all_files
    
    def parse_terraform_file(self, file_path):
        """
        Parse a Terraform file and extract its content.
        
        Args:
            file_path (str): Path to the Terraform file
            
        Returns:
            dict: Parsed Terraform content
        """
        try:
            with open(file_path, 'r') as file:
                print(f"Parsing file: {file_path}")
                # Parse HCL content
                parsed_content = hcl2.load(file)
                return parsed_content
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
    
    def extract_module_dependencies(self, file_path, parsed_content):
        """
        Extract module dependencies from a Terraform file.
        
        Args:
            file_path (str): Path to the Terraform file
            parsed_content (dict): Parsed Terraform content
            
        Returns:
            list: List of module dependencies
        """
        dependencies = []
        
        # Extract module sources
        if 'module' in parsed_content:
            module_content = parsed_content['module']
            print(f"Found modules in {file_path}")
            
            # Handle both dictionary and list formats
            if isinstance(module_content, dict):
                # Standard format: module is a dictionary
                for module_name, module_config in module_content.items():
                    if 'source' in module_config:
                        source = module_config['source']
                        print(f"  Module {module_name} source: {source}")
                        dependencies.append({
                            'type': 'module',
                            'name': module_name,
                            'source': source
                        })
            elif isinstance(module_content, list):
                # Alternative format: module is a list of dictionaries
                for module_item in module_content:
                    for module_name, module_config in module_item.items():
                        if 'source' in module_config:
                            source = module_config['source']
                            print(f"  Module {module_name} source: {source}")
                            dependencies.append({
                                'type': 'module',
                                'name': module_name,
                                'source': source
                            })
        else:
            print(f"No modules found in {file_path}")
        
        return dependencies
    
    def resolve_module_path(self, source, parent_file):
        """
        Resolve the absolute path of a module based on its source.
        """
        parent_dir = os.path.dirname(parent_file)
        
        # Handle local paths (including bare "../" or "./")
        if source.startswith('./') or source.startswith('../') or source in ['.', '..']:
            resolved_path = os.path.normpath(os.path.join(parent_dir, source))
            print(f"Resolved module path: {source} -> {resolved_path}")
            return resolved_path
        
        # Handle relative paths without ./ or ../ prefix
        if not source.startswith('/') and not re.match(r'^[a-zA-Z]:', source) and '://' not in source:
            # Try to resolve as a local path first
            local_path = os.path.normpath(os.path.join(parent_dir, source))
            if os.path.exists(local_path):
                print(f"Resolved relative module path: {source} -> {local_path}")
                return local_path
        
        # Handle other sources (GitHub, Terraform Registry, etc.)
        print(f"Non-local module source: {source}")
        return source
    
    def build_dependency_graph(self):
        """Build a dependency graph of Terraform files."""
        # Find all Terraform files
        tf_files = self.find_terraform_files()
        
        # Add files as nodes
        for file_path in tf_files:
            relative_path = os.path.relpath(file_path, self.local_dir)
            self.dependency_graph.add_node(
                relative_path, 
                type='file',
                path=file_path
            )
        
        # Add dependencies as edges
        edge_count = 0
        for file_path in tf_files:
            relative_path = os.path.relpath(file_path, self.local_dir)
            parsed_content = self.parse_terraform_file(file_path)
            
            if not parsed_content:
                print(f"No parsed content for {file_path}")
                continue
                
            dependencies = self.extract_module_dependencies(file_path, parsed_content)
            
            if not dependencies:
                print(f"No dependencies found in {file_path}")
                continue
                
            print(f"Found {len(dependencies)} dependencies in {file_path}")
            
            for dep in dependencies:
                if dep['type'] == 'module':
                    module_path = self.resolve_module_path(dep['source'], file_path)
                    
                    print(f"Checking module path: {module_path}")
                    
                    # Add module as node if it's a local path
                    if os.path.exists(module_path):
                        if os.path.isdir(module_path):
                            # Look for main.tf or similar in the module directory
                            module_files = glob.glob(f"{module_path}/*.tf")
                            
                            print(f"Found module files for {dep['source']}: {len(module_files)} files")
                            
                            if not module_files:
                                print(f"Warning: No .tf files found in module directory: {module_path}")
                                continue
                                
                            for module_file in module_files:
                                module_relative_path = os.path.relpath(module_file, self.local_dir)
                                
                                print(f"Adding edge: {relative_path} -> {module_relative_path}")
                                
                                self.dependency_graph.add_edge(
                                    relative_path, 
                                    module_relative_path,
                                    type='module_dependency',
                                    module_name=dep['name']
                                )
                                edge_count += 1
                        else:
                            print(f"Module path exists but is not a directory: {module_path}")
                    else:
                        print(f"Module path does not exist: {module_path}")
        
        print(f"Built dependency graph with {self.dependency_graph.number_of_nodes()} nodes and {edge_count} edges.")
    
    def export_graph(self, output_file="terraform_graph.json"):
        """
        Export the dependency graph to a JSON file.
        
        Args:
            output_file (str): Path to the output file
        """
        graph_data = {
            "nodes": [],
            "edges": []
        }
        
        for node in self.dependency_graph.nodes():
            node_data = self.dependency_graph.nodes[node]
            graph_data["nodes"].append({
                "id": node,
                "type": node_data.get("type", "unknown"),
                "path": node_data.get("path", "")
            })
        
        for source, target, data in self.dependency_graph.edges(data=True):
            graph_data["edges"].append({
                "source": source,
                "target": target,
                "type": data.get("type", "unknown"),
                "module_name": data.get("module_name", "")
            })
        
        with open(output_file, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        print(f"Dependency graph exported to {output_file}")
    
    def visualize_graph(self, output_file="terraform_graph.png"):
        """
        Visualize the dependency graph and save it as an image.
        
        Args:
            output_file (str): Path to the output image file
        """
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(12, 10))
            pos = nx.spring_layout(self.dependency_graph)
            
            # Draw nodes
            nx.draw_networkx_nodes(self.dependency_graph, pos, node_size=500, alpha=0.8)
            
            # Draw edges
            nx.draw_networkx_edges(self.dependency_graph, pos, width=1.0, alpha=0.5)
            
            # Draw labels
            nx.draw_networkx_labels(self.dependency_graph, pos, font_size=8)
            
            plt.title("Terraform Module Dependencies")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_file, dpi=300)
            print(f"Graph visualization saved to {output_file}")
        except ImportError:
            print("Matplotlib is required for visualization. Install it with 'pip install matplotlib'.")
    
    def analyze_repository(self):
        """Analyze the repository and build the dependency graph."""
        self.clone_repository()
        self.build_dependency_graph()
        self.generate_file_descriptions()
        
    def generate_file_descriptions(self):
        """Generate descriptions for each file using Gemini."""
        try:
            # Import Vertex AI
            import vertexai
            from vertexai.generative_models import GenerativeModel
            from constants import PROJECT_ID, LOCATION, MODEL_NAME
            
            # Initialize Vertex AI
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            model = GenerativeModel(MODEL_NAME)
            
            print("Generating file descriptions...")
            
            # Add descriptions to each node in the graph
            for node in self.dependency_graph.nodes():
                # Skip if description already exists
                if self.dependency_graph.nodes[node].get('description'):
                    continue
                    
                # Read file content
                file_path = os.path.join(self.local_dir, node)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Truncate content if it's too long
                    if len(content) > 10000:
                        content = content[:10000] + "... (truncated)"
                    
                    # Generate description using Gemini
                    prompt = f"""
                    You are a Terraform expert. Please provide a brief description (2-3 sentences) of what this Terraform file does:
                    
                    ```
                    {content}
                    ```
                    
                    Your description should be concise and focus on the main resources, modules, or configurations in the file.
                    """
                    
                    response = model.generate_content(prompt)
                    description = response.text.strip()
                    
                    # Add description to the node
                    self.dependency_graph.nodes[node]['description'] = description
                    print(f"Generated description for {node}")
                    
                except Exception as e:
                    print(f"Error generating description for {node}: {e}")
                    # Add a default description
                    self.dependency_graph.nodes[node]['description'] = "Terraform configuration file"
        
        except Exception as e:
            print(f"Error initializing Gemini for file descriptions: {e}")
            # Add default descriptions if Gemini fails
            for node in self.dependency_graph.nodes():
                if not self.dependency_graph.nodes[node].get('description'):
                    self.dependency_graph.nodes[node]['description'] = "Terraform configuration file"


def main():
    """Main function to run the analyzer from command line."""
    parser = argparse.ArgumentParser(description="Analyze Terraform repositories and build dependency graphs.")
    parser.add_argument("repo_url", help="URL of the GitHub repository to analyze")
    parser.add_argument("--branch", default="master", help="Branch to clone (default: master)")
    parser.add_argument("--output-dir", default="./terraform_analysis", help="Directory to store analysis results")
    parser.add_argument("--visualize", action="store_true", help="Generate a visualization of the dependency graph")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up paths
    local_dir = os.path.join(args.output_dir, "repo")
    graph_file = os.path.join(args.output_dir, "terraform_graph.json")
    viz_file = os.path.join(args.output_dir, "terraform_graph.png")
    
    # Run analysis
    analyzer = TerraformRepoAnalyzer(args.repo_url, args.branch, local_dir)
    graph = analyzer.analyze_repository()
    analyzer.export_graph(graph_file)
    
    if args.visualize:
        analyzer.visualize_graph(viz_file)
    
    # Print summary
    print(f"\nRepository Analysis Summary:")
    print(f"Total Terraform files: {len([n for n, d in graph.nodes(data=True) if d.get('type') == 'file'])}")
    print(f"Total module dependencies: {len([e for e in graph.edges(data=True) if e[2].get('type') == 'module_dependency'])}")
    
    # Find VPC-related files (for the example prompt)
    vpc_files = [n for n in graph.nodes() if 'vpc' in n.lower()]
    print(f"\nVPC-related files ({len(vpc_files)}):")
    for file in vpc_files[:5]:  # Show first 5 for brevity
        print(f"- {file}")
    if len(vpc_files) > 5:
        print(f"  ... and {len(vpc_files) - 5} more")


if __name__ == "__main__":
    main() 