"""Debug: dump raw HTML from getabsenmhs."""
from amikom_client import AmikomClient

def debug():
    client = AmikomClient()
    client.login("24SA31A022", "96376")
    
    import requests
    url = "https://student.amikompurwokerto.ac.id/pembelajaran/getabsenmhs"
    data = {
        "thn_akademik": "2025/2026",
        "semester": "2",
        "makul": "18693__PSTIW050"  # Analisis dan Desain Sistem Informasi (belum validasi)
    }
    res = client.session.post(url, data=data, timeout=15)
    
    # Save to file
    with open("debug_absensi.html", "w", encoding="utf-8") as f:
        f.write(res.text)
    
    print(f"Response length: {len(res.text)}")
    print(f"Saved to debug_absensi.html")
    
    # Search for edit_presensikehadiran
    import re
    matches = re.findall(r'edit_presensikehadiran\([^)]+\)', res.text)
    print(f"\nedit_presensikehadiran calls found: {len(matches)}")
    for m in matches:
        print(f"  {m}")
    
    # Search for any onclick
    matches2 = re.findall(r'onclick="([^"]*)"', res.text)
    print(f"\nonclick attributes found: {len(matches2)}")
    for m in matches2:
        print(f"  {m}")
    
    # Search for status B
    if 'class="badge' in res.text or '>B<' in res.text:
        print("\nFound 'B' status markers in HTML")
    
    # Print first 2000 chars
    print(f"\n--- HTML Preview (first 2000 chars) ---")
    print(res.text[:2000])

if __name__ == "__main__":
    debug()
