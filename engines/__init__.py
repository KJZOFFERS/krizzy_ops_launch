# makes `from engines import rei_dispo_engine, govcon_subtrap_engine` valid
import importlib

rei_dispo_engine = importlib.import_module(".rei_dispo_engine", __name__)
govcon_subtrap_engine = importlib.import_module(".govcon_subtrap_engine", __name__)

__all__ = ["rei_dispo_engine", "govcon_subtrap_engine"]
