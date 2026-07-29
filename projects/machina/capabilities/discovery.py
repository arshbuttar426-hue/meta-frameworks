import importlib.util, os

_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "discovery.py")
_spec = importlib.util.spec_from_file_location("_machina_discovery", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

auto_discover = _mod.auto_discover
