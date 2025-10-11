import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO

# --- Configuration ---
EPG_URLS = [
    "https://github.com/globetvapp/epg/raw/main/Bulgaria/bulgaria1.xml",
    "https://iptv-epg.org/files/epg-bg.xml",
    "https://github.com/harrygg/EPG/raw/refs/heads/master/all-3days.basic.epg.xml.gz",
]
OUTPUT_FILE = "merged_epg.xml"
DEFAULT_LANG = "bg"


def download_epg(url: str) -> bytes:
    """Download EPG data (handles .gz automatically)."""
    print(f"⬇️  Downloading: {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.content

    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        print("  → Decompressing gzip data")
        with gzip.open(BytesIO(data), "rb") as gz:
            data = gz.read()
    return data


def safe_parse_xml(data: bytes, url: str) -> ET.Element:
    """Parse XML safely, fixing malformed entities and missing lang tags."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"⚠️  Parse error in {url}: {e}")
        # Try to fix common entity issues
        fixed = data.decode("utf-8", errors="ignore").replace("&", "&amp;")
        root = ET.fromstring(fixed)

    # Ensure required language attributes
    for tag in ["display-name", "title", "desc"]:
        for elem in root.findall(f".//{tag}"):
            if "lang" not in elem.attrib:
                elem.set("lang", DEFAULT_LANG)

    return root


def merge_epgs(epg_roots: list[ET.Element]) -> ET.Element:
    """Combine multiple EPG XML trees, removing duplicates."""
    merged_root = ET.Element("tv")
    seen_channels = set()
    seen_programs = set()

    for root in epg_roots:
        # Merge unique channels
        for ch in root.findall("channel"):
            cid = ch.get("id")
            if cid and cid not in seen_channels:
                merged_root.append(ch)
                seen_channels.add(cid)

        # Merge unique programmes (based on channel + start + stop)
        for prog in root.findall("programme"):
            key = (prog.get("channel"), prog.get("start"), prog.get("stop"))
            if key not in seen_programs:
                merged_root.append(prog)
                seen_programs.add(key)

    print(f"✅ Merged {len(seen_channels)} unique channels and {len(seen_programs)} programmes.")
    return merged_root


def save_epg(root: ET.Element, filename: str) -> None:
    """Save merged EPG XML with proper formatting and encoding."""
    try:
        ET.ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)
        print(f"💾 Saved merged EPG to {filename}")
    except Exception as e:
        print(f"❌ Error saving XML: {e}")


def main():
    epg_roots = []

    for url in EPG_URLS:
        try:
            data = download_epg(url)
            root = safe_parse_xml(data, url)
            epg_roots.append(root)
        except Exception as e:
            print(f"⚠️  Failed to process {url}: {e}")

    if not epg_roots:
        print("❌ No valid EPG data downloaded. Exiting.")
        return

    merged_root = merge_epgs(epg_roots)
    save_epg(merged_root, OUTPUT_FILE)


if __name__ == "__main__":
    main()
