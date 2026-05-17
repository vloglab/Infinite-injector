# Infinite Injector - Roblox Linux

A Linux-based injector for Roblox that executes the Infinite Yield script on Sober Roblox.

## Features

- Automatic script injection for Roblox on Linux
- Executes Infinite Yield loadstring from raw GitHub source
- Simple command-line interface
- Works with Sober (Roblox Linux wrapper)

## Prerequisites

- Python 3.7+
- Roblox/Sober installed on Linux
- curl or wget

## Installation

```bash
git clone https://github.com/vloglab/Infinite-injector.git
cd Infinite-injector
pip install -r requirements.txt
```

## Usage

```bash
python injector.py
```

The injector will:
1. Detect running Roblox processes
2. Inject the Infinite Yield script
3. Execute the loadstring on Sober Roblox

## Script

The injector executes:
```lua
loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()
```

## License

MIT

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with Roblox's Terms of Service.
