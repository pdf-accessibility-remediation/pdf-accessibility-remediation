# pipeline/data

## english-words.txt

The offline English word list that `lib/langcands.py` uses to decide whether a word is "part of English" (#118, language
tagging). A word on this list is never sent to the AI as a candidate, unless it is printed in another script.

- **Source:** SCOWL (Spell Checker Oriented Word Lists) by Kevin Atkinson, release 2020.12.07,
  `scowl-2020.12.07.tar.gz` from the SCOWL project on SourceForge (sha256
  `5587667caa20c4891390c2d42dbb4d5c4c3f41bee77af1457ece3ba23fb859cc`).
- **Lists used:** `final/english-words`, `american-words`, `english-upper` and `american-upper`, sizes 10 to 70. Size 70
  is the largest size SCOWL recommends for spell checking. Proper-name and abbreviation lists are left out.
- **How it was built:** the lists were decoded as Latin-1, normalised to NFC and lower-cased, and possessive forms
  ("'s") were left out. The result was deduplicated and sorted, one word per line, UTF-8. No SCOWL script was run.
  - The builder is `runs/118-language-tagging/build_wordlist.py`. It is local only, because runs/ is never committed.
  - Result: 121,935 words, sha256 `5d6d9f564eecf5ab6270d7cf7ba7ce06c1ffea1fb4f8203fb27cc19128ce3dde`.
- **Licence:** SCOWL's own copyright and permission notice, in `english-words.COPYRIGHT` beside this file (copied unchanged
  from the release). It allows use, copying, modification and distribution for any purpose, provided the notice travels
  with the copies.

To update the list, build it from a newer release the same way, and replace both files and the numbers above.

## english-common-romanized.txt

The common English words that look like romanized Japanese or Chinese (review 08, M6 of #118). With title growth on
(`LANG_GROW=on`), a capitalized word in the English list may join a romanized title when it has a Hepburn or pinyin shape
("Nihon", "Kamakura"), unless it is on this list ("China", "Home", "One", "King", "Rite").

- **Source:** the same SCOWL 2020.12.07 release and lists as `english-words.txt`, sizes 10 to 35 only (SCOWL's common
  words), decoded and normalised the same way, kept when `lib/langcands.romanized_shape` accepts them.
- **Builder:** `runs/118-language-tagging/m6/build_common.py` (local only).
- **Removed by hand, 2026-11-21:** "shin" (proposal 20 (b), Patrick). On the test books it is the Japanese title prefix 新
  ("Shin kokin wakashū", "Shin sekai"): 163 places, all titles. A build from SCOWL puts it back, so remove it again.
- **Result:** 3,787 words, sha256 `0e058e2306f1d52ff5e73819ce1371fb116e075c9207212d5d10f962bbbea15c` (3,788 as built,
  `fd316845694c859e413efcb42b45236fb0bce3d6113d7bb072a0ee706e8d37c6`, before "shin" was removed).
- **Licence:** as above (`english-words.COPYRIGHT`).

## latin-whitaker.json

The Latin forms behind the review page's "Also found in a Latin dictionary." line (#141, proposal 14; `lib/latinlist.py`).
A row the AI tagged Latin shows the line when every word of its form is a form this data recognizes: a unique form, or
a stem followed by an ending of the same inflection class. The data decides nothing.

- **Source:** Whitaker's Words by William A. Whitaker, the data files of the mk270/whitakers-words repository on GitHub
  (`DICTLINE.GEN`, `INFLECTS.LAT`, `UNIQUES.LAT`). The repository's zip of master was downloaded on 2026-11-20:
  - upstream commit `fb7fb6f04c0c05b68d496a521d8c32abe823e57b` (the zip's comment);
  - zip sha256 `239ed0a351774489b651688b51ba144df9d604b22cd270f028abf639070efcc8`.

  master moves, so fetch that commit to build again.
- **How it was built:** `python3 tools/dict_measure.py build DICT_DIR whitaker`, with the zip unpacked in
  `DICT_DIR/whitaker/src/`. It writes `DICT_DIR/whitaker/_lists/whitaker.json`, copied here unchanged.
  - The data files are read as plain text; no Whitaker program is run.
  - Every stem, ending and unique form is normalized by `lib/latinlist.latin_norm` (compatibility forms folded, marks
    removed, lower case, æ/œ as ae/oe, v as u, j as i).
  - Participle and supine endings use the verb's stems.
- **Result:** 55,437 stems, 955 endings and 61 unique forms; 655,121 bytes, sha256
  `7ef11a6655133771168bb7bfd21a6298de6a9c1f6c1cfabb4900ece14ad109aa`.
- **Licence:** Whitaker's own notice, in `latin-whitaker.LICENCE` beside this file (the repository's `LICENCE.txt`,
  copied unchanged): "Permission is hereby freely given for any and all use of program and data."

## latin-phrases.txt

The Latin phrases behind the review page's "Part of the Latin phrase …" line (#141, proposal 14; `lib/latinlist.py`). A
form the AI left untagged shows the line when one of its places sits inside a whole phrase of this list.

- **Source:** written for #141's measurement (`tools/dict_measure.PHRASES`), not taken from a source. Its one French entry
  ("raison d'") is left out: 55 phrases.
- **Added 2026-11-21** (proposal 20 (c), Patrick): 28 more.
  - Seven with evidence on the test books: "materia medica", "locus classicus", "reductio ad absurdum", "summum bonum",
    "dramatis personae", "sub specie aeternitatis", "per diem".
  - 21 common ones like them ("ad libitum", "alter ego", … "vox populi").
  - Measured in `runs/150-language-finder-recall/m20/phrases.py` (local only).
- **Result:** 83 phrases, sha256 `14f5aec8455570bd91739c854690bf6b7df91da0738013329a1a659364f92704`. Lines starting with
  `#` are notes.
