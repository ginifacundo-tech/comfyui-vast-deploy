#!/bin/bash
set -eo pipefail

# SAFETY: Wait for Vast.ai to finish mounting the /workspace directory
for i in {1..15}; do
    if [ -d "/workspace" ]; then break; fi
    sleep 2
done

mkdir -p /workspace
> /workspace/provisioning.log

# ==========================================
# 🛠️ HELPER FUNCTIONS & ENV VAR PARSING
# ==========================================
is_enabled() {
    local var_name="$1"
    local default_val="${2:-true}"
    local val="${!var_name:-$default_val}"
    val=$(echo "$val" | tr '[:upper:]' '[:lower:]')
    [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]
}

run_task_foreground() {
    local task_name="$1"
    local script_path="$2"
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "⏳ STARTING: $task_name" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
    if python3 "$script_path" 2>&1 | tee -a /workspace/provisioning.log; then
        echo "✅ COMPLETED: $task_name" | tee -a /workspace/provisioning.log
        echo "============================================================" | tee -a /workspace/provisioning.log
    else
        echo "❌ ERROR: $task_name failed!" | tee -a /workspace/provisioning.log
        echo "============================================================" | tee -a /workspace/provisioning.log
        exit 1
    fi
}

run_task_background() {
    local task_name="$1"
    local script_path="$2"
    local log_file="$3"
    echo "============================================================"
    echo "⏳ STARTING: $task_name"
    echo "   (Detailed output saving to $log_file)"
    echo "============================================================"
    if python3 "$script_path" > "$log_file" 2>&1; then
        echo "✅ COMPLETED: $task_name"
        echo "============================================================"
    else
        echo "❌ ERROR: $task_name failed!"
        echo "============================================================"
    fi
}

# ==========================================
# 🚀 DYNAMIC SCRIPT FETCHING
# ==========================================
# Note: Updated to your actual GitHub repo based on previous context
REPO_RAW_BASE="https://raw.githubusercontent.com/ginifacundo-tech/comfyui-vast-deploy/main"

echo "🚀 Evaluating enabled scripts..."
SCRIPTS_TO_DOWNLOAD=()

if is_enabled "ENABLE_INSTALL_COMFYUI"; then SCRIPTS_TO_DOWNLOAD+=("install_comfyui.py"); fi
if is_enabled "ENABLE_INSTALL_NODES"; then SCRIPTS_TO_DOWNLOAD+=("install_nodes.py"); fi
if is_enabled "ENABLE_DOWNLOAD_MODELS"; then SCRIPTS_TO_DOWNLOAD+=("download_models.py"); fi
if is_enabled "ENABLE_DOWNLOAD_LORAS"; then SCRIPTS_TO_DOWNLOAD+=("download_loras.py"); fi
if is_enabled "ENABLE_DOWNLOAD_QWEN_IMAGE"; then SCRIPTS_TO_DOWNLOAD+=("download_qwen_image.py"); fi
if is_enabled "ENABLE_SAGEATTENTION"; then SCRIPTS_TO_DOWNLOAD+=("install_sageattention.py"); fi
if is_enabled "ENABLE_MISSING_NODES"; then SCRIPTS_TO_DOWNLOAD+=("install_missing_nodes.py"); fi

echo "🚀 Fetching enabled provisioning scripts from GitHub Repo..."
for script in "${SCRIPTS_TO_DOWNLOAD[@]}"; do
    curl -sL "$REPO_RAW_BASE/scripts/$script" -o "/tmp/$script"
    
    if [ ! -s "/tmp/$script" ] || grep -q "404: Not Found" "/tmp/$script"; then
        echo "❌ CRITICAL ERROR: Failed to download $script" | tee -a /workspace/provisioning.log
        exit 1
    fi
    chmod +x "/tmp/$script"
done

# ==========================================
# 🚀 PHASE 1: CORE SETUP & DYNAMIC WORKFLOWS
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    run_task_foreground "Installing ComfyUI Core" "/tmp/install_comfyui.py"
    
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "⏳ STARTING: Downloading All Workflows from Repo" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
    
    WORKFLOW_DIR="/workspace/ComfyUI/user/default/workflows"
    mkdir -p "$WORKFLOW_DIR"

    # Use Python to query the GitHub API and download all .json files dynamically
    python3 -c "
import urllib.request
import json
import os
import re

repo_raw_base = '$REPO_RAW_BASE'
match = re.search(r'githubusercontent\.com/([^/]+/[^/]+)/', repo_raw_base)
if not match:
    print('⚠️ Could not parse repo info from REPO_RAW_BASE')
    exit(1)
    
