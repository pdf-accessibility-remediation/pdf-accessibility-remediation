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
- **Result:** 3,788 words, sha256 `fd316845694c859e413efcb42b45236fb0bce3d6113d7bb072a0ee706e8d37c6`.
- **Licence:** as above (`english-words.COPYRIGHT`).
