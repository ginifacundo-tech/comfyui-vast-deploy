import os
import subprocess
import sys
from pathlib import Path

# Cleaned up trailing spaces from paths to prevent directory errors
COMFYUI_DIR = "/workspace/ComfyUI"
CM_CLI = os.path.join(COMFYUI_DIR, "custom_nodes", "ComfyUI-Manager", "cm-cli.py")
WORKFLOW_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows")
CUSTOM_NODES_DIR = os.path.join(COMFYUI_DIR, "custom_nodes")
PYTHON_BIN = "/workspace/comfy_venv/bin/python"

# Repositories that ComfyUI Manager sometimes fails to install automatically
EXTRA_NODES = [
    "https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo.git",
    "https://github.com/xmarre/Comfyui_Minimax_h3_latent_Upscaler-Plus.git"
]

def install_extra_nodes():
    print("\n🔧 Checking and installing specific hardcoded nodes...")
    for repo_url in EXTRA_NODES:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        target_dir = os.path.join(CUSTOM_NODES_DIR, repo_name)
        
        if not os.path.exists(target_dir):
            print(f"📦 Cloning {repo_name}...")
            res = subprocess.run(["git", "clone", repo_url, target_dir], cwd=CUSTOM_NODES_DIR, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"✅ Successfully cloned {repo_name}")
                # Install requirements.txt if it exists
                req_file = os.path.join(target_dir, "requirements.txt")
                if os.path.exists(req_file):
                    print(f"📦 Installing requirements for {repo_name}...")
                    subprocess.run([PYTHON_BIN, "-m", "pip", "install", "-r", req_file])
            else:
                print(f"❌ Failed to clone {repo_name}: {res.stderr}")
        else:
            print(f"✅ {repo_name} already exists, skipping clone.")

def scan_and_install(workflow_path):
    workflow_name = os.path.basename(workflow_path)
    print(f"\n🔍 Scanning '{workflow_name}' for missing nodes...")
    deps_file = f"/tmp/{workflow_name}_deps.json"
    
    cmd_deps = [PYTHON_BIN, CM_CLI, "deps-in-workflow", "--workflow", workflow_path, "--output", deps_file]
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
            print(f"⚠️ Failed to extract dependencies from {workflow_name}. (It might not be a valid ComfyUI workflow)")
            return
            
        print(f"\n📦 Installing missing nodes for {workflow_name}...")
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
            print(f"⚠️ CLI exited with code {process.returncode} for '{workflow_name}'.")
            
    except Exception as e:
        print(f"❌ Error running cm-cli.py for {workflow_name}: {e}")

if __name__ == "__main__":
    if not os.path.exists(CM_CLI):
        print("❌ ComfyUI-Manager not found! Install ComfyUI and ComfyUI-Manager first.")
        sys.exit(1)
        
    # 1. Install specific nodes that Manager might miss
    install_extra_nodes()

    if not os.path.exists(WORKFLOW_DIR):
        print(f"⚠️ Workflow directory not found: {WORKFLOW_DIR}")
        sys.exit(0)
        
    # Dynamically find ALL .json files in the local workflows directory
    workflow_files = list(Path(WORKFLOW_DIR).glob("*.json"))
    
    if not workflow_files:
        print("⚠️ No .json workflow files found in the local workflows directory. Skipping node scan.")
    else:
        print(f"🚀 Found {len(workflow_files)} local workflow(s) to scan.")
        for wf_path in workflow_files:
            scan_and_install(str(wf_path))
            
    print("\n🎉 Missing nodes scan and installation complete for all local workflows!")
