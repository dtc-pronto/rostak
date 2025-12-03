from datetime import datetime, timezone, timedelta
import uuid
import xml.etree.ElementTree as ET
import yaml

ISO_8601_UTC = "%Y-%m-%dT%H:%M:%S.%fZ"

class CotUtility:

    def __init__(self, config_path: str, **kwargs):
        
        with open(config_path) as config:
            self.cfg = yaml.safe_load(config)
        
        self.uid = self.cfg["uid"].replace("callsign", self.cfg["callsign"])
        self.cot_type = 'a-n-x'
        self.callsign = self.cfg["callsign"]
        self.team = self.cfg['team']
        self.fix = {"latitude": 0.0, "longitude": 0.0, "altitude":0.0}

        # added code:
        self.iconpath = self.cfg["iconpath"]

        self.triage_vitals = {
            "heart_rate": None,
            "respiration_rate": None,
            "severe_hemorrhage": None,
            "respiratory_distress": None,
            "trauma_head": None,
            "trauma_torso": None,
            "trauma_upper_extremities": None,
            "trauma_lower_extremities": None,
            "alertness_verbal": None,
            "alertness_motor": None,
            "alertness_ocular": None
        }
        self.image_url = None
        self.triage_flag = False

        self.usericon = None
        self.injury_grade = None

        # added code end

        try:
            self.object_detect_str = kwargs['object_str']
            self.parse_str()
        except KeyError:
            self.cot_type = self.cfg["type"]


    # new functions
    def parse_str(self): 
        detection_list = self.object_detect_str.split(',')
        hfu = 'n'

        for cot_info in detection_list:
            cot_info = cot_info.replace(' ','')
            if list(cot_info)[0] == 'a' and list(cot_info)[1] == '-':
                self.cot_type = cot_info
            elif cot_info.lower() == 'hostile':
                hfu = 'h'
                self.team = 'red'
            elif cot_info.lower() == 'friendly':
                hfu = 'f'
                self.team = 'green'
            elif cot_info.lower() == 'unknown':
                hfu = 'u'
                self.team = 'orange'
            elif cot_info.lower() == 'neutral':
                self.team = 'blue'
                continue
            else:
                self.callsign = cot_info

            self.uid = self.callsign
            temp = list(self.cot_type)
            temp[2] = hfu
            self.cot_type = ''.join(temp)

    def new_status(self, stale_in = 60) -> ET.Element:
        cot = self.new_cot(stale_in)

        detail = cot.find("detail")

        ET.SubElement(detail, "contact", attrib={
            "callsign": self.callsign,
            "endpoint": "*:-1:stcp"
        })
        
        ET.SubElement(detail, "precisionlocation", attrib={
            "geopointsrc": "GPS",
            "altsrc": "GPS"
        })
        
        ET.SubElement(detail, "__group", attrib={
            "name": self.team,
            "role": self.cfg["role"]
        })
        
        ET.SubElement(detail, "takv", attrib={
            "platform": "pronto/rostak"
        })

        #added code to treat triage.
        for key, value in self.triage_vitals.items():
            if value is not None:
                ET.SubElement(detail, key, attrib={"value": str(value)})
                self.triage_vitals[key] = None  # Reset after adding to detail

        ET.SubElement(detail, "usericon", attrib={"iconsetpath": "d226b4c6af085afdc212854fcadc551b2cdb1aeedcfddc4e133dadf101026f78/"
        "PRONTO_Icon/" + self.iconpath
        })

        if self.image_url is not None:
            ET.SubElement(detail, "image_url", attrib={"value": self.image_url})

        if self.injury_grade:
            ET.SubElement(detail, "injury_grade", attrib={"value": str(self.injury_grade)})
        else:
            ET.SubElement(detail, "injury_grade", attrib={"value": "0"})
        self.injury_grade = None  # Reset after adding to detail
    

        return cot

    def set_triage_vitals(self, key: str, value):
        """
        Set a triage vital value.
        :param key: The key of the vital to set.
        :param value: The value to set for the vital.
        """
        if key in self.triage_vitals:
            self.triage_vitals[key] = value
        else:
            raise KeyError(f"Invalid triage vital key: {key}")

    def set_image_url(self, url: str):
        """
        Set the image URL for the user.
        :param url: The URL of the image.
        """
        self.image_url = url
        self.cfg["image_url"] = url
        
    def set_icon(self, icon: str):
        """
        Set the icon for the user.
        :param icon: The path to the icon file.
        """
        self.iconpath = icon
        self.cfg["iconpath"] = icon
        
        # set priority of casualty
        self.injury_grade = 3 if icon == "noun-person-red.png" else 2 if icon == "noun-person-yellow.png" else 1 if icon == "noun-person-green.png" else 0 if icon == "noun-person-black.png" else 0

    # end of new functions

    def new_cot(self, stale_in = 60) -> ET.Element:
        cot = ET.Element("event", attrib=self.header(stale_in))
        
        ET.SubElement(cot, "point", attrib=self.current_point())
        ET.SubElement(cot, "detail")
        
        return cot

    def new_status_msg(self, stale_in = 60) -> str:
        return ET.tostring(
            self.new_status(stale_in)
        ).decode()
    
    def new_chat_msg(self, stale_in = 60) -> str:
        return ET.tostring(
            self.new_chat(stale_in)
        ).decode()

    def new_chat(self, text, stale_in = 84600):
        msg_id = str(uuid.uuid4())
        
        cot = self.new_cot(stale_in)
        cot.set("type", "b-t-f")

        detail = cot.find("detail")
        
        chat = ET.SubElement(detail, "__chat", {
            "parent": "",
            "groupOwner": "false",
            "messageId": msg_id,
            "chatroom": self.cfg["team"],
            "id": self.cfg['team'],
            "senderCallsign": self.cfg['callsign']
        })
        
        remarks = ET.SubElement(detail, "remarks", {
            "source": "",
            "time": ""
        })
        remarks.text = text
        
        ET.SubElement(detail, "link", {
            "uid": self.cfg['uid'],
            "type": self.cfg['type'],
            "relation": "p-p"
        })
        
        return cot

    def set_point(self, fix: dict):
        self.fix = fix
    
    def current_point(self):
        return {
            "lat": str(self.fix['latitude']),
            "lon": str(self.fix['longitude']),
            "hae": str(self.fix['altitude']),
            "ce": str(self.cfg['radius']),
            "le": str(self.cfg['height'])
        }
    
    def header(self, stale_in):
        time = datetime.now(timezone.utc)
        return {
            "version": "2.0",
            "uid": self.cfg['uid'],
            "type": self.cfg['type'],
            "how": "m-g",
            "time": time.strftime(ISO_8601_UTC),
            "start": time.strftime(ISO_8601_UTC),
            "stale": (time + timedelta(seconds=stale_in)).strftime(ISO_8601_UTC)
        }

    def get_config(self):
        return self.cfg