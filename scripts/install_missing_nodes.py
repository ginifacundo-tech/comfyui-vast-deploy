import os
import subprocess
import sys

COMFYUI_DIR = "/workspace/ComfyUI"
CM_CLI = os.path.join(COMFYUI_DIR, "custom_nodes", "ComfyUI-Manager", "cm-cli.py")
WORKFLOW_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows")
PYTHON_BIN = "/workspace/comfy_venv/bin/python"

# List the workflows you want to scan for missing nodes
WORKFLOWS_TO_SCAN = [
    "workflow_academia.json",
    # Add any other workflow filenames here if you download more
]

def scan_and_install(workflow_name):
    workflow_path = os.path.join(WORKFLOW_DIR, workflow_name)
    if not os.path.exists(workflow_path):
        print(f"⚠️ Workflow '{workflow_name}' not found at {workflow_path}. Skipping.")
        return

    print(f"\n🔍 Scanning '{workflow_name}' for missing nodes...")
    
    # Step 1: Generate a dependencies JSON file from the workflow
    deps_file = f"/tmp/{workflow_name}_deps.json"
    cmd_deps = [
        PYTHON_BIN, CM_CLI, "deps-in-workflow", 
        "--workflow", workflow_path, 
        "--output", deps_file
    ]
    
    try:
        print("⏳ Extracting node dependencies from workflow...")
        process = subprocess.Popen(
            cmd_deps, 
            cwd=COMFYUI_DIR, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1
        )
        for line in process.stdout:
            print(line, end="")
        process.wait()
        
        if process.returncode != 0 or not os.path.exists(deps_file):
            print(f"⚠️ Failed to extract dependencies from workflow. (Exit code: {process.returncode})")
            return
            
        # Step 2: Install the extracted dependencies
        print(f"\n📦 Installing missing nodes from {deps_file}...")
        cmd_install = [PYTHON_BIN, CM_CLI, "install-deps", deps_file]
        process = subprocess.Popen(
            cmd_install, 
            cwd=COMFYUI_DIR, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1
        )
        for line in process.stdout:
            print(line, end="")
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ Successfully installed missing nodes for '{workflow_name}'!")
        else:
            print(f"⚠️ CLI exited with code {process.returncode}. Some nodes might need manual installation in the GUI.")
    except Exception as e:
        print(f"❌ Error running cm-cli.py: {e}")

if __name__ == "__main__":
    if not os.path.exists(CM_CLI):
        print(f"❌ ComfyUI-Manager cm-cli.py not found at {CM_CLI}!")
        print("   Please ensure ComfyUI and ComfyUI-Manager are installed first.")
        sys.exit(1)
        
    for wf in WORKFLOWS_TO_SCAN:
        scan_and_install(wf)
        
    print("\n🎉 Missing nodes scan and installation complete!")
