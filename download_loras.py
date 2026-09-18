import subprocess
import os

LORA_DIR = "/workspace/ComfyUI/models/loras"
os.makedirs(LORA_DIR, exist_ok=True)

CIVITAI_TOKEN = os.environ.get("CIVITAI_TOKEN", "")
if not CIVITAI_TOKEN:
    print("⚠️ WARNING: CIVITAI_TOKEN environment variable is not set!")

def download_lora(filename, model_id, file_id):
    url = f"https://civitai.red/api/download/models/{model_id}?fileId={file_id}&token={CIVITAI_TOKEN}"
    dest = os.path.join(LORA_DIR, filename)
    print(f"\n⬇️ Downloading {filename}...")
    result = subprocess.run(["curl", "-C", "-", "-L", "-o", dest, url])
    if result.returncode == 0:
        print(f"✅ Downloaded {filename}")
    else:
        print(f"❌ Failed to download {filename}")

LORAS_TO_DOWNLOAD = [
    ("MysticXXX_MMH3-V4.safetensors", "3266628", "3150341"),
    ("Minimaxh3-Licking_Balls_and_Penis-Ref2V-512_000000552.safetensors", "3265246", "3148884"),
    ("cum_facial_000005400.safetensors", "3290361", "3174815"),
    ("Titjob - Titfuck v0.95.safetensors", "3264280", "3147835"),
]

print("🚀 Starting Lora downloads...")
for filename, model_id, file_id in LORAS_TO_DOWNLOAD:
    download_lora(filename, model_id, file_id)
print("\n✅ All Loras download process finished.")