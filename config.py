import json
import os

script_path = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_path, "config.json"), "r") as f:
    config = json.load(f)

__all__ = ["config"]
