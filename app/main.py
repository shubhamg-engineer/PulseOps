"""
PulseOps Streamlit Application Entrypoint.
Provides full backwards compatibility for 'streamlit run app/main.py'
by invoking 'app/streamlit_app.py'.
"""
import sys
from pathlib import Path
import runpy

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

target_app = Path(__file__).parent / "streamlit_app.py"
runpy.run_path(str(target_app), run_name="__main__")
