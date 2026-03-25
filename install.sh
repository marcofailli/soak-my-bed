#!/bin/bash
KLIPPER_PATH="${HOME}/klipper"
PYTHON_ENV="${HOME}/klippy-env"

echo "--- 🛋️ Installing Soak My Bed ---"

# 1. Plugin link in Klipper extras
if [ -d "$KLIPPER_PATH" ]; then
    ln -sf "${HOME}/soak-my-bed/klippy/extras/soak_my_bed.py" "${KLIPPER_PATH}/klippy/extras/soak_my_bed.py"
    echo "✅ Plugin linked to Klipper extras."
else
    echo "❌ Klipper not found at $KLIPPER_PATH"
    exit 1
fi

# 2. Dependencies installation
echo "📦 Installing Python dependencies..."
${PYTHON_ENV}/bin/pip install numpy matplotlib scipy

echo "✅ Dependencies installed."
echo "--- Installation Complete! ---"
echo "Please add [soak_my_bed] to your printer.cfg and restart Klipper."
