import sys
import json
import subprocess
from pathlib import Path
import urllib.request
import time

COMFYUI_DIR = "/workspace/ComfyUI"
PYTHON = sys.executable

CUSTOM_NODES = [
    "https://github.com/MoonGoblinDev/Civicomfy"
]

WORKFLOWS = [
    {
        "url": "https://raw.githubusercontent.com/AcademiaSD/comfyui_AcademiaSD/main/example_workflows/AcademiaSD_MiniMax-H3_v24.json",
        "name": "AcademiaSD_MiniMax-H3_v24.json",
    }
]

def run_cmd_live(cmd, cwd=None):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0

if not Path(COMFYUI_DIR).exists():
    raise RuntimeError(f"❌ ComfyUI not found at {COMFYUI_DIR}. Install ComfyUI first.")

custom_nodes_dir = Path(COMFYUI_DIR) / "custom_nodes"
custom_nodes_dir.mkdir(exist_ok=True)

for repo_url in CUSTOM_NODES:
    node_name = repo_url.split("/")[-1]
    node_path = custom_nodes_dir / node_name
    if not node_path.exists(): 
        run_cmd_live(f"git clone {repo_url}", cwd=str(custom_nodes_dir))
    else: 
        run_cmd_live("git pull", cwd=str(node_path))
        
    req_file = node_path / "requirements.txt"
    if req_file.exists(): 
        run_cmd_live(f"{PYTHON} -m pip install -r {req_file}")
    install_script = node_path / "install.py"
    if install_script.exists(): 
        run_cmd_live(f"{PYTHON} {install_script}", cwd=str(node_path))

workflow_dir = Path(COMFYUI_DIR) / "user" / "default" / "workflows"
workflow_dir.mkdir(parents=True, exist_ok=True)

for wf in WORKFLOWS:
    workflow_path = workflow_dir / wf["name"]
    try:
        urllib.request.urlretrieve(wf["url"], str(workflow_path))
        print(f"✅ Saved workflow: {wf['name']}")
    except Exception as e: 
        print(f"⚠️ Failed to download {wf['name']}: {e}")

print("\n✅ Nodes and Workflows setup complete!")
print(f"""
🧩 Custom Node:   {', '.join(url.split('/')[-1] for url in CUSTOM_NODES)}
📋 Workflow:      {', '.join(w['name'] for w in WORKFLOWS)}
🚀 Restart ComfyUI to load the new node:
!cd {COMFYUI_DIR} && {PYTHON} main.py \\
--listen 0.0.0.0 --port 8188 \\
--use-sage-attention --enable-manager --enable-manager-legacy-ui
""")
