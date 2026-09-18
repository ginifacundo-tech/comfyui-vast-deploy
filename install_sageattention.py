"""
SageAttention install script for vast.ai (Jupyter)
"""
import argparse
import os
import re
import subprocess
import sys
import time

WORKSPACE = "/workspace"
VENV_DIR = os.path.join(WORKSPACE, "comfy_venv")
PYTHON_BIN = os.path.join(VENV_DIR, "bin", "python")
PIP_BIN = os.path.join(VENV_DIR, "bin", "pip")
SAGE_DIR = os.path.join(WORKSPACE, "SageAttention")
VENV_DIR_OVERRIDE = None

KNOWN_TORCH_CUDA_TAGS = [
    ("11.8", "cu118"), ("12.1", "cu121"), ("12.4", "cu124"), 
    ("12.6", "cu126"), ("12.8", "cu128"), ("12.9", "cu129"), ("13.0", "cu130"),
]
BLACKWELL_FLOOR = "12.8"

def apt_install_with_retry(prefix, packages, env, max_retries=5, delay_seconds=10):
    repaired = False
    for attempt in range(1, max_retries + 1):
        result = subprocess.run(prefix + ["apt-get", "install", "-y"] + packages, env=env, capture_output=True, text=True)
        if result.returncode == 0: return
        combined = (result.stdout or "") + (result.stderr or "")
        if ("Could not get lock" in combined or "is another process using it" in combined) and attempt < max_retries:
            time.sleep(delay_seconds); continue
        if ("dpkg was interrupted" in combined) and not repaired:
            subprocess.run(prefix + ["dpkg", "--configure", "-a"], env=env)
            subprocess.run(prefix + ["apt-get", "install", "-f", "-y"], env=env)
            repaired = True; continue
        raise RuntimeError(f"apt-get install failed for {packages}")

def ensure_apt_packages(packages):
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    prefix = [] if is_root else ["sudo"]
    env = os.environ.copy(); env["DEBIAN_FRONTEND"] = "noninteractive"
    try:
        subprocess.run(prefix + ["apt-get", "update"], env=env)
        apt_install_with_retry(prefix, packages, env)
    except RuntimeError as e: print(f"Warning: apt-get step failed ({e})")

def run(cmd, cwd=None, env=None, check=True):
    print(f"\n$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    process = subprocess.Popen(cmd, cwd=cwd, env=env, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout: print(line, end=""); sys.stdout.flush()
    process.wait()
    if check and process.returncode != 0: raise RuntimeError(f"Command failed: {cmd}")

def detect_driver_cuda_version():
    try: return re.search(r"CUDA Version:\s*([\d.]+)", subprocess.check_output(["nvidia-smi"], text=True)).group(1)
    except: return None

def detect_compute_capability():
    try: return subprocess.check_output(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], text=True).strip().splitlines()[0].strip()
    except: return None

def detect_system_nvcc_version():
    try: return re.search(r"release (\d+.\d+)", subprocess.check_output(["nvcc", "--version"], text=True)).group(1)
    except: return None

def ensure_venv_with_torch(driver_cuda_version, compute_cap, system_nvcc_version):
    if not os.path.isdir(VENV_DIR):
        run([sys.executable, "-m", "venv", VENV_DIR])
        run([PIP_BIN, "install", "--upgrade", "pip", "setuptools", "wheel"])
    if subprocess.run([PYTHON_BIN, "-c", "import torch"], capture_output=True).returncode != 0:
        run([PIP_BIN, "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"])

def patch_sageattention_cpp20():
    setup_py = os.path.join(SAGE_DIR, "setup.py")
    if os.path.isfile(setup_py):
        with open(setup_py, "r", encoding="utf-8") as f: content = f.read()
        if "-std=c++17" in content:
            content = content.replace("-std=c++17", "-std=c++20")
            with open(setup_py, "w", encoding="utf-8") as f: f.write(content)

def main():
    os.makedirs(WORKSPACE, exist_ok=True)
    ensure_apt_packages(["git", "python3-venv", "python3-pip", "build-essential"])
    
    driver_cuda_version = detect_driver_cuda_version()
    compute_cap = detect_compute_capability()
    system_nvcc_version = detect_system_nvcc_version()
    
    ensure_venv_with_torch(driver_cuda_version, compute_cap, system_nvcc_version)
    
    if subprocess.run([PYTHON_BIN, "-c", "import sageattention"], capture_output=True).returncode == 0:
        print("sageattention already installed, skipping."); return

    if not os.path.isdir(SAGE_DIR): run(["git", "clone", "https://github.com/thu-ml/SageAttention.git", SAGE_DIR])
    else: run(["git", "pull"], cwd=SAGE_DIR)
    
    patch_sageattention_cpp20()
    build_env = os.environ.copy()
    if compute_cap: build_env["TORCH_CUDA_ARCH_LIST"] = compute_cap
    
    run([PYTHON_BIN, "-m", "pip", "install", "-e", ".", "--no-build-isolation"], cwd=SAGE_DIR, env=build_env)
    run([PYTHON_BIN, "-c", "import torch, sageattention; print('sageattention import OK')"])
    
    print("\n=== Done ===")
    print(f"Venv: {VENV_DIR}")
    print("If ComfyUI is installed, launch it with --use-sage-attention to enable it, e.g.:")
    print(f"  {PYTHON_BIN} /workspace/ComfyUI/main.py --use-sage-attention --listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui")

if __name__ == "__main__":
    main()