"""Run with blender [--background] --python bootstrap.py -- --config /path/config.json."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_codex.common import load_config
from blender_codex.bridge import start

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
BRIDGE = start(load_config(args.config))
