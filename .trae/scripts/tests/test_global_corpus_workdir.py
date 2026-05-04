import importlib.util
import os
import unittest
from pathlib import Path


SCRIPTS = Path("/workspace/Obsidian-Eg/.trae/scripts")


def load_module(filename: str, module_name: str):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GlobalCorpusWorkdirTest(unittest.TestCase):
    def test_default_work_dir_is_data_user_work(self):
        old = os.environ.pop("GLOBAL_CORPUS_WORK_DIR", None)
        try:
            mod = load_module("global_corpus_workdir.py", "global_corpus_workdir_default")
            self.assertEqual(mod.WORK_DIR, Path("/data/user/work"))
            self.assertEqual(mod.work_path("a.json"), Path("/data/user/work/a.json"))
        finally:
            if old is not None:
                os.environ["GLOBAL_CORPUS_WORK_DIR"] = old

    def test_env_overrides_work_dir(self):
        old = os.environ.get("GLOBAL_CORPUS_WORK_DIR")
        os.environ["GLOBAL_CORPUS_WORK_DIR"] = "/workspace/.trae/work"
        try:
            mod = load_module("global_corpus_workdir.py", "global_corpus_workdir_env")
            self.assertEqual(mod.WORK_DIR, Path("/workspace/.trae/work"))
            self.assertEqual(mod.work_path("x.json"), Path("/workspace/.trae/work/x.json"))
        finally:
            if old is None:
                os.environ.pop("GLOBAL_CORPUS_WORK_DIR", None)
            else:
                os.environ["GLOBAL_CORPUS_WORK_DIR"] = old


if __name__ == "__main__":
    unittest.main()
