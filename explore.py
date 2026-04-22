import requests
from bs4 import BeautifulSoup

def explore():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    # Step 1: Login
    print("=== Step 1: Login ===")
    login_url = "https://student.amikompurwokerto.ac.id/auth/toenter"
    login_data = {
        'pengguna': '24SA31A022',
        'passw': '96376'
    }
    res = session.post(login_url, data=login_data)
    print(f"Login response: {res.text}")
    print(f"Cookies after login: {dict(session.cookies)}")
    
    # Step 2: Fetch presensi page
    print("\n=== Step 2: Fetch Presensi Page ===")
    res2 = session.get("https://student.amikompurwokerto.ac.id/presensi")
    print(f"Presensi page status: {res2.status_code}")
    print(f"Content length: {len(res2.text)}")
    
    # Save full HTML to file for inspection
    with open("presensi_page.html", "w", encoding="utf-8") as f:
        f.write(res2.text)
    print("Saved full HTML to presensi_page.html")
    
    # Step 3: Look for script tags and JS files
    soup = BeautifulSoup(res2.text, 'html.parser')
    print(f"\nPage Title: {soup.title.string if soup.title else 'No Title'}")
    
    # Find CSRF token
    meta_csrf = soup.find('meta', attrs={'name': 'csrf-token'})
    print(f"\nCSRF Token Meta: {meta_csrf}")
    
    # Find all script tags
    scripts = soup.find_all('script')
    print(f"\n=== Script Tags ({len(scripts)}) ===")
    for i, script in enumerate(scripts):
        src = script.get('src', '')
        if src:
            print(f"  Script {i}: {src}")
        else:
            content = script.string or ''
            if any(k in content.lower() for k in ['validasi', 'absen', 'presensi', 'store', 'fetch', 'ajax', 'axios']):
                print(f"  Script {i} (inline, relevant): {content[:500]}")
    
    # Find buttons with onclick or data attributes
    print("\n=== Buttons/Links with onclick ===")
    for el in soup.find_all(attrs={"onclick": True}):
        print(f"  Tag: {el.name}, onclick: {el.get('onclick')}, text: {el.text.strip()[:50]}")
    
    # Find all forms
    print("\n=== Forms ===")
    for form in soup.find_all('form'):
        print(f"  Form: action={form.get('action')}, method={form.get('method')}")
        for inp in form.find_all('input'):
            print(f"    Input: name={inp.get('name')}, type={inp.get('type')}, value={inp.get('value')}")
    
    # Look for any elements with 'validasi' or 'absen' in attributes
    print("\n=== Elements with validasi/absen keywords ===")
    for el in soup.find_all(True):
        attrs_str = str(el.attrs)
        if any(k in attrs_str.lower() for k in ['validasi', 'absen', 'presensi']):
            print(f"  Tag: {el.name}, attrs: {el.attrs}, text: {el.text.strip()[:50]}")
    
    # Step 4: Check common API endpoints
    print("\n=== Testing common API endpoints ===")
    test_urls = [
        "https://student.amikompurwokerto.ac.id/presensi/store",
        "https://student.amikompurwokerto.ac.id/presensi/validasi",
        "https://student.amikompurwokerto.ac.id/api/presensi",
        "https://student.amikompurwokerto.ac.id/presensi/absen",
    ]
    for url in test_urls:
        try:
            r = session.get(url, allow_redirects=False)
            print(f"  GET {url} -> {r.status_code}")
        except Exception as e:
            print(f"  GET {url} -> Error: {e}")

if __name__ == '__main__':
    explore()
