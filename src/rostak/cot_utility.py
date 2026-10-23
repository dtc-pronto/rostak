"""CoT serialization shared by GPS and PRONTO casualty publishers."""
from datetime import datetime, timezone, timedelta
import math
import xml.etree.ElementTree as ET
import yaml


class CotUtility:
    def __init__(self, config):
        if isinstance(config, dict):
            self.cfg = dict(config)
        else:
            with open(config, encoding='utf-8') as stream:
                self.cfg = yaml.safe_load(stream)
        self.callsign = str(self.cfg.get('callsign', 'ROS2-Robot'))
        self.uid = str(self.cfg.get('uid', 'ros2.callsign')).replace('callsign', self.callsign)
        self.cot_type = self.cfg.get('type', 'a-f-G-E-V')
        self.fix = (0.0, 0.0, 0.0)
        self.triage_vitals = {}
        self.image_url = None
        self.injury_grade = None
        self.iconpath = self.cfg.get('iconpath')

    def set_point(self, point):
        if hasattr(point, 'latitude'):
            point = (point.latitude, point.longitude, point.altitude)
        elif isinstance(point, dict):
            point = (point['latitude'], point['longitude'], point.get('altitude', 0.0))
        lat, lon, alt = (float(value) if value is not None else 0.0 for value in point)
        if not math.isfinite(lat) or not -90 <= lat <= 90:
            raise ValueError('latitude must be finite and between -90 and 90')
        if not math.isfinite(lon) or not -180 <= lon <= 180:
            raise ValueError('longitude must be finite and between -180 and 180')
        self.fix = (lat, lon, alt if math.isfinite(alt) else 0.0)

    def new_status(self, stale_in=300):
        now = datetime.now(timezone.utc)
        stamp = lambda value: value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        event = ET.Element('event', version='2.0', uid=self.uid, type=self.cot_type,
                           how='m-g', time=stamp(now), start=stamp(now),
                           stale=stamp(now + timedelta(seconds=stale_in)))
        lat, lon, alt = self.fix
        ET.SubElement(event, 'point', lat=str(lat), lon=str(lon), hae=str(alt),
                      ce=str(self.cfg.get('radius', 2.0)), le=str(self.cfg.get('height', 2.0)))
        detail = ET.SubElement(event, 'detail')
        ET.SubElement(detail, 'contact', callsign=self.callsign)
        ET.SubElement(detail, 'precisionlocation', geopointsrc='GPS', altsrc='GPS')
        role = self.cfg.get('role', 'Team Member')
        ET.SubElement(detail, '__group', name=self.cfg.get('team', 'Cyan'), role=role)
        # ProntoGUI explicitly reads this detail, not __group.role.
        ET.SubElement(detail, 'userinfo', role=role)
        for key, value in self.triage_vitals.items():
            if value is not None:
                ET.SubElement(detail, key, value=str(value))
        if self.image_url:
            ET.SubElement(detail, 'image_url', value=self.image_url)
        if self.injury_grade is not None:
            ET.SubElement(detail, 'injury_grade', value=str(self.injury_grade))
        if self.iconpath and self.cfg.get('use_custom_icons', False):
            ET.SubElement(detail, 'usericon', iconsetpath=(
                'd226b4c6af085afdc212854fcadc551b2cdb1aeedcfddc4e133dadf101026f78/'
                'PRONTO_Icon/' + self.iconpath))
        return event

    def new_status_msg(self, stale_in=300):
        return ET.tostring(self.new_status(stale_in), encoding='unicode')

    def set_triage_vitals(self, key, value):
        self.triage_vitals[key] = value

    def set_image_url(self, url):
        self.image_url = url

    def set_icon(self, icon):
        self.iconpath = icon
        self.injury_grade = {'noun-person-red.png': 3, 'noun-person-yellow.png': 2,
                             'noun-person-green.png': 1, 'noun-person-black.png': 0}.get(icon)

    def get_config(self):
        return self.cfg
