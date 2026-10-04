from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def test_shell_smoke():
    app_file = BASE_DIR / "app" / "streamlit_app.py"
    at = AppTest.from_file(str(app_file), default_timeout=30)
    at.run()
    assert not at.exception, f"App shell threw exception: {at.exception}"

def test_page_1_fleet_command_center():
    page_file = BASE_DIR / "app" / "pages" / "1_Fleet_Command_Center.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 1 threw exception: {at.exception}"

def test_page_2_alert_queue():
    page_file = BASE_DIR / "app" / "pages" / "2_Alert_Queue.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 2 threw exception: {at.exception}"

def test_page_3_asset_drilldown():
    page_file = BASE_DIR / "app" / "pages" / "3_Asset_Drilldown.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 3 threw exception: {at.exception}"

def test_page_4_ask_pulseops():
    page_file = BASE_DIR / "app" / "pages" / "4_Ask_PulseOps.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 4 threw exception: {at.exception}"

def test_page_5_oee_and_impact():
    page_file = BASE_DIR / "app" / "pages" / "5_OEE_and_Impact.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 5 threw exception: {at.exception}"

def test_page_6_work_orders():
    page_file = BASE_DIR / "app" / "pages" / "6_Work_Orders.py"
    at = AppTest.from_file(str(page_file), default_timeout=30)
    at.run()
    assert not at.exception, f"Page 6 threw exception: {at.exception}"