repo_path = match.group(1)
api_url = f'https://api.github.com/repos/{repo_path}/contents/workflows'

try:
    req = urllib.request.Request(api_url, headers={'User-Agent': 'ComfyUI-Deploy-Script'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        files = [item['name'] for item in data if item['name'].endswith('.json') and item['type'] == 'file']
        
        if not files:
            print('⚠️ No .json workflows found in the repo workflows directory.')
        else:
            os.makedirs('$WORKFLOW_DIR', exist_ok=True)
            for f in files:
                print(f'⬇️ Downloading workflow: {f}')
                url = f'{repo_raw_base}/workflows/{f}'
                urllib.request.urlretrieve(url, os.path.join('$WORKFLOW_DIR', f))
            print('✅ All workflows downloaded successfully!')
except urllib.error.HTTPError as e:
    if e.code == 404:
        print('⚠️ Workflows directory not found in the repository.')
    else:
        print(f'⚠️ Failed to fetch workflows: {e}')
except Exception as e:
    print(f'⚠️ Failed to fetch workflows: {e}')
" | tee -a /workspace/provisioning.log

    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "✅ COMPLETED: Downloading All Workflows from Repo" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log

    # Apply Global Settings
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "⏳ STARTING: Applying Global ComfyUI Settings" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
    
    SETTINGS_DIR="/workspace/ComfyUI/user/default"
    mkdir -p "$SETTINGS_DIR"
    curl -sL "$REPO_RAW_BASE/config/comfy.settings.json" -o "$SETTINGS_DIR/comfy.settings.json"
    
    echo "✅ Global settings applied successfully!" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
fi

# ==========================================
# 🚀 PHASE 2: EARLY LAUNCH
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "🚀 STARTING: Launching ComfyUI EARLY" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "💡 You can now open the web UI on port 8188!" | tee -a /workspace/provisioning.log
    
    nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &
    COMFY_PID=$!
    
    echo "✅ ComfyUI is running on port 8188." | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
fi

# ==========================================
# 🚀 PHASE 3: MISSING NODES & BACKGROUND TASKS
# ==========================================
if is_enabled "ENABLE_MISSING_NODES"; then
    run_task_foreground "Scanning & Installing Missing Nodes" "/tmp/install_missing_nodes.py"
fi

echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Background Tasks" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

(
    if is_enabled "ENABLE_INSTALL_NODES"; then
        run_task_background "Installing Custom Nodes" "/tmp/install_nodes.py" "/workspace/nodes_install.log"
    fi
    
    if is_enabled "ENABLE_DOWNLOAD_MODELS"; then
        run_task_background "Downloading Models" "/tmp/download_models.py" "/workspace/models_download.log"
    fi
    
    if is_enabled "ENABLE_DOWNLOAD_LORAS"; then
        run_task_background "Downloading LoRAs" "/tmp/download_loras.py" "/workspace/loras_download.log"
    fi
    
    if is_enabled "ENABLE_DOWNLOAD_QWEN_IMAGE"; then
        run_task_background "Downloading Qwen Image Models" "/tmp/download_qwen_image.py" "/workspace/qwen_image_download.log"
    fi
    
    if is_enabled "ENABLE_SAGEATTENTION"; then
        run_task_background "Building SageAttention" "/tmp/install_sageattention.py" "/workspace/sageattention_build.log"
    fi
    
    echo "============================================================"
    echo "✅ ALL ENABLED BACKGROUND TASKS FINISHED"
    echo "============================================================"
) &
BG_PID=$!

echo "💡 Background tasks are running." | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 4: FINALIZE & RESTART
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "⏳ Waiting for background tasks to finish..." | tee -a /workspace/provisioning.log
    wait $BG_PID
    echo "✅ Background tasks finished!" | tee -a /workspace/provisioning.log

    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "🔄 STARTING: Restarting ComfyUI with Acceleration" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log

    kill $COMFY_PID 2>/dev/null || pkill -f "/workspace/ComfyUI/main.py"
    sleep 3

    LAUNCH_FLAGS="--listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui"
    if is_enabled "ENABLE_SAGEATTENTION"; then
        LAUNCH_FLAGS="$LAUNCH_FLAGS --use-sage-attention"
    fi

    nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py $LAUNCH_FLAGS > /workspace/comfyui_startup.log 2>&1 &

    echo "✅ ComfyUI restarted successfully." | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
fi

echo "============================================================" | tee -a /workspace/provisioning.log
echo "🎉 ALL DONE!" | tee -a /workspace/provisioning.log
echo "🔍 Main log: /workspace/provisioning.log" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
