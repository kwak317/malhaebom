#!/usr/bin/env python3
"""No third-party packages required. Run: python scripts/check_site.py"""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / 'index.html', ROOT / 'project' / 'index.html']

class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        for field in (('href',) if tag in ('a','link') else ('src',) if tag in ('img','script') else ()):
            if attrs.get(field): self.links.append((tag, attrs[field]))

def route_target(path: Path) -> Path:
    if path.is_dir(): return path / 'index.html'
    return path

def main():
    errors = []
    for page in PAGES:
        p = Reader()
        p.feed(page.read_text(encoding='utf-8'))
        seen = set()
        for id_value in p.ids:
            if id_value in seen: errors.append(f'{page.relative_to(ROOT)}: duplicate id {id_value}')
            seen.add(id_value)
        for tag, link in p.links:
            u = urlsplit(link)
            if u.scheme or u.netloc or link.startswith(('mailto:', 'tel:', '//')):
                continue
            path = route_target((page.parent / unquote(u.path)).resolve()) if u.path else page
            if not path.is_relative_to(ROOT):
                errors.append(f'{page.relative_to(ROOT)}: asset goes outside root: {link}')
            elif not path.exists():
                errors.append(f'{page.relative_to(ROOT)}: missing {link}')
            elif tag == 'a' and u.fragment:
                target = Reader()
                target.feed(path.read_text(encoding='utf-8'))
                if u.fragment not in target.ids:
                    errors.append(f'{page.relative_to(ROOT)}: anchor missing {link}')
        print(f'PASS {page.relative_to(ROOT)}: {len(p.ids)} IDs, {len(p.links)} links/assets')
    for css in ROOT.rglob('*.css'):
        for raw in re.findall(r'''url\(\s*['"]?([^'")]+)''', css.read_text(encoding='utf-8')):
            u = urlsplit(raw.strip())
            if u.scheme or u.netloc or raw.startswith(('/', '#')):
                continue
            target = (css.parent / unquote(u.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                errors.append(f'{css.relative_to(ROOT)}: missing CSS asset {raw}')
    for suffix, header in (('.webp', b'RIFF'), ('.png', b'\x89PNG')):
        for asset in ROOT.rglob('*' + suffix):
            if not asset.read_bytes().startswith(header):
                errors.append(f'{asset.relative_to(ROOT)}: invalid {suffix} signature')
    if errors:
        print('\n'.join('FAIL ' + error for error in errors))
        sys.exit(1)
    print('PASS internal files, CSS assets, image signatures, routes, anchors, and duplicate IDs')

if __name__ == '__main__': main()
