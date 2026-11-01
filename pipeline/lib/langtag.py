"""langtag.py: check and tidy a BCP 47 language tag (the /Lang values a screen reader uses to pick a voice).

    norm('en_US') -> 'en-US'     norm(' EN ') -> 'en'     norm('english') -> None (not a tag: a person decides)

Only spelling is tidied (separator, case, spaces); a value that is not a tag after that is never guessed at.
apply.py normalises /Lang values with it (veraPDF rule 7.2-29); decide.py checks the work order's document.lang.
"""
import re

_TAG = re.compile(r'[a-z]{2,3}(?:-[a-z]{3}){0,3}'          # language (with extlang); 4-8 letter subtags are never assigned
                  r'(?:-[A-Z][a-z]{3})?'                                       # script
                  r'(?:-(?:[A-Z]{2}|\d{3}))?'                                  # region
                  r'(?:-(?:[a-z0-9]{5,8}|\d[a-z0-9]{3}))*'                     # variants
                  r'(?:-[a-wyz0-9](?:-[a-z0-9]{2,8})+)*'                       # extensions
                  r'(?:-x(?:-[a-z0-9]{1,8})+)?'                                # private use
                  r'|x(?:-[a-z0-9]{1,8})+')                                    # private use only


def norm(value):
    """The tag in canonical case with '-' separators, or None if it is not a well-formed BCP 47 tag."""
    parts = re.split(r'[-_]', str(value).strip())
    if not parts or not all(parts) or ' ' in str(value).strip(): return None
    out = [parts[0].lower()]
    for p in parts[1:]:
        if len(p) == 4 and p.isalpha() and out[-1] != 'x': out.append(p.title())          # script: Latn, Hant
        elif (len(p) == 2 and p.isalpha() or len(p) == 3 and p.isdigit()) and out[-1] != 'x': out.append(p.upper())   # region
        else: out.append(p.lower())
    tag = '-'.join(out)
    return tag if _TAG.fullmatch(tag) else None


# Language names for people (the app's pages name a language, never its code): the tags the pipeline writes. The one
# BCP 47 → name table (review/ocr.py's tables are keyed by Tesseract's codes).
NAMES = {'en': 'English', 'fr': 'French', 'de': 'German', 'es': 'Spanish', 'pt': 'Portuguese', 'it': 'Italian', 'nl': 'Dutch',
         'la': 'Latin', 'haw': 'Hawaiian', 'tl': 'Tagalog', 'fil': 'Filipino', 'ilo': 'Ilokano', 'bik': 'Bikol', 'vi': 'Vietnamese',
         'id': 'Indonesian', 'ms': 'Malay', 'mi': 'Māori', 'sm': 'Samoan', 'to': 'Tongan', 'ja': 'Japanese', 'ko': 'Korean',
         'zh': 'Chinese', 'zh-Hant': 'Chinese (Traditional)', 'zh-Hans': 'Chinese (Simplified)', 'ar': 'Arabic', 'he': 'Hebrew',
         'ru': 'Russian', 'el': 'Greek', 'th': 'Thai'}

def name(tag):
    """A language tag's name ('en-US' → 'English', 'zh-Hant-TW' → 'Chinese (Traditional)'), or None when the table has no
    name for it (the caller says so in words, never shows the code)."""
    t = norm(tag) if tag else None
    if not t: return None
    parts = t.split('-')
    if len(parts) > 1 and f'{parts[0]}-{parts[1]}' in NAMES: return NAMES[f'{parts[0]}-{parts[1]}']
    return NAMES.get(parts[0])
