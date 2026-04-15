"""Runner script - loads .env and starts the bot."""

import os
import sys
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Look for .env in bot directory first, then project root
    bot_dir = Path(__file__).resolve().parent
    project_root = bot_dir.parent

    env_file = bot_dir / ".env"
    if not env_file.exists():
        env_file = project_root / ".env.bot"
    if not env_file.exists():
        env_file = project_root / ".env"

    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from: {env_file}")
except ImportError:
    pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.main import main

if __name__ == "__main__":
    main()
