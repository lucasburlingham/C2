import time
import xml.etree.ElementTree as ET

def generate_pli_cot(callsign: str, lat: float, lon: float, hae: float = 0.0, speed: float = 0.0, course: float = 0.0) -> str:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 60))
    
    event = ET.Element("event", {
        "version": "2.0",
        "uid": f"VEHICLE-C2-{callsign}",
        "type": "a-f-G-U-C",
        "time": now,
        "start": now,
        "stale": stale,
        "how": "m-g"
    })
    
    point = ET.SubElement(event, "point", {
        "lat": str(lat),
        "lon": str(lon),
        "hae": str(hae),
        "ce": "5.0",
        "le": "5.0"
    })
    
    detail = ET.SubElement(event, "detail")
    ET.SubElement(detail, "contact", {"callsign": callsign})
    ET.SubElement(detail, "track", {"course": str(course), "speed": str(speed)})
    
    return ET.tostring(event, encoding="utf-8", method="xml").decode("utf-8")
