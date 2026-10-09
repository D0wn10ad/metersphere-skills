import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'skills' / 'scripts' / 'ms_batch.py'


def run_batch(args, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def test_old_3arg_still_runs(tmp_path):
    # minimal payload with projectId and templateId via env
    payload = [{
        "projectId": "p1",
        "name": "t1",
        "templateId": "tpl1",
        "versionId": "v1"
    }]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    rc, out, err = run_batch(['functional-cases', str(f)], env={'METERSPHERE_BASE_URL': 'http://127.0.0.1:9', 'METERSPHERE_ACCESS_KEY': 'a', 'METERSPHERE_SECRET_KEY': 'b'})
    # will fail to connect but should parse/attempt (not die on argc)
    assert rc != 0  # connection error expected
    # should not be usage error
    assert '用法' not in err


def test_new_flagged_invocation_runs(tmp_path):
    payload = [{
        "projectId": "p1",
        "name": "t1",
        "templateId": "tpl1",
        "versionId": "v1"
    }]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    rc, out, err = run_batch(['functional-cases', str(f), '--attach-file-id', 'fid1'], env={'METERSPHERE_BASE_URL': 'http://127.0.0.1:9', 'METERSPHERE_ACCESS_KEY': 'a', 'METERSPHERE_SECRET_KEY': 'b'})
    assert rc != 0
    assert '用法' not in err


def test_bodies_differ_only_by_relatefilemetaids(tmp_path):
    # simulate by checking that with flag we inject relateFileMetaIds
    payload = [{
        "projectId": "p1",
        "name": "t1",
        "templateId": "tpl1"
    }]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    # call with flag - but we can't see curl body directly; instead test via create_functional_cases
    import importlib.util
    spec = importlib.util.spec_from_file_location('msb', SCRIPT)
    msb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(msb)
    # monkey patch subprocess/curl to capture
    captured = []
    def fake_run(cmd, capture_output=True, text=True, timeout=30, input=None, **kwargs):
        captured.append(cmd)
        class R:
            stdout = json.dumps({'success': True}).encode('utf-8')
            returncode = 0
        return R()
    import subprocess as sp
    orig = sp.run
    import os as _os
    orig_unlink = _os.unlink
    def fake_unlink(p, *args, **kwargs):
        pass
    try:
        _os.unlink = fake_unlink
        sp.run = fake_run
        msb.create_functional_cases([{"projectId": "p1", "name": "t1", "templateId": "tpl1"}])
        body1 = None
        # find -F request
        for c in captured:
            for i, a in enumerate(c):
                if a.startswith('request=@'):
                    fname = a[9:]
                    if ';' in fname:
                        fname = fname.split(';')[0]
                    body1 = Path(fname).read_text()
                    break
        captured.clear()
        msb.create_functional_cases([{"projectId": "p1", "name": "t1", "templateId": "tpl1"}], attach_file_id='fid1')
        body2 = None
        for c in captured:
            for i, a in enumerate(c):
                if a.startswith('request=@'):
                    fname = a[9:]
                    if ';' in fname:
                        fname = fname.split(';')[0]
                    body2 = Path(fname).read_text()
                    break
        d1 = json.loads(body1)
        d2 = json.loads(body2)
        # remove relateFileMetaIds
        d1.pop('relateFileMetaIds', None)
        d2.pop('relateFileMetaIds', None)
        assert d1 == d2
        assert json.loads(body2).get('relateFileMetaIds') == ['fid1']
    finally:
        _os.unlink = orig_unlink
        sp.run = orig


def test_templateid_absent_env_unset(tmp_path):
    payload = [{"projectId": "p1", "name": "t1"}]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    rc, out, err = run_batch(['functional-cases', str(f)], env={'METERSPHERE_BASE_URL': 'http://127.0.0.1:9', 'METERSPHERE_ACCESS_KEY': 'a', 'METERSPHERE_SECRET_KEY': 'b'})
    assert rc == 1
    assert 'templateId' in err or 'templateId' in out


def test_element_without_projectid(tmp_path):
    payload = [{"name": "t1", "templateId": "tpl1"}]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    rc, out, err = run_batch(['functional-cases', str(f)], env={'METERSPHERE_BASE_URL': 'http://127.0.0.1:9', 'METERSPHERE_ACCESS_KEY': 'a', 'METERSPHERE_SECRET_KEY': 'b'})
    assert rc == 1
    assert 'projectId' in err or 'projectId' in out


def test_versionid_never_in_outgoing_body(tmp_path):
    payload = [{"projectId": "p1", "name": "t1", "templateId": "tpl1"}]
    f = tmp_path / 'cases.json'
    f.write_text(json.dumps(payload, ensure_ascii=False))
    import importlib.util
    spec = importlib.util.spec_from_file_location('msb', SCRIPT)
    msb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(msb)
    captured = []
    def fake_run(cmd, capture_output=True, text=True, timeout=30, input=None, **kwargs):
        captured.append(cmd)
        class R:
            stdout = json.dumps({'success': True}).encode('utf-8')
            returncode = 0
        return R()
    import subprocess as sp
    orig = sp.run
    import os as _os
    orig_unlink = _os.unlink
    saved = []
    def fake_unlink(p):
        saved.append(p)
        # don't actually delete so we can read
        pass
    try:
        _os.unlink = fake_unlink
        sp.run = fake_run
        msb.create_functional_cases([{"projectId": "p1", "name": "t1", "templateId": "tpl1"}])
        body = None
        for c in captured:
            for i, a in enumerate(c):
                if a.startswith('request=@'):
                    fname = a[9:]
                    if ';' in fname:
                        fname = fname.split(';')[0]
                    body = Path(fname).read_text()
                    break
        d = json.loads(body)
        assert 'versionId' not in d
    finally:
        _os.unlink = orig_unlink
        sp.run = orig
