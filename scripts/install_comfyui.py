import os
import re
import subprocess
import sys
import shutil

WORKSPACE = "/workspace"
COMFY_DIR = os.path.join(WORKSPACE, "ComfyUI")
VENV_DIR = os.path.join(WORKSPACE, "comfy_venv")
PYTHON_BIN = os.path.join(VENV_DIR, "bin", "python")
PIP_BIN = os.path.join(VENV_DIR, "bin", "pip")

def run(cmd, cwd=None, check=True):
    process = subprocess.Popen(cmd, cwd=cwd, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout: print(line, end="")
    process.wait()
    if check and process.returncode != 0: raise RuntimeError(f"Failed: {cmd}")

def main():
    os.makedirs(WORKSPACE, exist_ok=True)
    run(["sudo", "apt-get", "update", "-qq"], check=False)
    run(["sudo", "apt-get", "install", "-y", "-qq", "git", "python3-venv"], check=False)

    if not os.path.isdir(COMFY_DIR):
        run(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", COMFY_DIR])
    else:
        run(["git", "pull"], cwd=COMFY_DIR)

    manager_dir = os.path.join(COMFY_DIR, "custom_nodes", "ComfyUI-Manager")
    if os.path.isdir(manager_dir): shutil.rmtree(manager_dir)
    run(["git", "clone", "https://github.com/Comfy-Org/ComfyUI-Manager.git", manager_dir])

    if not os.path.isdir(VENV_DIR):
        run([sys.executable, "-m", "venv", VENV_DIR])
        run([PIP_BIN, "install", "--upgrade", "pip", "setuptools", "wheel"])

    run([PIP_BIN, "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"])
    run([PIP_BIN, "install", "-r", os.path.join(COMFY_DIR, "requirements.txt")])
    run([PIP_BIN, "install", "-r", os.path.join(manager_dir, "requirements.txt")])
    print("✅ ComfyUI Core installed successfully!")

if __name__ == "__main__":
    main()
