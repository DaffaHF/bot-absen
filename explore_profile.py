import requests
from bs4 import BeautifulSoup

def explore():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    
    # Login
    login_url = "https://student.amikompurwokerto.ac.id/auth/toenter"
    login_data = {'pengguna': '24SA31A022', 'passw': '96376'}
    res = session.post(login_url, data=login_data)
    print("Login:", res.text)
    
    # Try different pages
    pages = [
        ("Dashboard", "https://student.amikompurwokerto.ac.id/"),
        ("Profil", "https://student.amikompurwokerto.ac.id/profil"),
        ("Akademik", "https://student.amikompurwokerto.ac.id/akademik"),
        ("KHS", "https://student.amikompurwokerto.ac.id/khs"),
        ("Transkrip", "https://student.amikompurwokerto.ac.id/transkrip")
    ]
    
    for name, url in pages:
        print(f"\n--- {name} ({url}) ---")
        try:
            r = session.get(url, timeout=5)
            print("Status:", r.status_code)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find any text that looks like IPK, Nama, or NIM
            found = []
            for elem in soup.find_all(['td', 'th', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'div', 'b', 'strong']):
                text = elem.get_text(strip=True)
                text_lower = text.lower()
                if len(text) > 2 and len(text) < 100:
                    if 'ipk' in text_lower or 'indeks prestasi' in text_lower or 'nama' in text_lower or 'nim' in text_lower or '24sa31a022' in text_lower:
                        if text not in found:
                            found.append(text)
            
            if found:
                for f in found[:20]:  # Limit output
                    print("Found:", f)
            else:
                print("No relevant keywords found.")
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    explore()
