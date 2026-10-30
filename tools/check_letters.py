"""Independent letters-and-digits check of every version against its ALECE page (regex tokenizer, no HTML parser).

    python -X utf8 check_letters.py [part.json ...]

For each version: the page body (no head, styles, scripts, comments or Word <xml> blocks) with every text run under a
strike-through (s, strike, del, or a line-through style) left out, ALECE's alteration notes in parentheses
("(Nova redação dada pela ...)", "(Acrescido pela ...)", ...) left out, and the "VOLTAR" link and the "O texto desta Lei
não substitui o publicado no Diário Oficial." notice left out, reduced to letters and digits, must equal the version's
unit files reduced the same way, each unit found at its place in document order.
"""
import hashlib, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from br_lib import letters_check  # noqa: E402

TOKEN = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9:]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>|([^<]+)', re.S)
VOIDS = ('br', 'img', 'meta', 'link', 'hr', 'input', 'col', 'area', 'base', 'wbr')
NOTES = re.compile(r'\(\s*(?:Nova\s+reda|Reda[çc]|Acresc|Revogad|Inclu[íi]d|Alterad|Renumerad|Suprimid|Vide\b|Vig[êe]n|'
                   r'Regulamentad|Modificad|Declarad|Suspens|Ver\b|Efic[áa]cia|Derrogad|Transformad|Prorrogad)'
                   r'(?:[^()]|\([^()]*\))*\)', re.I)
NOTICE = re.compile(r'(?im)^\s*(?:VOLTAR|O texto desta Lei n[ãa]o substitui o publicado no Di[áa]rio Oficial\.?)\s*$')


def page_text(b):
    m = re.search(rb'charset=["\']?([\w-]+)', b[:3000])
    enc = (m.group(1).decode() if m else 'cp1252').lower()
    s = b.decode('cp1252' if enc in ('iso-8859-1', 'latin1', 'latin-1', 'windows-1252') else enc, 'replace')
    s = re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->|<head\b.*?</head>|<xml\b.*?</xml>', '', s)
    s = re.sub(r'<!\[[^\]<>]*\]>', '', s)  # Word's <![if !supportLists]> ... <![endif]> markers are markup, not text
    i = s.lower().find('<body')
    s = s[s.index('>', i) + 1:] if i >= 0 else s
    open_, out = [], []
    for t in TOKEN.finditer(s):
        close, tag, a, text = t.group(1), (t.group(2) or '').lower(), t.group(3) or '', t.group(4)
        if text is not None:
            if not any(o[1] for o in open_):
                out.append(re.sub(r'\s+', ' ', html.unescape(text)))
            continue
        if tag in ('p', 'div', 'br', 'tr', 'li', 'table', 'tbody', 'thead', 'ul', 'ol', 'center', 'blockquote') or \
                re.fullmatch(r'h[1-6]', tag):
            out.append('\n')
        if close:
            for k in range(len(open_) - 1, -1, -1):
                if open_[k][0] == tag:
                    del open_[k:]
                    break
        elif tag not in VOIDS and not a.rstrip().endswith('/'):
            open_.append((tag, tag in ('s', 'strike', 'del') or 'line-through' in a.lower()))
    text = ''.join(out)
    text = '\n'.join(NOTES.sub(' ', l) for l in text.split('\n'))
    return NOTICE.sub('', '\n'.join(l.strip() for l in text.split('\n')))


def main(paths):
    vs = []
    for p in paths:
        for a in json.load(open(p, encoding='utf-8'))['acts']:
            for v in a['versions']:
                raw = (HERE / '.cache' / 'raw' / hashlib.sha256(v['source_url'].encode()).hexdigest()).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == v['sha256'], (a['slug'], 'sha256')
                vs.append((f"{a['slug']} {v['from']}", v['units'], page_text(raw)))
    bad = letters_check(vs, None)
    for b in bad:
        print(b)
    print(f'{len(vs)} versions checked, {len(bad)} mismatches')
    return len(bad)


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1:] or sorted(str(p) for p in (HERE / 'corpus.d').glob('*.json'))) else 0)
