import os
import subprocess
import sys
import urllib.request
import urllib.error
import json
import re

COMFYUI_DIR = "/workspace/ComfyUI"
CUSTOM_NODES_DIR = os.path.join(COMFYUI_DIR, "custom_nodes")
REFMOD_DIR = os.path.join(CUSTOM_NODES_DIR, "ComfyUI-MiniMaxH3Mod")

# Placed inside the default workflows dir so ComfyUI natively lists them in the UI
WORKFLOW_DEST_DIR = os.path.join(COMFYUI_DIR, "user", "default", "workflows", "refmod")

# --- NEW: input folders so you're ready to drop reference files in ---
INPUT_DIR = os.path.join(COMFYUI_DIR, "input")
REFMOD_INPUT_SUBDIRS = {
    "refmod_images": "Drop your reference IMAGES here (.png, .jpg, .webp)",
    "refmod_video":  "Drop your reference VIDEOS here (.mp4, .mov, .webm)",
}

PYTHON_BIN = "/workspace/comfy_venv/bin/python"

# Read the repo URL from the environment (set by master.sh)
REPO_RAW_BASE = os.environ.get(
    "REPO_RAW_BASE",
    "https://raw.githubusercontent.com/ginifacundo-tech/comfyui-vast-deploy/main"
)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def run_cmd(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    sys.stdout.flush()
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    for line in process.stdout:
        print(line, end="")
        sys.stdout.flush()
    process.wait()
    return process.returncode


# ----------------------------------------------------------------------
# NEW: create the input directories
# ----------------------------------------------------------------------
def create_input_directories():
    print("\n📁 Preparing RefMod input directories...")

    if not os.path.isdir(COMFYUI_DIR):
        print(f"⚠️  ComfyUI not found at {COMFYUI_DIR} — skipping input folder creation.")
        return

    try:
        os.makedirs(INPUT_DIR, exist_ok=True)
    except OSError as e:
        print(f"❌ Could not create {INPUT_DIR}: {e}")
        return

    for subdir, description in REFMOD_INPUT_SUBDIRS.items():
        target = os.path.join(INPUT_DIR, subdir)
        try:
            os.makedirs(target, exist_ok=True)
            print(f"   ✅ {target}")

            # Optional: drop a placeholder README (delete this block if unwanted)
            readme = os.path.join(target, "README.txt")
            if not os.path.exists(readme):
                with open(readme, "w", encoding="utf-8") as f:
                    f.write(f"{description}\n")
        except OSError as e:
            print(f"   ❌ Failed to create {target}: {e}")


# ----------------------------------------------------------------------
# NEW: cupy / CUDA safeguard (fixes the pkg_resources build error)
# ----------------------------------------------------------------------
def detect_cuda_version():
    try:
        res = subprocess.run(
            [PYTHON_BIN, "-c", "import torch; print(torch.version.cuda or '')"],
            capture_output=True, text=True
        )
        out = res.stdout.strip()
        if out:
            return out.splitlines()[-1].strip()
    except Exception:
        pass

    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        match = re.search(r"CUDA Version:\s+(\d+\.\d+)", res.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def ensure_cupy_for(req_file):
    """Only acts if the requirements file actually asks for cupy."""
    try:
        with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
            contents = f.read().lower()
    except OSError:
        return

    if "cupy" not in contents:
        return

    cuda_ver = detect_cuda_version()
    if not cuda_ver:
        print("⚠️  cupy requested but CUDA version not detected; pip will attempt a source build.")
        return

    pkg = None
    if cuda_ver.startswith("12"):
        pkg = "cupy-cuda12x"
    elif cuda_ver.startswith("11"):
        pkg = "cupy-cuda11x"

    if pkg:
        print(f"🔍 CUDA {cuda_ver} detected — pre-installing {pkg} to avoid a source build...")
        run_cmd([PYTHON_BIN, "-m", "pip", "install", pkg])


def main():
    print("🚀 Starting ComfyUI-MiniMaxH3Mod (RefMod) installation...")

    # 1. Create input folders FIRST so they exist even if the clone fails
    create_input_directories()

    # 2. Make sure build tooling is present (Python 3.12 drops setuptools by default)
    print("\n🔧 Upgrading pip / setuptools / wheel...")
    run_cmd([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    # 3. Clone or update the repository
    if not os.path.exists(REFMOD_DIR):
        print("\n⬇️  Cloning ComfyUI-MiniMaxH3Mod...")
        clone_cmd = ["git", "clone",
                     "https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod.git",
                     REFMOD_DIR]
        if run_cmd(clone_cmd) != 0:
            print("❌ Failed to clone repository.")
            sys.exit(1)
    else:
        print("\n✅ ComfyUI-MiniMaxH3Mod already exists. Updating...")
        run_cmd(["git", "pull"], cwd=REFMOD_DIR)

    # 4. Install requirements
    req_file = os.path.join(REFMOD_DIR, "requirements.txt")
    if os.path.exists(req_file):
        ensure_cupy_for(req_file)
        print("\n📦 Installing RefMod requirements...")
        run_cmd([PYTHON_BIN, "-m", "pip", "install", "-r", req_file])
    else:
        print("\n⚠️  No requirements.txt found in RefMod.")

    # 5. Download RefMod workflows from the user's GitHub repo
    print("\n📂 Downloading RefMod workflows from GitHub repo...")
    os.makedirs(WORKFLOW_DEST_DIR, exist_ok=True)

    match = re.search(r'githubusercontent\.com/([^/]+/[^/]+)/', REPO_RAW_BASE)
    if not match:
        print("⚠️  Could not parse repo info from REPO_RAW_BASE. Skipping workflow download.")
        print("\n🎉 RefMod installation complete!")
        return

    repo_path = match.group(1)
    api_url = f'https://api.github.com/repos/{repo_path}/contents/refmod/workflows'

    headers = {'User-Agent': 'ComfyUI-Deploy'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        files = [item['name'] for item in data
                 if item['name'].endswith('.json') and item['type'] == 'file']

        if not files:
            print("⚠️  No .json workflows found in refmod/workflows/ directory.")
        else:
            for f in files:
                print(f'⬇️  Downloading workflow: {f}')
                url = f'{REPO_RAW_BASE}/refmod/workflows/{f}'
                urllib.request.urlretrieve(url, os.path.join(WORKFLOW_DEST_DIR, f))
            print("✅ All RefMod workflows downloaded successfully!")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠️  refmod/workflows/ directory not found in the repository.")
        elif e.code == 403:
            print("⚠️  GitHub API rate limit hit. Set GITHUB_TOKEN to raise the limit.")
        else:
            print(f"⚠️  Failed to fetch workflows: {e}")
    except Exception as e:
        print(f"⚠️  Failed to fetch workflows: {e}")

    print("\n🎉 RefMod installation complete!")


if __name__ == "__main__":
    main()
