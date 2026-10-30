"""Builds corpus.d parts for Ceará from the retrieved ALECE ementário pages (no network).

    python -X utf8 parse.py --today YYYY-MM-DD [--part-size 50]

Each Lei Complementar page of the ALECE ementário is the act's text with its later alterations worked in: earlier
wordings struck through (<s>), each alteration noted in parentheses, often as a link ("(Nova redação dada pela Lei
Complementar n.º 27, de 17.01.2001)", "(Acrescido pela ...)", "(Revogado pela ...)"). An act with no such note and no
struck text is given as enacted, credited to the act itself; an altered act only as its text in force, credited to
ALECE as the oldest version available, dated by the latest date its alteration notes cite.
"""
import argparse, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from br_lib import lines_of, units_of, write_part, sha, norm  # noqa: E402

CACHE = HERE / '.cache'
BLOCK = {'p', 'div', 'br', 'tr', 'li', 'table', 'tbody', 'thead', 'ul', 'ol', 'center', 'blockquote', 'h1', 'h2', 'h3',
         'h4', 'h5', 'h6'}
VOID = {'br', 'img', 'meta', 'link', 'hr', 'input', 'col', 'area', 'base', 'wbr'}
NOTE = re.compile(r'\(\s*(?:Nova\s+reda|Reda[çc]|Acresc|Revogad|Inclu[íi]d|Alterad|Renumerad|Suprimid|Vide\b|Vig[êe]n|'
                  r'Regulamentad|Modificad|Declarad|Suspens|Ver\b|Efic[áa]cia|Derrogad|Transformad|Prorrogad)'
                  r'(?:[^()]|\([^()]*\))*\)', re.I)
BOILER = re.compile(r'^(?:VOLTAR|O texto desta Lei n[ãa]o substitui o publicado no Di[áa]rio Oficial\.?)$', re.I)


