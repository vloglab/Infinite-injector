"""
Configuration file for Infinite Injector
"""

# Script to inject and execute
INJECT_SCRIPT = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()'

# Timeout for script execution (seconds)
SCRIPT_TIMEOUT = 10

# Roblox process names to search for
ROBLOX_PROCESSES = [
    "RobloxPlayerBeta",
    "roblox-player",
    "sober",
    "wine",
    "proton",
    "RobloxStudio",
]

# Infinite Yield script URL
INFINITE_YIELD_URL = "https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"

# Debug mode
DEBUG = False

# Maximum retry attempts
MAX_RETRIES = 3

# Retry delay (seconds)
RETRY_DELAY = 1
