"""scripts.py: which CJK script a run of text is in, and what language tag it needs. Shared by audit.py (the digest's
cjk_runs) and apply.py (the language step), so both see the same runs.

    scripts.kind(text)                          -> None | 'mixed_with_latin' | 'kana' | 'hangul' | 'han_only'
    scripts.action(kind, text, doc_lang, kana_lang) -> ('tag', lang) | ('inherit', None) | ('defer', why)

A run needs a language tag only when it differs from the document's (WCAG 3.1.2). Hangul is only Korean and kana only
Japanese, so those runs are known. Chinese characters with no kana or hangul (Han-only) are Japanese or Chinese and are
never guessed: in a Chinese, Japanese or Korean document they are read in its language (Japanese kanji, Korean hanja),
elsewhere they go to a person.
"""
import re

KANA = re.compile(r'[぀-ヿㇰ-ㇿｦ-ﾟ]')            # hiragana, katakana, their extensions, half-width katakana
HANGUL = re.compile(r'[가-힯ᄀ-ᇿ㄰-㆏ꥠ-꥿ힰ-퟿ﾠ-ￜ]')
                                                                         # syllables, jamo (+ extended), compatibility and half-width jamo
HAN = re.compile(r'[㐀-䶿一-鿿豈-﫿]')           # CJK ideographs, extension A, compatibility ideographs
CJK = re.compile(r'[　-ヿ㐀-䶿一-鿿豈-﫿＀-￯'
                 r'가-힯ᄀ-ᇿ㄰-㆏ꥠ-꥿ힰ-퟿]')   # all of the above, CJK punctuation, full-width forms

def kind(text):
    """The CJK script of a run, or None when it has no kana, hangul or Chinese character. Latin letters left after the CJK characters are
    removed make it 'mixed_with_latin'; then kana means Japanese, hangul Korean, and Chinese characters alone 'han_only'."""
    if not (KANA.search(text) or HANGUL.search(text) or HAN.search(text)): return None   # CJK punctuation or full-width forms alone
    if re.sub(r'[\s\W\d_]', '', CJK.sub('', text)): return 'mixed_with_latin'
    if KANA.search(text): return 'kana'
    if HANGUL.search(text): return 'hangul'
    return 'han_only'

def primary(lang):
    """The language subtag of a BCP 47 tag, lower case: 'zh' for 'zh-Hant-TW', '' for none."""
    return re.split(r'[-_]', str(lang or '').strip())[0].lower()

CJK_DOC = {'zh', 'ja', 'ko', 'yue', 'cmn'}                  # documents whose own language a Han-only run is read in

def script_lang(text, doc_lang):
    """The language the CJK characters of text are in: ja for kana, ko for hangul, the document's own language for
    Chinese characters alone in a CJK document, else None (not known)."""
    if KANA.search(text): return 'ja'
    if HANGUL.search(text): return 'ko'
    return primary(doc_lang) if primary(doc_lang) in CJK_DOC else None

def action(k, text, doc_lang, kana_lang=None):
    """What the language step does with a run of kind k.
    kana_lang: the work order's kana_runs; kana is only Japanese, so without one kana runs are tagged 'ja'."""
    doc = primary(doc_lang); lang = script_lang(text, doc_lang)
    if lang is not None and lang == doc: return ('inherit', None)        # the document's own language: nothing to tag
    if k == 'mixed_with_latin': return ('defer', 'CJK mixed with Latin in one run')
    if k == 'hangul': return ('tag', 'ko')
    if k == 'kana': return ('tag', kana_lang or 'ja')
    return ('defer', 'Han-only runs (ja vs zh)')
