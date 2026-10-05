import sys
import os
import subprocess
from pathlib import Path

PYTHON = sys.executable
COMFYUI_DIR = "/workspace/ComfyUI"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

def is_enabled(env_var_name, default=True):
    val = os.environ.get(env_var_name, "").lower()
    if not val: return default
    return val in ("true", "1", "yes")

if not HF_TOKEN:
    print("⚠️ WARNING: HF_TOKEN environment variable is not set!")

print("📦 Ensuring hf_transfer is installed...")
subprocess.run([PYTHON, "-m", "pip", "install", "hf_transfer", "huggingface_hub", "--upgrade", "--quiet"], check=True)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
if HF_TOKEN: os.environ["HF_TOKEN"] = HF_TOKEN

import hf_transfer
from huggingface_hub import hf_hub_download

# ==========================================
# 📦 QWEN IMAGE 2.1 MODEL DEFINITIONS
# ==========================================
# Add your specific Qwen 2.1 models here. 
# Example structure provided below:
MODELS = [
    {
        "env_var": "DOWNLOAD_QWEN_IMAGE_2_1_bf16",
        "repo": "Comfy-Org/Qwen-Image-2.1", # Replace with your actual Qwen repo
        "filename": "diffusion_models/qwen_image_2.1_bf16.safetensors",         # Replace with actual filename
        "dest": f"{COMFYUI_DIR}/models/diffusion_models/"
    },
       {
        "env_var": "DOWNLOAD_QWEN_IMAGE_2_1_int8",
        "repo": "Comfy-Org/Qwen-Image-2.1", # Replace with your actual Qwen repo
        "filename": "diffusion_models/qwen_image_2.1_int8_convrot.safetensors",         # Replace with actual filename
        "dest": f"{COMFYUI_DIR}/models/diffusion_models/"
    },
       {
        "env_var": "DOWNLOAD_QWEN_IMAGE_TEXT_ENCODER_QWEN3VL_8B_BF16",
        "repo": "Comfy-Org/Qwen-Image-2.1", # Replace with your actual Qwen repo
        "filename": "text_encoders/qwen3vl_8b_bf16.safetensors",         # Replace with actual filename
        "dest": f"{COMFYUI_DIR}/models/text_encoders/"
    },
         "env_var": "DOWNLOAD_QWEN_IMAGE_VAE_BF16",
        "repo": "Comfy-Org/Qwen-Image-2.1", # Replace with your actual Qwen repo
        "filename": "vae/qwen_image_2.1_vae_bf16.safetensors",         # Replace with actual filename
        "dest": f"{COMFYUI_DIR}/models/vae/"
    },
        "env_var": "DOWNLOAD_QWEN_IMAGE_TURBO_LORA",
        "repo": "Viggle/Qwen-Image-2.1-viggle-turbo", # Replace with your actual Qwen repo
        "filename": "Qwen-Image-2.1-viggle-turbo-v0.2-5step-lora-r256.safetensors",         # Replace with actual filename
        "dest": f"{COMFYUI_DIR}/models/loras/"
    },
    
    # Add more Qwen models here if needed...
]

print("\n🚀 Starting Qwen Image model downloads...")
for model in MODELS:
    if not is_enabled(model["env_var"]):
        print(f"⏭️ Skipping {model['filename']} (Disabled via {model['env_var']})")
        continue

    dest_dir = Path(model["dest"])
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n⬇️ Downloading {model['filename']} from {model['repo']}")
    
    try:
        path = hf_hub_download(
            repo_id=model["repo"], 
            filename=model["filename"], 
            local_dir=str(dest_dir), 
            resume_download=True, 
            token=HF_TOKEN if HF_TOKEN else None
        )
        size_gb = Path(path).stat().st_size / (1024**3)
        print(f"✅ Downloaded: {Path(path).name} ({size_gb:.1f} GB)")
    except Exception as e:
        print(f"❌ Failed: {e}")

print("\n🎉 All enabled Qwen Image downloads complete!")
