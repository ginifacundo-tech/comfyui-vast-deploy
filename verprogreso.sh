#!/bin/bash
# verprogreso.sh - A quick shortcut to tail the Vast.ai provisioning log

if [ ! -f /workspace/provisioning.log ]; then
    echo "⚠️ /workspace/provisioning.log not found yet. Waiting..."
    sleep 2
fi

echo "👀 Watching /workspace/provisioning.log (Press Ctrl+C to exit)..."
echo "============================================================"
tail -f /workspace/provisioning.log
