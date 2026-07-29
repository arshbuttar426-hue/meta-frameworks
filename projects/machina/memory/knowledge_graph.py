import importlib.util, os

_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_graph.py")
_spec = importlib.util.spec_from_file_location("_machina_kg", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

KnowledgeGraph = _mod.KnowledgeGraph
