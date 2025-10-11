import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO

EPG_URLS = [
    "https://github.com/globetvapp/epg/raw/main/Bulgaria/bulgaria1.xml",
    "https://iptv-epg.org/files/epg-bg.xml",
    "https://github.com/harrygg/EPG/raw/refs/heads/master/all-3days.basic.epg.xml.gz",
]
OUTPUT_FILE = "merged_epg.xml"
DEFAULT_LANG = "bg"


def download_epg(url):
    print(f"Downloading: {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.content
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        print("  → Decompressing .gz")
        with gzip.open(BytesIO(data), "rb") as gz:
            data = gz.read()
    return data


def validate_xml(xml_data, url):
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"⚠️ Parse error in {url}: {e}")
        xml_data = xml_data.decode("utf-8", errors="ignore").replace("&", "&amp;")
        root = ET.fromstring(xml_data)
    for tag in ["display-name", "title", "desc"]:
        for elem in root.findall(f".//{tag}"):
            if "lang" not in elem.attrib:
                elem.set("lang", DEFAULT_LANG)
    return ET.tostring(root, encoding="utf-8")


def merge_epgs(epg_data):
    merged_root = ET.Element("tv")
    seen_channels = set()
    seen_programs = set()
    for data in epg_data:
        root = ET.fromstring(data)
        for ch in root.findall("channel"):
            cid = ch.get("id")
            if cid and cid not in seen_channels:
                merged_root.append(ch)
                seen_channels.add(cid)
        for prog in root.findall("programme"):
            key = (prog.get("channel"), prog.get("start"), prog.get("stop"))
            if key not in seen_programs:
                merged_root.append(prog)
                seen_programs.add(key)
    return merged_root


def save_epg(root, filename):
    ET.ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)
    print(f"✅ Saved merged EPG as {filename}")


def main():
    epg_data = []
    for url in EPG_URLS:
        try:
            data = download_epg(url)
            clean = validate_xml(data, url)
            epg_data.append(clean)
        except Exception as e:
            print(f"⚠️ Failed {url}: {e}")
    if not epg_data:
        print("❌ No valid EPGs")
        return
    merged_root = merge_epgs(epg_data)
    save_epg(merged_root, OUTPUT_FILE)


if __name__ == "__main__":
    main()
