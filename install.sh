#!/bin/bash

# Infinite Injector Installation Script for Linux

echo "=========================================="
echo "Infinite Injector - Installation"
echo "=========================================="
echo

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[-] Python 3 is not installed"
    echo "[*] Please install Python 3.7 or later"
    exit 1
fi

echo "[+] Python 3 found: $(python3 --version)"
echo

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "[-] pip3 is not installed"
    echo "[*] Please install pip3"
    exit 1
fi

echo "[+] pip3 found"
echo

# Install dependencies
echo "[*] Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "[+] Dependencies installed successfully"
else
    echo "[-] Failed to install dependencies"
    exit 1
fi

echo

# Make injector executable
chmod +x injector.py

echo "[+] Installation complete!"
echo "[*] Run with: python3 injector.py"
echo
