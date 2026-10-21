#!/usr/bin/env python3
"""Run the unit tests, one process per test module, in parallel.

Usage: python3 run.py [--coverage] [-j N] [name ...]

  name        run only the test modules whose name contains it (run.py config toml)
  -j N        processes at once (default: the number of CPUs)
  --coverage  run each module under coverage.py, combine the data and report;
              fails below fail_under in the repository's pyproject.toml

unittest has no parallel mode, so each module gets its own process; every test
uses its own temporary directory and port, so modules can run side by side.
Exit code: 0 when every module passes (and coverage meets its threshold),
1 when one fails, 2 on a usage error.
"""

import concurrent.futures
import glob
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def repo_root():
    """The checkout's root, the nearest folder above with a pyproject.toml, or None."""
    d = HERE
    while True:
        if os.path.isfile(os.path.join(d, 'pyproject.toml')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def run_module(name, coverage, root):
    """Run one test module in its own process; a dict with its result and output."""
    env = dict(os.environ, PYTHONPATH=HERE + os.pathsep + os.environ.get('PYTHONPATH', ''), PYTHONDONTWRITEBYTECODE='1')
    cmd = [sys.executable, '-m', 'unittest', '-q', name]
    if coverage:
        env['COVERAGE_FILE'] = os.path.join(root, '.coverage')
        cmd = [sys.executable, '-m', 'coverage', 'run', '--parallel-mode', '-m', 'unittest', '-q', name]
    start = time.monotonic()
    p = subprocess.run(cmd, cwd=root or HERE, env=env, capture_output=True, text=True)
    out = p.stdout + p.stderr
    ran = re.search(r'Ran (\d+) test', out)
    return {'name': name, 'ok': p.returncode == 0, 'tests': int(ran.group(1)) if ran else 0,
            'seconds': time.monotonic() - start, 'output': out}


def parse(argv):
    """(coverage, jobs, names), or an error message."""
    coverage, jobs, names = False, os.cpu_count() or 4, []
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == '--coverage':
            coverage = True
        elif a == '-j':
            if not args or not args[0].isdigit() or int(args[0]) < 1:
                return '-j needs a positive number'
            jobs = int(args.pop(0))
        elif a.startswith('-'):
            return f'unknown option {a}'
        else:
            names.append(a)
    return coverage, jobs, names


def main(argv):
    if argv and argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    parsed = parse(argv)
    if isinstance(parsed, str):
        print(f'run.py: {parsed}', file=sys.stderr)
        return 2
    coverage, jobs, names = parsed
    root = repo_root()
    if coverage and not root:
        print('run.py: --coverage needs a checkout of the repository (no pyproject.toml found)', file=sys.stderr)
        return 2
    modules = sorted(os.path.basename(f)[:-3] for f in glob.glob(os.path.join(HERE, 'test_*.py')))
    if names:
        modules = [m for m in modules if any(n in m for n in names)]
    if not modules:
        print('run.py: no test modules matched', file=sys.stderr)
        return 2
    if coverage:
        for f in glob.glob(os.path.join(root, '.coverage*')):
            os.remove(f)

    start = time.monotonic()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for r in pool.map(lambda m: run_module(m, coverage, root), modules):
            results.append(r)
            print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['name']:<28} {r['tests']:>3} tests  {r['seconds']:5.1f}s", flush=True)
    failed = [r for r in results if not r['ok']]
    for r in failed:
        print(f"\n===== {r['name']} =====\n{r['output']}")
    print(f"\n{len(modules)} module(s), {sum(r['tests'] for r in results)} test(s), {len(failed)} failed, "
          f"{time.monotonic() - start:.1f}s with {min(jobs, len(modules))} process(es)", flush=True)

    code = 1 if failed else 0
    if coverage:
        env = dict(os.environ, COVERAGE_FILE=os.path.join(root, '.coverage'))
        subprocess.run([sys.executable, '-m', 'coverage', 'combine', '-q'], cwd=root, env=env, check=False)
        report = subprocess.run([sys.executable, '-m', 'coverage', 'report'], cwd=root, env=env)
        code = code or (1 if report.returncode else 0)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
