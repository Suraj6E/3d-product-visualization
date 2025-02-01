import os
import ast
import subprocess
from collections import defaultdict

def extract_imports(file_path):
    """Extract import statements from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            tree = ast.parse(file.read())
    except UnicodeDecodeError:
        try:
            # Try with a different encoding if utf-8 fails
            with open(file_path, 'r', encoding='latin-1') as file:
                tree = ast.parse(file.read())
        except Exception as e:
            print(f"Skipping {file_path}: {str(e)}")
            return set()
    except Exception as e:
        print(f"Skipping {file_path}: {str(e)}")
        return set()

    imports = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    
    return imports

def get_installed_packages():
    """Get dictionary of installed packages and their versions using pip list."""
    try:
        # Use pip list instead of pip freeze for more reliable output
        result = subprocess.run(['pip', 'list', '--format=json'], 
                              capture_output=True, text=True, encoding='utf-8')
        
        # Parse the JSON output
        import json
        packages = {}
        pip_list = json.loads(result.stdout)
        for package in pip_list:
            packages[package['name'].lower()] = package['version']
        return packages
    except Exception as e:
        print(f"Error getting installed packages: {str(e)}")
        return {}

def generate_requirements():
    """Generate requirements.txt from Python files in current directory."""
    # Get all imports from .py files
    all_imports = set()
    for root, _, files in os.walk('.'):
        # Skip virtual environment directories and node_modules
        if any(skip_dir in root for skip_dir in ['venv', 'env', 'node_modules', '__pycache__', '.git']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = extract_imports(file_path)
                all_imports.update(imports)

    # Get installed packages and their versions
    installed_packages = get_installed_packages()

    # Write requirements.txt with explicit UTF-8 encoding
    with open('requirements.txt', 'w', encoding='utf-8', newline='\n') as f:
        for package_name in sorted(all_imports):
            package_lower = package_name.lower()
            if package_lower in installed_packages:
                f.write(f'{package_name}=={installed_packages[package_lower]}\n')

if __name__ == '__main__':
    try:
        generate_requirements()
        print("requirements.txt has been generated successfully!")
        
        # Verify the contents
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            print("\nGenerated requirements.txt contents:")
            print(content)
    except Exception as e:
        print(f"An error occurred: {str(e)}")