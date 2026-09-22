import sys
import os
import subprocess

VENV_DIR = "/workspace/comfy_venv"
PYTHON_BIN = os.path.join(VENV_DIR, "bin", "python")
PIP_BIN = os.path.join(VENV_DIR, "bin", "pip")

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
    print("🚀 Starting Flash Attention 2 installation...")
    
    # Check if already installed
    check_cmd = [PYTHON_BIN, "-c", "import flash_attn; print('Flash Attention 2 is already installed.')"]
    if run_cmd(check_cmd) == 0:
        print("✅ Flash Attention 2 is already installed. Skipping.")
        return

    print("📦 Installing Flash Attention 2 via pip (this may take a few minutes)...")
    # --no-build-isolation is highly recommended for flash-attn to use the existing torch cuda libraries
    install_cmd = [PIP_BIN, "install", "flash-attn", "--no-build-isolation"]
    
    return_code = run_cmd(install_cmd)
    
    if return_code == 0:
        print("\n✅ Flash Attention 2 installed successfully!")
        # Verify installation
        run_cmd([PYTHON_BIN, "-c", "import flash_attn; print('Verification: flash_attn imported successfully.')"])
    else:
        print("\n❌ Flash Attention 2 installation failed!")
        print("💡 Tip: Ensure you are using PyTorch 2.x with CUDA 11.8 or 12.x, and an Ampere (RTX 30xx) or newer GPU.")
        sys.exit(1)

if __name__ == "__main__":
    main()
