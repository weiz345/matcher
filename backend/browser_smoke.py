"""Compatibility entrypoint for the current direct-Supabase browser tests."""
import runpy,sys
from pathlib import Path
folder=Path(__file__).resolve().parent.parent/'supabase'
sys.path.insert(0,str(folder))
runpy.run_path(str(folder/'browser_smoke.py'),run_name='__main__')
