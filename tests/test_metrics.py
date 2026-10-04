import pytest
from src.metrics import calculate_fleet_oee, calculate_oee_by_plant, calculate_oee_by_asset, calculate_mtbf_mttr, calculate_total_downtime_cost

def test_fleet_oee():
    oee_data = calculate_fleet_oee()
    assert 0.0 < oee_data["availability"] <= 1.0
    assert 0.0 < oee_data["performance"] <= 1.0
    assert 0.0 < oee_data["quality"] <= 1.0
    assert 0.0 < oee_data["oee"] <= 1.0
    
    # Check OEE mathematical consistency: OEE = A * P * Q
    expected_oee = round(oee_data["availability"] * oee_data["performance"] * oee_data["quality"], 4)
    assert abs(oee_data["oee"] - expected_oee) <= 0.001

def test_oee_by_plant():
    df_plants = calculate_oee_by_plant()
    assert len(df_plants) == 3
    assert "plant_id" in df_plants.columns
    assert "oee" in df_plants.columns
    for oee in df_plants["oee"]:
        assert 0.5 <= oee <= 1.0

def test_mtbf_mttr():
    reliability = calculate_mtbf_mttr()
    assert reliability["total_failures"] >= 15
    assert reliability["mtbf_hours"] > 100.0
    assert 1.0 <= reliability["mttr_hours"] <= 12.0

def test_downtime_cost():
    cost = calculate_total_downtime_cost()
    assert cost > 100000.0
