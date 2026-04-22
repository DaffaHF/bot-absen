import re
from bs4 import BeautifulSoup

with open('akademik.html', 'r', encoding='utf-8') as f:
    text = f.read()

soup = BeautifulSoup(text, 'html.parser')
for e in soup.find_all(string=re.compile(r'IPK|NPM|SKS|Nama', re.IGNORECASE)):
    parent = e.parent
    if parent:
        print(f"Tag: {parent.name}, Class: {parent.get('class')}")
        print(f"Parent Text: {parent.get_text(strip=True)[:100]}")
        print("---")
