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
if is_enabled "INSTALL_REFMOD"; then SCRIPTS_TO_DOWNLOAD+=("install_refmod.py"); fi

echo "🚀 Fetching enabled provisioning scripts from GitHub Repo..."
for script in "${SCRIPTS_TO_DOWNLOAD[@]}"; do
    curl -sL "$REPO_RAW_BASE/scripts/$script" -o "/tmp/$script"
    if [ ! -s "/tmp/$script" ] || grep -q "404: Not Found" "/tmp/$script"; then
        echo "❌ CRITICAL: Failed to download $script" | tee -a /workspace/provisioning.log
        exit 1
    fi
    chmod +x "/tmp/$script"
done

# ==========================================
# 🚀 PHASE 1: CORE SETUP & DYNAMIC WORKFLOWS
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    run_task_foreground "Installing ComfyUI Core" "/tmp/install_comfyui.py"

    WORKFLOW_DIR="/workspace/ComfyUI/user/default/workflows"
    mkdir -p "$WORKFLOW_DIR"
    python3 -c "
import urllib.request, json, os, re
base = '$REPO_RAW_BASE'
m = re.search(r'githubusercontent\.com/([^/]+/[^/]+)/', base)
if not m: exit(0)
api = f'https://api.github.com/repos/{m.group(1)}/contents/workflows'
try:
    req = urllib.request.Request(api, headers={'User-Agent': 'Deploy'})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        for item in data:
            if item['name'].endswith('.json') and item['type'] == 'file':
                print(f'Downloading: {item[\"name\"]}')
                urllib.request.urlretrieve(f'{base}/workflows/{item[\"name\"]}', os.path.join('$WORKFLOW_DIR', item['name']))
        print('All base workflows downloaded.')
except Exception as e: print(f'Workflow fetch: {e}')
" | tee -a /workspace/provisioning.log

    SETTINGS_DIR="/workspace/ComfyUI/user/default"
    mkdir -p "$SETTINGS_DIR"
    curl -sL "$REPO_RAW_BASE/config/comfy.settings.json" -o "$SETTINGS_DIR/comfy.settings.json" 2>/dev/null
fi

# ==========================================
# 🚀 PHASE 2: EARLY LAUNCH
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    echo "🚀 Launching ComfyUI EARLY on port 8188..." | tee -a /workspace/provisioning.log
    nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &
    COMFY_PID=$!
fi

# ==========================================
# 🚀 PHASE 3: MISSING NODES & BACKGROUND TASKS
# ==========================================
if is_enabled "ENABLE_MISSING_NODES"; then
    run_task_foreground "Scanning & Installing Missing Nodes" "/tmp/install_missing_nodes.py"
fi

(
    if is_enabled "ENABLE_INSTALL_NODES"; then run_task_background "Installing Custom Nodes" "/tmp/install_nodes.py" "/workspace/nodes_install.log"; fi
    if is_enabled "ENABLE_DOWNLOAD_MODELS"; then run_task_background "Downloading Models" "/tmp/download_models.py" "/workspace/models_download.log"; fi
    if is_enabled "ENABLE_DOWNLOAD_LORAS"; then run_task_background "Downloading LoRAs" "/tmp/download_loras.py" "/workspace/loras_download.log"; fi
    if is_enabled "ENABLE_DOWNLOAD_QWEN_IMAGE"; then run_task_background "Downloading Qwen Image" "/tmp/download_qwen_image.py" "/workspace/qwen_image_download.log"; fi
    if is_enabled "ENABLE_SAGEATTENTION"; then run_task_background "Building SageAttention" "/tmp/install_sageattention.py" "/workspace/sageattention_build.log"; fi
    if is_enabled "INSTALL_REFMOD"; then run_task_background "Installing RefMod" "/tmp/install_refmod.py" "/workspace/refmod_install.log"; fi
) &
BG_PID=$!

# ==========================================
# 🚀 PHASE 4: FINALIZE & RESTART
# ==========================================
if is_enabled "ENABLE_INSTALL_COMFYUI"; then
    wait $BG_PID
    kill $COMFY_PID 2>/dev/null || pkill -f "ComfyUI/main.py"
    sleep 3
    
    LAUNCH_FLAGS="--listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui"
    if is_enabled "ENABLE_SAGEATTENTION"; then 
        LAUNCH_FLAGS="$LAUNCH_FLAGS --use-sage-attention"
    fi
    
    nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py $LAUNCH_FLAGS > /workspace/comfyui_startup.log 2>&1 &
    echo "🎉 ALL DONE! ComfyUI restarted with final configuration." | tee -a /workspace/provisioning.log
fi
