"""Storage relocation and launcher safety; no real CLI, sockets or original records."""
import json
import os
import subprocess
import sys
from pathlib import Path


def test_external_runtime_paths_do_not_depend_on_launch_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    paths = {name: str(tmp_path / name.lower()) for name in (
        'WITNESSTRACE_DATA_DIR', 'WITNESSTRACE_OUTPUTS_DIR', 'WITNESSTRACE_WORK_DIR')}
    env.update(paths, PYTHONPATH=str(root))
    code = '''import json
from pathlib import Path
import app, case_store
print(json.dumps({'data': str(case_store.DATA), 'outputs': str(app.OUTPUTS),
                  'work': str(app.WORK), 'static_ok': (app.STATIC/'index.html').is_file(),
                  'database_ok': case_store.DB.is_file()}))
'''
    run = subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env=env,
                         text=True, capture_output=True, timeout=20)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['data'] == paths['WITNESSTRACE_DATA_DIR']
    assert result['outputs'] == paths['WITNESSTRACE_OUTPUTS_DIR']
    assert result['work'] == paths['WITNESSTRACE_WORK_DIR']
    assert result['static_ok'] and result['database_ok']


def test_launcher_rejects_protected_ports_before_starting_server(tmp_path):
    launcher = Path(__file__).resolve().parents[1] / 'start.sh'
    for port in ('8000', '8001', '08000', '08001'):
        env = os.environ.copy()
        env['WITNESSTRACE_PORT'] = port
        run = subprocess.run(['bash', str(launcher)], cwd=tmp_path, env=env,
                             text=True, capture_output=True, timeout=5)
        assert run.returncode == 2
        assert 'other than 8000 or 8001' in run.stderr
