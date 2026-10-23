import math
import xml.etree.ElementTree as ET
import pytest
from rostak.cot_utility import CotUtility


def test_gps_identity_coordinates_and_times():
    util = CotUtility({'callsign': 'Robot & One', 'uid': 'ros.callsign'})
    util.set_point((39.0, -77.0, 100.0))
    event = ET.fromstring(util.new_status_msg(300))
    assert event.attrib['uid'] == 'ros.Robot & One'
    assert event.find('point').attrib['lat'] == '39.0'
    assert event.find('point').attrib['lon'] == '-77.0'
    assert event.find('detail/contact').attrib['callsign'] == 'Robot & One'
    assert event.attrib['stale'] > event.attrib['time']


def test_casualty_contract_and_zero_priority():
    util = CotUtility({'callsign': 'Alpha-1', 'role': 'Casualty'})
    util.set_triage_vitals('heart_rate', 0)
    util.set_icon('noun-person-black.png')
    for _ in range(2):
        event = ET.fromstring(util.new_status_msg())
        assert event.find('detail/userinfo').attrib['role'] == 'Casualty'
        assert event.find('detail/heart_rate').attrib['value'] == '0'
        assert event.find('detail/injury_grade').attrib['value'] == '0'


@pytest.mark.parametrize('point', [(91, 0, 0), (0, 181, 0), (math.nan, 0, 0)])
def test_invalid_gps_is_rejected(point):
    with pytest.raises(ValueError):
        CotUtility({}).set_point(point)


def test_unknown_altitude_is_serialized_as_finite():
    util = CotUtility({})
    util.set_point((39, -77, math.nan))
    assert util.new_status().find('point').attrib['hae'] == '0.0'
