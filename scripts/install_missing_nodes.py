import os
import subprocess
import sys
from pathlib import Path

COMFYUI_DIR = "/workspace/ComfyUI"
CM_CLI = os.path.join(COMFYUI_DIR, "custom_nodes", "ComfyUI-Manager", "cm-cli.py")
WORKFLOW_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows")
PYTHON_BIN = "/workspace/comfy_venv/bin/python"

def scan_and_install(workflow_path):
    workflow_name = os.path.basename(workflow_path)
    print(f"\n🔍 Scanning '{workflow_name}' for missing nodes...")
    deps_file = f"/tmp/{workflow_name}_deps.json"
    cmd_deps = [PYTHON_BIN, CM_CLI, "deps-in-workflow", "--workflow", workflow_path, "--output", deps_file]
    try:
        process = subprocess.Popen(cmd_deps, cwd=COMFYUI_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout: print(line, end="")
        process.wait()
        if process.returncode != 0 or not os.path.exists(deps_file): return
        cmd_install = [PYTHON_BIN, CM_CLI, "install-deps", deps_file]
        process = subprocess.Popen(cmd_install, cwd=COMFYUI_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout: print(line, end="")
        process.wait()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if not os.path.exists(CM_CLI): sys.exit(1)
    if not os.path.exists(WORKFLOW_DIR): sys.exit(0)
    workflow_files = list(Path(WORKFLOW_DIR).glob("*.json"))
    for wf_path in workflow_files: scan_and_install(str(wf_path))
    print("\n🎉 Missing nodes scan complete!")