class Split(HTMLParser):
    """The page split into the text as shown without struck-through runs, and the struck runs (a strike-through
    applies to everything inside it)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.kept, self.old = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK:
            self.kept.append('<br>')
        if tag not in VOID:
            st = (dict(attrs).get('style') or '').lower()
            self.stack.append((tag, tag in ('s', 'strike', 'del') or 'line-through' in st))

    def handle_endtag(self, tag):
        if tag in BLOCK:
            self.kept.append('<br>')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, d):
        if any(e[1] for e in self.stack):
            self.old.append(d)
        else:
            self.kept.append(html.escape(d, quote=False))


def body(h):
    h = re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->|<head\b.*?</head>|<xml\b.*?</xml>', '', h)
    i = h.lower().find('<body')
    return h[h.index('>', i) + 1:] if i >= 0 else h


def split(h):
    p = Split()
    p.feed(body(h))
    p.close()
    kept = ''.join(p.kept)
    lines, notes = [], []
    for kind, l in lines_of(kept):
        notes += NOTE.findall(l)
        l = norm(NOTE.sub(' ', l))
        if not l or not re.search(r'\w', l) or BOILER.match(l):
            continue
        lines.append((kind, l))
    return lines, notes, norm(''.join(p.old))


DMY = re.compile(r'\b(\d{1,2})[º°]?\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4}|\d{2})\b')
MONTHS = {m: i + 1 for i, m in enumerate(['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
                                           'setembro', 'outubro', 'novembro', 'dezembro'])}
LONG = re.compile(r'\b(\d{1,2})[º°o]?\s+de\s+(' + '|'.join(MONTHS) + r')\s+de\s+(\d{4})', re.I)


def year(y):
    y = int(y)
    return y if y > 99 else (2000 + y if y <= 40 else 1900 + y)


def dates(s):
    out = [f'{year(y):04d}-{int(mo):02d}-{int(d):02d}' for d, mo, y in DMY.findall(s) if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31]
    out += [f'{int(y):04d}-{MONTHS[mo.lower()]:02d}-{int(d):02d}' for d, mo, y in LONG.findall(s)]
    return out


def is_alteration(n):
    return not re.match(r'^\(\s*(Vide|Ver\b|Regulamentad|Vig[êe]n)', n, re.I)


HEADER = re.compile(r'LEI\s+COMPLEMENTAR\s+(?:ESTADUAL\s+)?N[.º°o\s]*\s*(\d+)', re.I)


COUNTRY = {
    'code': 'BR-CE', 'name': 'Ceará', 'slug': 'brazil-ceara', 'lang': 'pt', 'tz': 'America/Fortaleza',
    'future_branch': 'futuro',
    'publisher': {'name': 'Assembleia Legislativa do Estado do Ceará (ALECE)', 'email': 'alece@al.ce.gov.br.invalid'},
    'default_in_force_rule': {
        'text': 'Decreto-Lei 4.657/1942 (LINDB) art. 1: unless it says otherwise, a law takes effect 45 days after its '
                'official publication. Ceará laws almost always say "Esta Lei entra em vigor na data de sua '
                'publicação"; this record dates each act as enacted by its publication in the Diário Oficial do Estado.',
        'source': 'https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm'},
    'licence_note': 'Texts: Assembleia Legislativa do Estado do Ceará (ALECE), ementário de Leis Complementares, '
                    'www2.al.ce.gov.br. Lei 9.610/1998 art. 8 IV: the texts of laws and other official acts are not '
                    'protected by copyright. Non-official text ("O texto desta Lei não substitui o publicado no Diário '
                    'Oficial"): only the Diário Oficial do Estado is authoritative.',
}
DECISIONS = [
    'An act ALECE shows no alteration for (no alteration note, nothing struck through) is given as enacted, credited to '
    'the act itself and dated by its publication in the Diário Oficial do Estado as the page states it ("D.O."). An '
    'altered act is given only as its text in force, credited to ALECE as the oldest version available and dated by '
    'the latest date its alteration notes cite. The wordings in between are not reconstructed yet, so no earlier '
    'version is given rather than a wrong one. An altered act whose notes cite no date is left out.',
    'The text in force leaves out what the page strikes through (earlier wordings) and ALECE\'s alteration notes in '
    'parentheses ("(Nova redação dada pela ...)", "(Acrescido pela ...)", "(Revogado pela ...)", "(Vide ...)"); '
    '"Vide" and "Vigência" notes do not date a version. The page\'s "VOLTAR" link and its notice "O texto desta Lei '
    'não substitui o publicado no Diário Oficial." are left out. Two-digit years in the notes (17.01.01) are read as '
    '19xx above 40 and 20xx otherwise.',
    'One file per Art.; headings of the Títulos, Capítulos and Seções stand above the first article under them; '
    '"000-titulo" holds the title, the ementa and the preamble. Text after the last article (place, date, signatures, '
    'annexes) stays with the last article. Tables are one line per row, cells separated by " | "; images are left out.',
]
AI = ["Claude Code (claude-opus-5-5) wrote Lexifina's code and chose the sources. No model output is used as legal "
      "text or dates: every word comes from the ALECE pages."]


def raw(url):
    p = CACHE / 'raw' / sha(url.encode())
    return p.read_bytes() if p.exists() else None


def decode(b):
    m = re.search(rb'charset=["\']?([\w-]+)', b[:3000])
    enc = (m.group(1).decode() if m else 'cp1252').lower()
    if enc in ('iso-8859-1', 'latin1', 'latin-1', 'windows-1252'):
        enc = 'cp1252'
    return b.decode(enc, 'replace')


def act_of(url):
    b = raw(url)
    if b is None:
        return None, {}, 'not fetched'
    lines, notes, old = split(decode(b))
    head = next((l for _, l in lines[:12] if HEADER.search(l)), None)
    if not head:
        return None, {}, 'no header'
    n = int(HEADER.search(head).group(1))
    ds = dates(head)
    m = re.search(r'D\.?\s*O\.?\s*E?\.?\s*(?:de\s*)?(\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2,4})', head)
    published = dates(m.group(1))[0] if m and dates(m.group(1)) else None
    enacted = ds[0] if ds else None
    if not enacted:
        return None, {}, 'no date'
    y = enacted[:4]
    slug = law_key = f'lc-{y}-{n:03d}'
    short, label = f'LC {n}/{y}', f'Lei Complementar nº {n}, de {enacted[8:10]}.{enacted[5:7]}.{y}'
    first = published or enacted
    alter = sorted(d for x in notes if is_alteration(x) for d in dates(x) if d > first)
    altered = bool(old) or any(is_alteration(x) for x in notes)
    if altered and not alter:
        return None, {}, 'altered, no dated note'
    units = units_of(lines, adt=False)
    if not units or list(units) == ['000-titulo']:
        return None, {}, 'no text'
    ementa = ''
    t = units.get('000-titulo', {}).get('text', '').split('\n')
    for i, l in enumerate(t):
        if HEADER.search(l):
            ementa = next((norm(x) for x in t[i + 1:] if norm(x) and not x.lstrip('# ').startswith('(')), '')
            break
    laws = {law_key: {'label': label, 'title': ementa or label, 'kind': 'law', 'enacted': enacted, 'published': published,
                      'url': url, 'temporary_until': None, 'restores': None, 'note': None}}
    v = {'from': alter[-1] if alter else first, 'source_url': url, 'sha256': sha(b), 'units': units}
    if alter:
        v['note'] = (f'Text in force as kept by ALECE; {label} was altered on {len(set(alter))} date(s) its notes cite, '
                     f'the latest {alter[-1]}.')
    act = {'slug': slug, 'short': short,
           'title': label + (f' ({ementa})' if ementa and len(ementa) < 160 else ''),
           'url': url, 'first_law': None if alter else law_key, 'earlier_laws': [law_key] if alter else [],
           'versions': [v]}
    return act, laws, 'ok'


def part(name, acts, laws, today):
    c = {'country': COUNTRY,
         'sources': [{'name': 'Assembleia Legislativa do Estado do Ceará (ALECE): ementário de Leis Complementares, the '
                              'page of each act', 'url': 'https://www2.al.ce.gov.br/legislativo/ementario/lc.htm',
                      'retrieved': today, 'licence': COUNTRY['licence_note'], 'notes': f'{len(acts)} acts in this part.'}],
         'laws': laws, 'acts': acts, 'applies': [], 'decisions': DECISIONS, 'ai_use': AI}
    return write_part(HERE / 'corpus.d', name, c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', required=True)
    ap.add_argument('--part-size', type=int, default=50)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    urls = json.loads((CACHE / 'lc-urls.json').read_text(encoding='utf-8'))
    acts, why = {}, {}
    for u in urls:
        if raw(u) is None:
            why['not fetched'] = why.get('not fetched', 0) + 1
            continue
        act, l, w = act_of(u)
        why[w] = why.get(w, 0) + 1
        if act:
            if act['slug'] in acts:
                why['duplicate'] = why.get('duplicate', 0) + 1
                continue
            acts[act['slug']] = (act, l)
    print(why)
    if a.dry or not (CACHE / 'fetch-done').exists():
        return acts
    order = sorted(acts.values(), key=lambda x: (next(iter(x[1].values()))['enacted'], x[0]['slug']))
    for i in range(0, len(order), a.part_size):
        chunk = order[i:i + a.part_size]
        laws = {}
        for _, l in chunk:
            laws.update(l)
        print(part(f'20-lc-{i // a.part_size + 1:02d}', [x[0] for x in chunk], laws, a.today), len(chunk))


if __name__ == '__main__':
    main()
