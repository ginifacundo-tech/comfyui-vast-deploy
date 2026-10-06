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

KNOWN_TORCH_CUDA_TAGS = [
    ("11.8", "cu118"), ("12.1", "cu121"), ("12.4", "cu124"), 
    ("12.6", "cu126"), ("12.8", "cu128"), ("12.9", "cu129"), ("13.0", "cu130"),
]
BLACKWELL_FLOOR = "12.8"

def ensure_apt_packages(packages):
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    prefix = [] if is_root else ["sudo"]
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    try:
        run(prefix + ["apt-get", "update", "-qq"], env=env)
        run(prefix + ["apt-get", "install", "-y", "-qq"] + packages, env=env)
    except RuntimeError as e:
        print(f"Warning: apt-get step failed ({e}).")

def run(cmd, cwd=None, env=None, check=True):
    print(f"\n$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    process = subprocess.Popen(
        cmd, cwd=cwd, env=env, shell=isinstance(cmd, str),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    for line in process.stdout:
        print(line, end="")
        sys.stdout.flush()
    process.wait()
    if check and process.returncode != 0:
        raise RuntimeError(f"Command failed (exit {process.returncode}): {cmd}")
    return process.returncode

def version_tuple(v):
    return tuple(int(x) for x in v.split("."))

def detect_driver_cuda_version():
    try:
        out = subprocess.check_output(["nvidia-smi"], text=True)
        m = re.search(r"CUDA Version:\s*([\d.]+)", out)
        if m: return m.group(1)
    except Exception as e:
        print(f"Warning: nvidia-smi check failed: {e}")
    return None

def detect_compute_capability():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], text=True)
        return out.strip().splitlines()[0].strip()
    except Exception as e:
        print(f"Warning: could not detect compute capability: {e}")
    return None

def detect_system_nvcc_version():
    try:
        out = subprocess.check_output(["nvcc", "--version"], text=True)
        m = re.search(r"release (\d+\.\d+)", out)
        if m: return m.group(1)
    except Exception as e:
        print(f"No usable system nvcc found ({e}).")
    return None

def pick_torch_cuda_tag(driver_cuda_version, compute_cap, system_nvcc_version):
    floor = version_tuple(BLACKWELL_FLOOR) if (compute_cap and compute_cap.startswith("12")) else (0, 0)
    def best_tag_leq(version_str):
        if version_str is None: return None
        v = version_tuple(version_str)
        eligible = [(ver, tag) for ver, tag in KNOWN_TORCH_CUDA_TAGS if version_tuple(ver) <= v and version_tuple(ver) >= floor]
        return eligible[-1] if eligible else None

    if system_nvcc_version:
        match = best_tag_leq(system_nvcc_version)
        if match:
            ver, tag = match
            print(f"System nvcc is {system_nvcc_version}; selecting torch tag {tag} (CUDA {ver}).")
            return tag
            
    match = best_tag_leq(driver_cuda_version)
    if match:
        ver, tag = match
        print(f"Falling back to torch tag {tag} (CUDA {ver}) based on driver version.")
        return tag
        
    if floor > (0, 0):
        raise RuntimeError(f"This GPU needs CUDA {BLACKWELL_FLOOR}+, but driver only supports {driver_cuda_version}.")
        
    print("Could not confidently pick a torch CUDA tag; defaulting to cu124.")
    return "cu124"

def main():
    os.makedirs(WORKSPACE, exist_ok=True)
    print("=== Step 0: Ensuring OS-level prerequisites ===")
    ensure_apt_packages(["git", "python3-venv", "python3-pip"])

    print("\n=== Step 1: Detecting GPU / CUDA ===")
    driver_cuda_version = detect_driver_cuda_version()
    compute_cap = detect_compute_capability()
    system_nvcc_version = detect_system_nvcc_version()
    print(f"Driver-reported max CUDA version: {driver_cuda_version}")
    print(f"GPU compute capability: {compute_cap}")
    print(f"System nvcc version: {system_nvcc_version}")
    
    torch_tag = pick_torch_cuda_tag(driver_cuda_version, compute_cap, system_nvcc_version)
    index_url = f"https://download.pytorch.org/whl/{torch_tag}"
    print(f"Will install torch from: {index_url}")

    print("\n=== Step 2: Cloning / updating ComfyUI ===")
    if not os.path.isdir(COMFY_DIR):
        run(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", COMFY_DIR])
    else:
        run(["git", "pull"], cwd=COMFY_DIR)

    print("\n=== Step 2b: Ensuring clean ComfyUI-Manager installation ===")
    manager_dir = os.path.join(COMFY_DIR, "custom_nodes", "ComfyUI-Manager")
    
    if os.path.isdir(manager_dir):
        print("Existing Manager folder found. Wiping it to ensure a clean, up-to-date clone...")
        shutil.rmtree(manager_dir)
        
    print("Cloning fresh copy of ComfyUI-Manager from Comfy-Org (main branch)...")
    run(["git", "clone", "https://github.com/Comfy-Org/ComfyUI-Manager.git", manager_dir])

    print("\n=== Step 3: Creating venv ===")
    if not os.path.isdir(VENV_DIR):
        run([sys.executable, "-m", "venv", VENV_DIR])
        run([PIP_BIN, "install", "--upgrade", "pip", "setuptools", "wheel"])

    print("\n=== Step 4: Installing torch ===")
    run([PIP_BIN, "install", "torch", "torchvision", "torchaudio", "--index-url", index_url])
    run([PYTHON_BIN, "-c", "import torch; print('torch:', torch.__version__, '| torch CUDA:', torch.version.cuda)"])

    print("\n=== Step 5: Installing ComfyUI requirements ===")
    run([PIP_BIN, "install", "-r", os.path.join(COMFY_DIR, "requirements.txt")])
    
    print("\n=== Step 5b: Installing ComfyUI-Manager requirements ===")
    manager_requirements = os.path.join(manager_dir, "requirements.txt")
    if os.path.isfile(manager_requirements):
        run([PIP_BIN, "install", "-r", manager_requirements])

    print("\n=== Done ===")

if __name__ == "__main__":
    main()
