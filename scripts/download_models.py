import sys
import os
import subprocess
from pathlib import Path

PYTHON = sys.executable
COMFYUI_DIR = "/workspace/ComfyUI"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

if not HF_TOKEN:
    print("⚠️ WARNING: HF_TOKEN environment variable is not set!")

print("📦 Installing hf_transfer...")
subprocess.run([PYTHON, "-m", "pip", "install", "hf_transfer", "huggingface_hub", "--upgrade", "--quiet"], check=True)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
if HF_TOKEN: 
    os.environ["HF_TOKEN"] = HF_TOKEN

import hf_transfer
print(f"✅ hf_transfer installed")
if HF_TOKEN:
    from huggingface_hub import HfApi
    try: 
        print(f"✅ Authenticated as: {HfApi().whoami(token=HF_TOKEN)['name']}")
    except Exception as e: 
        print(f"⚠️ Token verification failed: {e}")

MODELS = [
    {"repo": "Comfy-Org/MiniMax-H3", "filename": "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors", "dest": f"{COMFYUI_DIR}/models/"},
    {"repo": "ethanfel/Qwen3-VL-32B-Ultra-Heretic-H3-ComfyUI-INT8-ConvRot", "filename": "qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors", "dest": f"{COMFYUI_DIR}/models/text_encoders/"},
    {"repo": "larryvrh/MiniMax-H3-Turbo-Lora", "filename": "minimax_h3_turbo_v4_step600_ema.safetensors", "dest": f"{COMFYUI_DIR}/models/loras/"},
    {"repo": "Comfy-Org/MiniMax-H3", "filename": "vae/minimax_h3_video_vae_fp16.safetensors", "dest": f"{COMFYUI_DIR}/models/"},
    {"repo": "Comfy-Org/MiniMax-H3", "filename": "vae/minimax_h3_audio_vae_fp32.safetensors", "dest": f"{COMFYUI_DIR}/models/"},
    {"repo": "Kijai/MiniMax-H3-TAE", "filename": "vae_approx/taeh3.safetensors", "dest": f"{COMFYUI_DIR}/models/"},
]

from huggingface_hub import hf_hub_download
print("\n🚀 Starting HuggingFace model downloads...")
for model in MODELS:
    dest_dir = Path(model["dest"])
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n⬇️ Downloading {model['filename']} from {model['repo']}")
    try:
        path = hf_hub_download(repo_id=model["repo"], filename=model["filename"], local_dir=str(dest_dir), resume_download=True, token=HF_TOKEN if HF_TOKEN else None)
        size_gb = Path(path).stat().st_size / (1024**3)
        print(f"✅ Downloaded: {Path(path).name} ({size_gb:.1f} GB)")
    except Exception as e: 
        print(f"❌ Failed: {e}")
print("\n🎉 All HF downloads complete!")
