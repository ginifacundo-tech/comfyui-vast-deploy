import os
import subprocess
import sys
import re
from pathlib import Path

# ==========================================
# 1. FIX: Removed trailing spaces from paths
# ==========================================
COMFYUI_DIR = "/workspace/ComfyUI"
CM_CLI = os.path.join(COMFYUI_DIR, "custom_nodes", "ComfyUI-Manager", "cm-cli.py")
WORKFLOW_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows")
CUSTOM_NODES_DIR = os.path.join(COMFYUI_DIR, "custom_nodes")
PYTHON_BIN = "/workspace/comfy_venv/bin/python"

# ==========================================
# 2. FIX: Add a Logger to save output to a file
# ==========================================
class Logger(object):
    def __init__(self, filename="install_missing_nodes.log"):
        self.terminal = sys.stdout
        # Save log to the workspace folder
        self.log = open(os.path.join("/workspace", filename), "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # Ensure it writes immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def isatty(self):
        return False

# Redirect all print statements to both the console and the log file
sys.stdout = Logger("install_missing_nodes.log")

# Repositories that ComfyUI Manager sometimes fails to install automatically
EXTRA_NODES = [
    "https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo.git",
    "https://github.com/xmarre/Comfyui_Minimax_h3_latent_Upscaler-Plus.git"
]

def preinstall_cuda_dependencies():
    print("\n🔧 Pre-installing build tools and matching CuPy CUDA version...")
    # 1. Upgrade build tools to prevent the 'pkg_resources' error
    subprocess.run([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    
    # 2. Detect CUDA version and install the correct CuPy binary
    try:
        # Try to detect via torch if available
        detect_cmd = [PYTHON_BIN, "-c", "import torch; print(torch.version.cuda or '')"]
        res = subprocess.run(detect_cmd, capture_output=True, text=True)
        cuda_ver = res.stdout.strip()
        
        if not cuda_ver:
            # Fallback to nvidia-smi
            nvidia_res = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            match = re.search(r"CUDA Version:\s+(\d+\.\d+)", nvidia_res.stdout)
            if match:
                cuda_ver = match.group(1)
                
        if cuda_ver:
            print(f"🔍 Detected CUDA Version: {cuda_ver}")
            if cuda_ver.startswith("12"):
                print("📦 Installing cupy-cuda12x...")
                subprocess.run([PYTHON_BIN, "-m", "pip", "install", "cupy-cuda12x"])
            elif cuda_ver.startswith("11"):
                print("📦 Installing cupy-cuda11x...")
                subprocess.run([PYTHON_BIN, "-m", "pip", "install", "cupy-cuda11x"])
            else:
                print(f"⚠️ Unrecognized CUDA version ({cuda_ver}). Letting pip handle cupy.")
        else:
            print("⚠️ Could not detect CUDA version. Ensure PyTorch is installed with CUDA support.")
    except Exception as e:
        print(f"❌ Error detecting CUDA version: {e}")

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
    print("🚀 Starting ComfyUI Missing Nodes Installer...")
    
    # Run the CuPy / CUDA fix first!
    preinstall_cuda_dependencies()

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
