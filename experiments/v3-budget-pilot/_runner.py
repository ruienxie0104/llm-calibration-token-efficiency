#!/usr/bin/env python3
"""Run the pilot script with env vars set programatically."""
import os
import subprocess
import sys

os.environ["OLLAMA_API_KEY"] = "7d30048207d541afa72fceb4a639852f._kuPlqyToP_iFGGYEek_UIcA"
os.environ["OLLAMA_API_URL"] = "https://ollama.com/api/chat"

result = subprocess.run(
    [sys.executable, "experiments/v3-budget-pilot/run_pilot.py"],
    cwd="/Users/ryan/Projects/llm-calibration-token-efficiency",
)
sys.exit(result.returncode)