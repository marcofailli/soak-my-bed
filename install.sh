#!/bin/bash
set -e

echo "======================================="
echo "   Installing Soak My Bed for Klipper  "
echo "======================================="

KLIPPER_DIR="${HOME}/klipper"
KLIPPY_ENV="${HOME}/klippy-env"
PLUGIN_SRC="${HOME}/soak-my-bed/klippy/extras/soak_my_bed.py"
PLUGIN_DEST="${KLIPPER_DIR}/klippy/extras/soak_my_bed.py"

# 1. Verifica che Klipper esista
if [ ! -d "$KLIPPER_DIR" ]; then
    echo "[ERROR] Klipper directory not found at $KLIPPER_DIR"
    exit 1
fi

# 2. Installa le dipendenze Python
echo "[1/3] Installing Python dependencies (this may take a while)..."
${KLIPPY_ENV}/bin/pip install matplotlib scipy numpy pillow

# 3. Collega il plugin a Klipper
echo "[2/3] Linking plugin to Klipper..."
ln -sf "$PLUGIN_SRC" "$PLUGIN_DEST"

# 4. Riavvia Klipper
echo "[3/3] Restarting Klipper service..."
sudo systemctl restart klipper

echo "======================================="
echo " Installation Complete! "
echo " Don't forget to add [soak_my_bed] to your printer.cfg"
echo "======================================="
