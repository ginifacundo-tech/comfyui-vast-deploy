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
# 🛠️ HELPER FUNCTIONS
# ==========================================
run_task_foreground() {
    local task_name="$1"
    local script_path="$2"
    echo "============================================================" | tee -a /workspace/provisioning.log
    echo "⏳ STARTING: $task_name" | tee -a /workspace/provisioning.log
    echo "============================================================" | tee -a /workspace/provisioning.log
    if python3 "$script_path" 2>&1 | tee -a /workspace/provisioning.log; then
        echo "============================================================" | tee -a /workspace/provisioning.log
        echo "✅ COMPLETED: $task_name" | tee -a /workspace/provisioning.log
        echo "============================================================" | tee -a /workspace/provisioning.log
    else
        echo "============================================================" | tee -a /workspace/provisioning.log
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
        echo "============================================================"
        echo "✅ COMPLETED: $task_name"
        echo "============================================================"
    else
        echo "============================================================"
        echo "❌ ERROR: $task_name failed!"
        echo "🔍 Check $log_file for details."
        echo "============================================================"
    fi
}

# ==========================================
# 🚀 FETCH SCRIPTS FROM GITHUB REPO
# ==========================================
REPO_RAW_BASE="https://raw.githubusercontent.com/ginifacundo-tech/comfyui-vast-deploy/main"

echo "🚀 Fetching provisioning scripts from GitHub Repo..."
SCRIPTS=("install_comfyui.py" "install_nodes.py" "download_models.py" "download_loras.py" "install_sageattention.py" "install_missing_nodes.py")

for script in "${SCRIPTS[@]}"; do
    curl -sL "$REPO_RAW_BASE/scripts/$script" -o "/tmp/$script"
    
    if [ ! -s "/tmp/$script" ] || grep -q "404: Not Found" "/tmp/$script"; then
        echo "❌ CRITICAL ERROR: Failed to download $script" | tee -a /workspace/provisioning.log
        exit 1
    fi
    chmod +x "/tmp/$script"
done

# ==========================================
# 🚀 PHASE 1: CORE SETUP & WORKFLOW (FOREGROUND)
# ==========================================
run_task_foreground "Installing ComfyUI Core" "/tmp/install_comfyui.py"

# 🔧 FIX: Allow ComfyUI-Manager CLI to install nodes without the 0.0.0.0 security block
MANAGER_CONFIG="/workspace/ComfyUI/custom_nodes/ComfyUI-Manager/config.ini"
if [ -f "$MANAGER_CONFIG" ]; then
    sed -i 's/allow_git_url_install = False/allow_git_url_install = True/g' "$MANAGER_CONFIG"
    if ! grep -q "allow_git_url_install" "$MANAGER_CONFIG"; then
        sed -i '/^\[default\]/a allow_git_url_install = True' "$MANAGER_CONFIG"
    fi
    echo "✅ ComfyUI-Manager config updated to allow CLI installations." | tee -a /workspace/provisioning.log
fi

echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Downloading Custom Workflow" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
WORKFLOW_DIR="/workspace/ComfyUI/user/default/workflows"
mkdir -p "$WORKFLOW_DIR"
curl -sL "$REPO_RAW_BASE/workflows/workflow_academia.json" -o "$WORKFLOW_DIR/workflow_academia.json"
echo "✅ Workflow downloaded successfully!" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
echo "✅ COMPLETED: Downloading Custom Workflow" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

# 🔧 FIX: Run Missing Nodes installation BEFORE launching ComfyUI to avoid the security block
run_task_foreground "Scanning & Installing Missing Nodes" "/tmp/install_missing_nodes.py"

# ==========================================
# 🚀 PHASE 1.5: APPLY GLOBAL COMFYUI SETTINGS
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Applying Global ComfyUI Settings" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

SETTINGS_DIR="/workspace/ComfyUI/user/default"
mkdir -p "$SETTINGS_DIR"
curl -sL "$REPO_RAW_BASE/config/comfy.settings.json" -o "$SETTINGS_DIR/comfy.settings.json"

echo "✅ Global settings applied successfully!" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
echo "✅ COMPLETED: Applying Global ComfyUI Settings" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 2: EARLY LAUNCH
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "🚀 STARTING: Launching ComfyUI EARLY" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
echo "💡 You can now open the web UI on port 8188!" | tee -a /workspace/provisioning.log
nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &
COMFY_PID=$!
echo "✅ ComfyUI is running on port 8188." | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
echo "✅ COMPLETED: Launching ComfyUI EARLY" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 3: BACKGROUND TASKS
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Background Tasks" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

(
    run_task_background "Installing Custom Nodes" "/tmp/install_nodes.py" "/workspace/nodes_install.log"
    
    echo "============================================================"
    echo "⏳ STARTING: Patching ComfyUI-QwenVL-Mod"
    echo "============================================================"
    TARGET_FILE="/workspace/ComfyUI/custom_nodes/ComfyUI-QwenVL-Mod/AILab_QwenVL.py"
    mkdir -p "$(dirname "$TARGET_FILE")"
    curl -sL "$REPO_RAW_BASE/patches/AILab_QwenVL.py" -o "$TARGET_FILE"
    
    if [ -s "$TARGET_FILE" ] && ! grep -q "404: Not Found" "$TARGET_FILE"; then
        echo "✅ Custom AILab_QwenVL.py applied successfully!"
    else
        echo "⚠️ WARNING: Failed to apply patch. File might be missing in repo."
    fi
    echo "============================================================"
    
    run_task_background "Downloading Models" "/tmp/download_models.py" "/workspace/models_download.log"
    run_task_background "Downloading LoRAs" "/tmp/download_loras.py" "/workspace/loras_download.log"
    run_task_background "Building SageAttention" "/tmp/install_sageattention.py" "/workspace/sageattention_build.log"
    
    echo "============================================================"
    echo "✅ ALL BACKGROUND TASKS FINISHED"
    echo "============================================================"
) &
BG_PID=$!

echo "💡 Background tasks are running. Broad progress is shown below." | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 4: FINALIZE & RESTART WITH ACCELERATION
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ Waiting for background tasks to finish..." | tee -a /workspace/provisioning.log
wait $BG_PID
echo "✅ Background tasks finished!" | tee -a /workspace/provisioning.log

echo "============================================================" | tee -a /workspace/provisioning.log
echo "🔄 STARTING: Restarting ComfyUI with SageAttention & New Nodes" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

kill $COMFY_PID 2>/dev/null || pkill -f "/workspace/ComfyUI/main.py"
sleep 3

nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --use-sage-attention --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &

echo "✅ ComfyUI restarted successfully." | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
echo "✅ COMPLETED: Restarting ComfyUI with SageAttention & New Nodes" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

echo "============================================================" | tee -a /workspace/provisioning.log
echo "🎉 ALL DONE!" | tee -a /workspace/provisioning.log
echo "✅ ComfyUI is now running with SageAttention acceleration." | tee -a /workspace/provisioning.log
echo "✅ All models, LoRAs, missing nodes, and custom patches are fully installed." | tee -a /workspace/provisioning.log
echo "🔍 Main log: /workspace/provisioning.log" | tee -a /workspace/provisioning.log
echo "🔍 Detailed background logs: /workspace/*.log" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
