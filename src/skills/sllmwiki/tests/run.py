#!/usr/bin/env python3
"""Run the unit tests in parallel: one process per test module.

Usage: python3 run.py [--coverage] [-j N] [name ...]

  name        run only the test modules whose name contains it (e.g. pdf, wiki_check)
  -j N        processes at once (default: the number of CPUs)
  --coverage  run each process under coverage.py (parallel mode), then combine
              the data and report; fails below fail_under in pyproject.toml.
              Needs `coverage[toml]` and a checkout of the repository (it reads
              the repository's pyproject.toml).

Standard library only (unittest has no parallel mode). Every test uses its own
temporary directory and ports, so modules can run side by side. Exit code: 0
when every module passes (and coverage meets the threshold), 1 otherwise.
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
    """The checkout's root (the directory with pyproject.toml), or None for an installed skill."""
    d = HERE
    while True:
        if os.path.isfile(os.path.join(d, 'pyproject.toml')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def run_module(name, coverage, root):
    env = dict(os.environ, PYTHONPATH=HERE + os.pathsep + os.environ.get('PYTHONPATH', ''), PYTHONDONTWRITEBYTECODE='1')
    cmd = [sys.executable, '-m', 'unittest', '-q', name]
    if coverage:
        env['COVERAGE_FILE'] = os.path.join(root, '.coverage')
        cmd = [sys.executable, '-m', 'coverage', 'run', '--parallel-mode', '-m', 'unittest', '-q', name]
    start = time.monotonic()
    p = subprocess.run(cmd, cwd=root or HERE, env=env, capture_output=True, text=True)
    out = p.stdout + p.stderr
    ran = re.search(r'Ran (\d+) test', out)
    xfail = re.search(r'expected failures=(\d+)', out)
    return {'name': name, 'ok': p.returncode == 0, 'tests': int(ran.group(1)) if ran else 0,
            'xfail': int(xfail.group(1)) if xfail else 0, 'seconds': time.monotonic() - start, 'output': out}


def main(argv):
    coverage, jobs, names = False, os.cpu_count() or 4, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--coverage':
            coverage = True
        elif a == '-j' and i + 1 < len(argv) and argv[i + 1].isdigit():
            i += 1
            jobs = max(1, int(argv[i]))
        elif a in ('-h', '--help'):
            print(__doc__)
            return 0
        elif a.startswith('-'):
            print(f'run.py: unknown option {a}', file=sys.stderr)
            return 2
        else:
            names.append(a)
        i += 1

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
        futures = [pool.submit(run_module, m, coverage, root) for m in modules]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            results.append(r)
            print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['name']:<28} {r['tests']:>3} tests  {r['seconds']:5.1f}s", flush=True)

    failed = [r for r in results if not r['ok']]
    for r in sorted(failed, key=lambda r: r['name']):
        print(f"\n===== {r['name']} =====\n{r['output']}")
    total = sum(r['tests'] for r in results)
    xfail = sum(r['xfail'] for r in results)
    print(f"\n{len(modules)} module(s), {total} test(s){f', {xfail} expected failure(s)' if xfail else ''}, "
          f"{len(failed)} module(s) failed, {time.monotonic() - start:.1f}s with {min(jobs, len(modules))} process(es)", flush=True)

    code = 1 if failed else 0
    if coverage:
        env = dict(os.environ, COVERAGE_FILE=os.path.join(root, '.coverage'))
        subprocess.run([sys.executable, '-m', 'coverage', 'combine', '-q'], cwd=root, env=env, check=False)
        report = subprocess.run([sys.executable, '-m', 'coverage', 'report'], cwd=root, env=env)
        code = code or (1 if report.returncode else 0)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
