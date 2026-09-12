"""Verify the first OpenWrt router extension before advertising kmod providers."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'boards/t95h/kernel/base-module-contract.json'

def load():
    return json.loads(CONTRACT.read_text())

def read_config(text):
    return dict(re.findall(r'^CONFIG_(\w+)=(.*)$', text, re.M))

def verify(config, module_root=None, builtin_file=None, contract=None):
    contract = contract or load()
    missing = [s for s in contract['required_config'] if config.get(s) not in ('y', 'm')]
    if missing:
        raise ValueError('Missing router base configuration: ' + ', '.join(missing))
    result = {}
    if module_root is not None:
        modules = {p.name.removesuffix('.ko') for p in Path(module_root).rglob('*.ko')}
        builtins = {Path(line).name.removesuffix('.ko') for line in Path(builtin_file).read_text().splitlines()}
    for package, requirement in contract['providers'].items():
        missing = [s for s in requirement['symbols'] if config.get(s) not in ('y', 'm')]
        if missing:
            raise ValueError(package + ': missing configuration ' + ', '.join(missing))
        if module_root is not None:
            for symbol, names in requirement['objects'].items():
                expected = builtins if config.get(symbol) == 'y' else modules
                absent = sorted(set(names) - expected)
                if absent:
                    raise ValueError(package + ': missing built payload for ' + symbol + ': ' + ', '.join(absent))
        result[package] = requirement['symbols'][0]
    return result
