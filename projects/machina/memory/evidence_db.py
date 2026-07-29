import importlib.util, os

_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evidence_db.py")
_spec = importlib.util.spec_from_file_location("_machina_edb", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

EvidenceDB = _mod.EvidenceDB
