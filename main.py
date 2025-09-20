#!/usr/bin/env python3
"""
Main entry point for Telegram bot with OpenAI Realtime API.
"""

import asyncio
import sys
from src.app import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Application interrupted")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)