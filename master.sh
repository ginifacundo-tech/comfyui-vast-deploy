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
# 🚀 FETCH SCRIPTS FROM GITHUB REPO
# ==========================================
# ⚠️ REPLACE 'YOUR_USERNAME' AND 'YOUR_REPO' WITH YOUR ACTUAL GITHUB INFO!
REPO_RAW_BASE="https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main"

echo "🚀 Fetching provisioning scripts from GitHub Repo..."
SCRIPTS=("install_comfyui.py" "install_nodes.py" "download_models.py" "download_loras.py" "install_sageattention.py" "install_missing_nodes.py")

for script in "${SCRIPTS[@]}"; do
    # Notice the /scripts/ folder in the URL!
    curl -sL "$REPO_RAW_BASE/scripts/$script" -o "/tmp/$script"
    chmod +x "/tmp/$script"
done

# ==========================================
# 🚀 PHASE 1: CORE SETUP & WORKFLOW
# ==========================================
run_task_foreground "Installing ComfyUI Core" "/tmp/install_comfyui.py"
run_task_foreground "Installing Custom Nodes" "/tmp/install_nodes.py"

echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Downloading Custom Workflow" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
WORKFLOW_DIR="/workspace/ComfyUI/user/default/workflows"
mkdir -p "$WORKFLOW_DIR"
# Notice the /workflows/ folder in the URL!
curl -sL "$REPO_RAW_BASE/workflows/workflow_academia.json" -o "$WORKFLOW_DIR/workflow_academia.json"
echo "✅ Workflow downloaded successfully!" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

run_task_foreground "Scanning & Installing Missing Nodes" "/tmp/install_missing_nodes.py"

# ==========================================
# 🚀 PHASE 1.5: APPLY CUSTOM FILE PATCHES
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "⏳ STARTING: Patching ComfyUI-QwenVL-Mod" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

TARGET_FILE="/workspace/ComfyUI/custom_nodes/ComfyUI-QwenVL-Mod/AILab_QwenVL.py"
mkdir -p "$(dirname "$TARGET_FILE")"
# Notice the /patches/ folder in the URL!
curl -sL "$REPO_RAW_BASE/patches/AILab_QwenVL.py" -o "$TARGET_FILE"

echo "✅ Custom AILab_QwenVL.py applied successfully!" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 2: EARLY LAUNCH
# ==========================================
echo "============================================================" | tee -a /workspace/provisioning.log
echo "🚀 STARTING: Launching ComfyUI EARLY" | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log
nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &
COMFY_PID=$!
echo "✅ ComfyUI is running on port 8188." | tee -a /workspace/provisioning.log
echo "============================================================" | tee -a /workspace/provisioning.log

# ==========================================
# 🚀 PHASE 3: BACKGROUND DOWNLOADS & BUILD
# ==========================================
(
    run_task_background "Downloading Models" "/tmp/download_models.py" "/workspace/models_download.log"
    run_task_background "Downloading LoRAs" "/tmp/download_loras.py" "/workspace/loras_download.log"
    run_task_background "Building SageAttention" "/tmp/install_sageattention.py" "/workspace/sageattention_build.log"
    echo "✅ ALL BACKGROUND TASKS FINISHED"
) &
BG_PID=$!

# ==========================================
# 🚀 PHASE 4: FINALIZE & RESTART
# ==========================================
wait $BG_PID

kill $COMFY_PID 2>/dev/null || pkill -f "/workspace/ComfyUI/main.py"
sleep 3

nohup /workspace/comfy_venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --use-sage-attention --enable-manager --enable-manager-legacy-ui > /workspace/comfyui_startup.log 2>&1 &

echo "🎉 ALL DONE!" | tee -a /workspace/provisioning.log
