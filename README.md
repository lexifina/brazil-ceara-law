# Ceará: law history in git

The law of the State of Ceará (Estado do Ceará) (Brazil) as a git history: one file per Artigo, one paragraph per line, so `git blame`, `git log` and `git diff` work line by line. The text is Portuguese, the only official language.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law).

## What this repository holds

| Folder | Act | Versions |
| --- | --- | ---: |
| `lc-<year>-<number>/` | the Leis Complementares on the ALECE ementário | 1 each |

**Partial:** the Constituição Estadual is not in yet (ALECE publishes it as a typeset PDF book), nor ordinary Leis; the history may still gain earlier commits. An act ALECE shows no alteration for is given **as enacted**, credited to the act itself. An altered act is given **only as its text in force**, credited to ALECE as the oldest version available: the wordings in between are not reconstructed yet, so no earlier version is shown rather than a wrong one.

## Source

[ALECE, ementário de Leis Complementares](https://www2.al.ce.gov.br/legislativo/ementario/lc.htm), published by the Assembleia Legislativa do Estado do Ceará (ALECE). Each version names the page it was taken from and that page's sha256, in `data/versions.json`.

## Dates

An unaltered act is dated by its publication in the Diário Oficial do Estado as its page states it (Ceará laws almost always take effect on publication). An altered act's text in force is dated by the latest date among the alterations ALECE's notes cite ("(Nova redação dada pela ...)", "(Acrescido pela ...)", "(Revogado pela ...)"); "Vide" notes do not date a version. Commits are at noon in Fortaleza.

## How it is built

Lexifina reads the sources listed here and records each act's dated versions, and the laws that made each change, in one corpus file. `tools/build.py` writes this repository from that file, and the same corpus always gives the same commit hashes; `REPRODUCE.md` gives the details and the checks. A model (Claude) wrote Lexifina's code; it wrote no legal text, and no model runs when the history is built.

Each page becomes one file per Art.; headings of the Títulos, Capítulos and Seções stand above the first article under them; `000-titulo.md` holds the title, the ementa and the preamble. For the text in force, the earlier wordings the page strikes through and ALECE's alteration notes in parentheses are left out, as are the page's "VOLTAR" link and its notice that the text does not replace the Diário Oficial. Tables are one line per row, with cells separated by ` | `.

## How it is checked

Every version is read back from git on the day it took effect (`tools/check_repo.py`) and must match the corpus; an independent letters-and-digits comparison of every version against the source page must show no difference. Results are in `REPRODUCE.md`.

## What "author" means

The author of each commit is the law that made the text, or, for a consolidated text, the publisher, with an e-mail address that cannot exist; the committer is always Lexifina.

## Limits

Not a complete history: an altered act starts at its text in force. Of the 374 Lei Complementar pages the ementário links, 345 are in: 8 answered "not found", 12 carry no recognisable heading (number and date), 7 are altered with notes that cite no date, and 2 are a duplicate page or an empty one. The text is not the official version: only the Diário Oficial do Estado is authoritative. Text after the last article (place, date, signatures, annexes) stays in the last article's file.

## Licence

See [LICENSE](LICENSE): Brazilian law texts are not protected by copyright (Lei 9.610/1998, art. 8, IV). Fonte: ALECE, ementário de Leis Complementares, Assembleia Legislativa do Estado do Ceará (ALECE).
