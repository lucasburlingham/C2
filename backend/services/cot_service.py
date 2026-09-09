import time
import xml.etree.ElementTree as ET
import socket
import os

def generate_pli_cot(callsign: str, lat: float, lon: float, hae: float = 0.0, speed: float = 0.0, course: float = 0.0, extra: dict = None) -> str:
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
    # attach any extra metadata into the detail element
    if extra:
        try:
            # If there's an RTSP URL, add as a link element
            rtsp = extra.get('rtsp_url') or extra.get('rtsp')
            if rtsp:
                ET.SubElement(detail, 'link', {'rel': 'rtsp', 'href': str(rtsp)})
            # add other simple key/value pairs as simple child elements
            for k, v in extra.items():
                if k in ('rtsp_url', 'rtsp'):
                    continue
                try:
                    child = ET.SubElement(detail, k)
                    child.text = str(v)
                except Exception:
                    pass
        except Exception:
            pass
    
    return ET.tostring(event, encoding="utf-8", method="xml").decode("utf-8")


def send_pli_multicast(callsign: str, lat: float, lon: float, hae: float = 0.0, speed: float = 0.0, course: float = 0.0, rtsp_url: str = None) -> dict:
    """Generate a PLI CoT message and send it to a configurable multicast address/port.

    Environment variables:
    - COT_MULTICAST_ADDR (default: 239.255.0.1)
    - COT_MULTICAST_PORT (default: 6969)
    - COT_TTL (default: 1)
    """
    addr = os.environ.get('COT_MULTICAST_ADDR', '239.255.0.1')
    port = int(os.environ.get('COT_MULTICAST_PORT', '6969'))
    ttl = int(os.environ.get('COT_TTL', '1'))
    try:
        extra = None
        if rtsp_url:
            extra = {'rtsp_url': rtsp_url}
        xml = generate_pli_cot(callsign, lat, lon, hae, speed, course, extra=extra)
        data = xml.encode('utf-8')
        # create UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            # set TTL for multicast
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            # allow reuse
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.sendto(data, (addr, port))
        return {'ok': True, 'addr': addr, 'port': port}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
