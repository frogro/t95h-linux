#!/usr/bin/env python3
"""Compare an official target's published kmods with T95H profile configurations.

Read-only static review: does not resolve Kconfig dependencies or prove module
payload, ABI compatibility, autoload, firmware, or hardware functionality.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def config(text):
    result = dict(re.findall(r'^(CONFIG_\w+)=(.*)$', text, re.M))
    result.update({name: 'n' for name in re.findall(r'^# (CONFIG_\w+) is not set$', text, re.M)})
    return result

def recipes(text):
    result = {}
    for block in re.split(r'^Package: ', text, flags=re.M)[1:]:
        name = block.splitlines()[0]
        fields = dict(re.findall(r'^([\w-]+): (.*)$', block, re.M))
        if name.startswith('kmod-'):
            result[name] = fields
    return result

def requirements(text, cfg):
    missing, unknown, disabled_conflicts, expressions = [], [], [], []
    selected = []
    for token in text.split():
        match = re.fullmatch(r'(CONFIG_\w+)(?:=(.*))?', token)
        if not match:
            expressions.append(token)
            continue
        symbol, value = match.groups()
        if value == 'n':
            if cfg.get(symbol) in ('y', 'm'):
                disabled_conflicts.append(symbol)
            continue
        if value not in (None, 'y', 'm'):
            expressions.append(token)
            continue
        selected.append(symbol)
        if symbol not in cfg:
            unknown.append(symbol)
        elif cfg[symbol] not in ('y', 'm'):
            missing.append(symbol)
    return dict(required=sorted(set(selected)), missing=sorted(set(missing)),
                absent_symbols=sorted(set(unknown)),
                disabled_conflicts=sorted(set(disabled_conflicts)),
                expressions=sorted(set(expressions)))

def assess(name, recipe, cfg, providers):
    row = {'package': name, 'advertised_provider': providers.get(name.removeprefix('kmod-'))}
    symbol = row['advertised_provider']
    row['advertised_in_profile'] = bool(symbol and cfg.get('CONFIG_' + symbol) in ('y', 'm'))
    if recipe is None:
        return dict(row, state='recipe_unavailable')
    req = requirements(recipe.get('Kernel-Config', ''), cfg)
    row.update(req)
    row['recipe_dependencies'] = recipe.get('Depends', '')
    row['category'] = recipe.get('Submenu', '')
    if not req['required'] or req['expressions'] or req['absent_symbols']:
        state = 'manual_review'
    elif req['missing']:
        state = 'missing_functions'
    elif req['disabled_conflicts']:
        state = 'config_conflict_review'
    elif not row['advertised_in_profile']:
        state = 'enabled_without_provider'
    else:
        state = 'config_and_provider_present'
    row['state'] = state
    return row

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packageinfo', type=Path, required=True)
    parser.add_argument('--index-dump', type=Path, required=True)
    parser.add_argument('--index-url', required=True)
    parser.add_argument('--upstream-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    metadata = recipes(args.packageinfo.read_text())
    published = sorted(set(re.findall(r'^  - name: (kmod-[\w.+-]+)$', args.index_dump.read_text(), re.M)))
    if not published:
        raise ValueError('No published kmods found in apk adbdump input')
    board = ROOT / 'boards/t95h'
    provider_file = board / 'kernel/package-providers.json'
    providers = json.loads(provider_file.read_text())['config']
    profiles = {}
    for path in sorted((board / 'profiles/kconfig-draft').glob('*.config')):
        cfg = config(path.read_text())
        rows = [assess(name, metadata.get(name), cfg, providers) for name in published]
        profiles[path.stem] = {'config_sha256': digest(path),
            'counts': dict(sorted(Counter(r['state'] for r in rows).items())),
            'advertised_but_requires_review': [r['package'] for r in rows
                if r['advertised_in_profile'] and r['state'] != 'config_and_provider_present'],
            'packages': rows}
    report = {'scope': 'Published OpenWrt 25.12.5 sunxi/cortexa53 kmods versus T95H requested profile configs',
        'upstream_commit': args.upstream_commit, 'index_url': args.index_url,
        'packageinfo_sha256': digest(args.packageinfo), 'index_dump_sha256': digest(args.index_dump),
        'providers_sha256': digest(provider_file), 'published_packages': len(published),
        'limitations': ['Static audit only; presence of symbols is not proof of packaged module files.',
            'Missing/renamed symbols and conditional dependencies need Linux 6.12 versus 7.2 review.',
            'Published for sunxi does not mean applicable to T95H; PCI and other SoC drivers need scope decisions.',
            'Disabled conflicts can reflect deliberate superset profiles; do not disable blindly.',
            'Current t95h-kernel is monolithic; no independent matching kmod feed is established by this audit.'],
        'profiles': profiles}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'published_packages': len(published), 'profiles': {
        k: v['counts'] for k, v in profiles.items()}}, indent=2))

if __name__ == '__main__':
    main()
