"""Fixed offline worker; called in isolated Python mode by circuit.py."""
import importlib.util
from pathlib import Path
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    source, project, output = map(Path, sys.argv[1:])
    model = load(source / 'engine/spatial_model.py', 'ark_spatial_model')
    renderer = load(source / 'engine/spatial_renderer.py', 'ark_spatial_renderer')
    audio, metrics = renderer.render_project(model.SpatialProject.load_json(str(project)))
    renderer.export_wav(str(output), audio, metrics['sample_rate'])
