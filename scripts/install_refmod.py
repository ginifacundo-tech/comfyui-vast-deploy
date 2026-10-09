import os
import subprocess
import sys
import urllib.request
import json
import re

COMFYUI_DIR = "/workspace/ComfyUI"
CUSTOM_NODES_DIR = os.path.join(COMFYUI_DIR, "custom_nodes")
REFMOD_DIR = os.path.join(CUSTOM_NODES_DIR, "ComfyUI-MiniMaxH3Mod")
# Placed inside the default workflows dir so ComfyUI natively lists them in the UI
WORKFLOW_DEST_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows", "refmod")
PYTHON_BIN = "/workspace/comfy_venv/bin/python"
PIP_BIN = "/workspace/comfy_venv/bin/pip"

# Read the repo URL from the environment (set by master.sh)
REPO_RAW_BASE = os.environ.get("REPO_RAW_BASE", "https://raw.githubusercontent.com/ginifacundo-tech/comfyui-vast-deploy/main")

def run_cmd(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    for line in process.stdout:
        print(line, end="")
        sys.stdout.flush()
    process.wait()
    return process.returncode

def main():
    print("🚀 Starting ComfyUI-MiniMaxH3Mod (RefMod) installation...")
    
    # 1. Clone or update the repository
    if not os.path.exists(REFMOD_DIR):
        print("⬇️ Cloning ComfyUI-MiniMaxH3Mod...")
        clone_cmd = ["git", "clone", "https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod.git", REFMOD_DIR]
        if run_cmd(clone_cmd) != 0:
            print("❌ Failed to clone repository.")
            sys.exit(1)
    else:
        print("✅ ComfyUI-MiniMaxH3Mod already exists. Updating...")
        run_cmd(["git", "pull"], cwd=REFMOD_DIR)

    # 2. Install requirements
    req_file = os.path.join(REFMOD_DIR, "requirements.txt")
    if os.path.exists(req_file):
        print("📦 Installing RefMod requirements...")
        run_cmd([PIP_BIN, "install", "-r", req_file])
    else:
        print("⚠️ No requirements.txt found in RefMod.")

    # 3. Download RefMod workflows from the user's GitHub repo
    print("📂 Downloading RefMod workflows from GitHub repo...")
    os.makedirs(WORKFLOW_DEST_DIR, exist_ok=True)
    
    # Extract repo path from REPO_RAW_BASE to use GitHub API
    match = re.search(r'githubusercontent\.com/([^/]+/[^/]+)/', REPO_RAW_BASE)
    if match:
        repo_path = match.group(1)
        api_url = f'https://api.github.com/repos/{repo_path}/contents/refmod/workflows'
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'ComfyUI-Deploy'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                files = [item['name'] for item in data if item['name'].endswith('.json') and item['type'] == 'file']
                
                if not files:
                    print("⚠️ No .json workflows found in refmod/workflows/ directory.")
                else:
                    for f in files:
                        print(f'⬇️ Downloading workflow: {f}')
                        url = f'{REPO_RAW_BASE}/refmod/workflows/{f}'
                        urllib.request.urlretrieve(url, os.path.join(WORKFLOW_DEST_DIR, f))
                    print("✅ All RefMod workflows downloaded successfully!")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("⚠️ refmod/workflows/ directory not found in the repository.")
            else:
                print(f"⚠️ Failed to fetch workflows: {e}")
        except Exception as e:
            print(f"⚠️ Failed to fetch workflows: {e}")
    else:
        print("⚠️ Could not parse repo info from REPO_RAW_BASE. Skipping workflow download.")

    print("\n🎉 RefMod installation complete!")

if __name__ == "__main__":
    main()
