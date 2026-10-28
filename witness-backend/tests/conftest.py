"""Never write fixture jobs/cases into the user's real SQLite database."""
import sys
import os
import tempfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# Isolate even import-time app initialization, before any per-test fixture runs.
_bootstrap=tempfile.TemporaryDirectory(prefix='witnesstrace-tests-')
os.environ['WITNESSTRACE_DATA_DIR']=_bootstrap.name
os.environ['WITNESSTRACE_OUTPUTS_DIR']=str(Path(_bootstrap.name)/'outputs')
os.environ['WITNESSTRACE_WORK_DIR']=str(Path(_bootstrap.name)/'work')
import case_store
case_store.DATA=Path(_bootstrap.name)
case_store.DB=case_store.DATA/'witness.sqlite3'

@pytest.fixture(autouse=True)
def isolated_case_database(tmp_path,monkeypatch):
    monkeypatch.setattr(case_store,'DATA',tmp_path/'data')
    monkeypatch.setattr(case_store,'DB',tmp_path/'data/witness.sqlite3')
    case_store.initialize()
