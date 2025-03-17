#!/usr/bin/env python3
"""
Terraform Code Modifier

This script uses the dependency graph from TerraformRepoAnalyzer to identify
relevant files for a code modification request and then uses Gemini via Vertex AI
to generate the necessary code changes.
"""

import os
import re
import json
import argparse
from pathlib import Path
from terraform_analyzer import TerraformRepoAnalyzer

# Import constants
from constants import (
    PROJECT_ID, LOCATION, API_ENDPOINT, MODEL_NAME, 
    GENERATION_CONFIG, DEFAULT_OUTPUT_DIR, DEFAULT_BRANCH
)

class TerraformCodeModifier:
    def __init__(self, analyzer, credentials_path=None, model_name=MODEL_NAME):
        """
        Initialize the code modifier.
        
        Args:
            analyzer (TerraformRepoAnalyzer): An initialized TerraformRepoAnalyzer instance
            credentials_path (str, optional): Path to Google Cloud credentials JSON file
            model_name (str, optional): Name of the Gemini model to use
        """
        self.analyzer = analyzer
        
        # Set credentials path if provided
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        # Import Vertex AI
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            self.vertexai = vertexai
            self.GenerativeModel = GenerativeModel
        except ImportError:
            raise ImportError("Vertex AI SDK is required. Install with 'pip install google-cloud-aiplatform'")
        
        # Initialize Vertex AI
        self.project_id = PROJECT_ID
        self.location = LOCATION
        self.model_name = model_name
        self.generation_config = GENERATION_CONFIG
        
        self.vertexai.init(project=self.project_id, location=self.location)
    
    def prepare_graph_data_for_prompt(self):
        """
        Prepare a simplified version of the dependency graph for inclusion in prompts.
        
        Returns:
            str: A text representation of the graph
        """
        graph = self.analyzer.dependency_graph
        
        # Get all nodes and edges
        nodes = list(graph.nodes(data=True))
        edges = list(graph.edges(data=True))
        
        # Format nodes
        node_text = "Files:\n"
        for node, data in nodes:
            node_text += f"- {node}\n"
        
        # Format edges
        edge_text = "\nDependencies:\n"
        for source, target, data in edges:
            module_name = data.get('module_name', '')
            edge_text += f"- {source} -> {target} (module: {module_name})\n"
        
        return node_text + edge_text
    
    def identify_relevant_files(self, modification_request):
        """
        Identify files that are likely relevant to a code modification request.
        
        Args:
            modification_request (str): Natural language description of the requested change
            
        Returns:
            list: List of file paths that are likely relevant to the request
        """
        try:
            # Initialize Vertex AI model
            model = self.GenerativeModel(self.model_name)
            
            # Prepare information about all files in the repository
            file_info = []
            for node in self.analyzer.dependency_graph.nodes():
                # Get node data
                node_data = self.analyzer.dependency_graph.nodes[node]
                
                # Get description (use a default if not available)
                description = node_data.get('description', "Terraform configuration file")
                
                # Get dependencies
                dependencies = []
                for _, target, data in self.analyzer.dependency_graph.out_edges(node, data=True):
                    dep_type = data.get('type', 'unknown')
                    module_name = data.get('module_name', '')
                    dependencies.append(f"{target} ({dep_type}{': ' + module_name if module_name else ''})")
                
                # Add to file info
                file_info.append({
                    "file": node,
                    "description": description,
                    "dependencies": dependencies
                })
            
            # Create a prompt for the model
            prompt = f"""
            You are a Terraform expert. I need to identify which files in a Terraform repository need to be modified to implement the following change:
            
            MODIFICATION REQUEST: {modification_request}
            
            Here are the files in the repository, with descriptions and dependencies:
            
            """
            
            # Add file information to the prompt
            for info in file_info:
                prompt += f"\nFILE: {info['file']}\n"
                prompt += f"DESCRIPTION: {info['description']}\n"
                if info['dependencies']:
                    prompt += f"DEPENDENCIES: {', '.join(info['dependencies'])}\n"
            
            prompt += """
            Please identify the files that need to be modified to implement the requested change.
            Return your answer as a JSON array of file paths, like this:
            ["path/to/file1.tf", "path/to/file2.tf"]
            
            Only include files that need to be modified, not files that are just referenced.
            """
            
            # Generate response
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON array from response
            import json
            import re
            
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                file_paths = json.loads(json_str)
            else:
                # Fallback: try to extract file paths using regex
                file_paths = re.findall(r'"([^"]+\.tf)"', response_text)
            
            # Validate file paths
            valid_file_paths = []
            for file_path in file_paths:
                # Remove any leading slashes
                file_path = file_path.lstrip('/')
                
                # Check if the file exists
                full_path = os.path.join(self.analyzer.local_dir, file_path)
                if os.path.exists(full_path):
                    valid_file_paths.append(file_path)
                else:
                    # Try to find the file by searching the repository
                    found = False
                    for root, dirs, files in os.walk(self.analyzer.local_dir):
                        if os.path.basename(file_path) in files:
                            # Use the relative path from the repository root
                            rel_path = os.path.relpath(
                                os.path.join(root, os.path.basename(file_path)), 
                                self.analyzer.local_dir
                            )
                            valid_file_paths.append(rel_path)
                            found = True
                            break
                    
                    if not found:
                        print(f"Warning: File not found: {file_path}")
            
            print(f"Identified {len(valid_file_paths)} valid files:")
            for file in valid_file_paths:
                print(f"- {file}")
            
            return valid_file_paths
            
        except Exception as e:
            print(f"Error identifying relevant files: {str(e)}")
            # Fallback: return all .tf files in the repository
            return [node for node in self.analyzer.dependency_graph.nodes()]
    
    def read_file_content(self, file_path):
        """
        Read the content of a file.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Content of the file
        """
        full_path = os.path.join(self.analyzer.local_dir, file_path)
        try:
            with open(full_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {full_path}: {e}")
            return ""
    
    def modify_files(self, modification_request, file_paths):
        """
        Generate code modifications for the specified files based on the request.
        
        Args:
            modification_request (str): Natural language description of the requested change
            file_paths (list): List of file paths to modify
            
        Returns:
            dict: Dictionary mapping file paths to modified content
        """
        modifications = {}
        
        try:
            # Initialize Vertex AI model
            model = self.GenerativeModel(self.model_name)
            
            # Process each file
            for file_path in file_paths:
                print(f"Generating modifications for {file_path}...")
                
                # Read the original file content
                full_path = os.path.join(self.analyzer.local_dir, file_path)
                with open(full_path, 'r') as f:
                    original_content = f.read()
                
                # Get file description
                description = "Terraform configuration file"
                if file_path in self.analyzer.dependency_graph.nodes():
                    description = self.analyzer.dependency_graph.nodes[file_path].get('description', description)
                
                # Get dependencies
                dependencies = []
                if file_path in self.analyzer.dependency_graph.nodes():
                    for _, target, data in self.analyzer.dependency_graph.out_edges(file_path, data=True):
                        dep_type = data.get('type', 'unknown')
                        module_name = data.get('module_name', '')
                        dependencies.append(f"{target} ({dep_type}{': ' + module_name if module_name else ''})")
                
                # Create a prompt for the model
                prompt = f"""
                You are a Terraform expert. I need to modify a Terraform file to implement the following change:
                
                MODIFICATION REQUEST: {modification_request}
                
                FILE: {file_path}
                DESCRIPTION: {description}
                """
                
                if dependencies:
                    prompt += f"DEPENDENCIES: {', '.join(dependencies)}\n"
                
                prompt += f"""
                Here is the current content of the file:
                
                ```terraform
                {original_content}
                ```
                
                Please provide the modified version of the file that implements the requested change.
                Return ONLY the complete modified file content, with no additional explanations.
                """
                
                # Generate response
                response = model.generate_content(prompt)
                modified_content = response.text
                
                # Extract code block if present
                import re
                code_match = re.search(r'```(?:terraform|hcl)?\s*([\s\S]*?)\s*```', modified_content)
                if code_match:
                    modified_content = code_match.group(1)
                
                # Add to modifications
                modifications[file_path] = modified_content
        
        except Exception as e:
            print(f"Error generating modifications: {str(e)}")
        
        return modifications
    
    def apply_modifications(self, modifications, dry_run=False):
        """
        Apply the modifications to the files.
        
        Args:
            modifications (dict): Dictionary mapping file paths to their modified content
            dry_run (bool): If True, don't actually write the files
            
        Returns:
            list: List of modified file paths
        """
        modified_files = []
        
        for file_path, content in modifications.items():
            full_path = os.path.join(self.analyzer.local_dir, file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if dry_run:
                print(f"Would write to {full_path}:")
                print("---")
                print(content)
                print("---")
            else:
                try:
                    with open(full_path, 'w') as f:
                        f.write(content)
                    print(f"Updated {file_path}")
                    modified_files.append(file_path)
                except Exception as e:
                    print(f"Error writing to {full_path}: {e}")
        
        return modified_files

    def generate_file_summary(self, file_path, content=None):
        """
        Generate a summary of a Terraform file using Gemini.
        
        Args:
            file_path (str): Path to the file
            content (str, optional): File content if already read
            
        Returns:
            str: Summary of the file
        """
        try:
            # Initialize Vertex AI model
            model = self.GenerativeModel(self.model_name)
            
            # Read the file content if not provided
            if content is None:
                full_path = os.path.join(self.analyzer.local_dir, file_path)
                with open(full_path, 'r') as f:
                    content = f.read()
            
            # Truncate content if it's too long
            if len(content) > 10000:
                content = content[:10000] + "... (truncated)"
            
            # Create a prompt for the model
            prompt = f"""
            You are a Terraform expert. Please provide a detailed summary of what this Terraform file does.
            Focus on the resources, modules, variables, and outputs defined in the file.
            
            File: {file_path}
            
            ```terraform
            {content}
            ```
            
            Your summary should be comprehensive but concise (3-5 sentences).
            """
            
            # Generate response
            response = model.generate_content(prompt)
            summary = response.text.strip()
            
            return summary
        except Exception as e:
            print(f"Error generating summary for {file_path}: {str(e)}")
            return f"Terraform file: {file_path}"


def main():
    """Main function to run the modifier from command line."""
    parser = argparse.ArgumentParser(description="Modify Terraform code based on natural language requests.")
    parser.add_argument("repo_url", help="URL of the GitHub repository to analyze")
    parser.add_argument("request", help="Natural language description of the requested change")
    parser.add_argument("--branch", default="master", help="Branch to clone (default: master)")
    parser.add_argument("--output-dir", default="./terraform_analysis", help="Directory to store analysis results")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write the files")
    parser.add_argument("--credentials", help="Path to Google Cloud credentials JSON file")
    parser.add_argument("--model", default=MODEL_NAME, help=f"Gemini model name (default: {MODEL_NAME})")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up paths
    local_dir = os.path.join(args.output_dir, "repo")
    
    # Run analysis first
    print("Step 1: Analyzing repository...")
    analyzer = TerraformRepoAnalyzer(args.repo_url, args.branch, local_dir)
    analyzer.analyze_repository()
    
    # Initialize modifier
    print("\nStep 2: Processing modification request...")
    modifier = TerraformCodeModifier(analyzer, credentials_path=args.credentials, model_name=args.model)
    
    # Identify relevant files
    print("\nIdentifying relevant files...")
    relevant_files = modifier.identify_relevant_files(args.request)
    
    if not relevant_files:
        print("No relevant files identified. Cannot proceed with modification.")
        return
    
    # Generate modifications
    print("\nGenerating modifications...")
    modifications = modifier.modify_files(args.request, relevant_files)
    
    if not modifications:
        print("No modifications generated. No files will be changed.")
        return
    
    # Apply modifications
    print("\nApplying modifications...")
    modified_files = modifier.apply_modifications(modifications, dry_run=args.dry_run)
    
    # Print summary
    if args.dry_run:
        print(f"\nDry run completed. {len(modified_files)} files would be modified.")
    else:
        print(f"\nModification completed. {len(modified_files)} files were modified.")


if __name__ == "__main__":
    main() 