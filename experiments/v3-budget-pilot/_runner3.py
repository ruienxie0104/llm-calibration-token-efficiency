#!/usr/bin/env python3
"""Runner for B (confidence test)."""
import subprocess, os
env = os.environ.copy()
env["OLLAMA_API_KEY"] = "7d30048207d541afa72fceb4a639852f._kuPlqyToP_iFGGYEek_UIcA"
env["OLLAMA_API_URL"] = "https://ollama.com/api/chat"
subprocess.run(["uv", "run", "python3", "experiments/v3-budget-pilot/run_confidence_test.py"],
    cwd="/Users/ryan/Projects/llm-calibration-token-efficiency", env=env)