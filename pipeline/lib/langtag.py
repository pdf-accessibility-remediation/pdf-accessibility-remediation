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
         'ru': 'Russian', 'el': 'Greek', 'th': 'Thai',
         # #118 (language tagging): every language the language step may write, so the pages never show a code
         'ja-Latn': 'Japanese (Romanized)', 'zh-Latn': 'Chinese (Romanized)', 'ko-Latn': 'Korean (Romanized)',
         'sa': 'Sanskrit', 'sa-Latn': 'Sanskrit (Romanized)', 'pi': 'Pali', 'pi-Latn': 'Pali (Romanized)', 'yue': 'Cantonese',
         'mh': 'Marshallese', 'chk': 'Chuukese', 'pon': 'Pohnpeian', 'ch': 'Chamorro', 'ty': 'Tahitian', 'fj': 'Fijian',
         'gil': 'Gilbertese', 'ceb': 'Cebuano', 'hil': 'Hiligaynon', 'pam': 'Kapampangan', 'pag': 'Pangasinan', 'war': 'Waray',
         'bo': 'Tibetan', 'mn': 'Mongolian', 'hi': 'Hindi', 'ur': 'Urdu', 'fa': 'Persian', 'tr': 'Turkish', 'km': 'Khmer',
         'my': 'Burmese', 'lo': 'Lao', 'ug': 'Uyghur', 'ain': 'Ainu', 'ryu': 'Okinawan', 'sv': 'Swedish', 'da': 'Danish',
         'no': 'Norwegian', 'pl': 'Polish', 'cs': 'Czech', 'hu': 'Hungarian', 'fi': 'Finnish', 'grc': 'Ancient Greek',
         'qaa': 'Placeholder (local use)'}

# ISO 639-2 three-letter codes whose language has a two-letter ISO 639-1 code: BCP 47 uses the shortest (jpn → ja). The
# languages above and their neighbours; a three-letter code not listed here is left as it is (haw, chk, pon have no
# two-letter code).
SHORT = {'eng': 'en', 'fra': 'fr', 'fre': 'fr', 'deu': 'de', 'ger': 'de', 'spa': 'es', 'por': 'pt', 'ita': 'it', 'nld': 'nl',
         'dut': 'nl', 'lat': 'la', 'tgl': 'tl', 'vie': 'vi', 'ind': 'id', 'msa': 'ms', 'may': 'ms', 'mri': 'mi', 'mao': 'mi',
         'smo': 'sm', 'ton': 'to', 'jpn': 'ja', 'kor': 'ko', 'zho': 'zh', 'chi': 'zh', 'ara': 'ar', 'heb': 'he', 'rus': 'ru',
         'ell': 'el', 'gre': 'el', 'tha': 'th', 'san': 'sa', 'pli': 'pi', 'mah': 'mh', 'cha': 'ch', 'tah': 'ty', 'fij': 'fj',
         'bod': 'bo', 'tib': 'bo', 'mon': 'mn', 'hin': 'hi', 'urd': 'ur', 'fas': 'fa', 'per': 'fa', 'tur': 'tr', 'khm': 'km',
         'mya': 'my', 'bur': 'my', 'lao': 'lo', 'uig': 'ug', 'swe': 'sv', 'dan': 'da', 'nor': 'no', 'pol': 'pl', 'ces': 'cs',
         'cze': 'cs', 'hun': 'hu', 'fin': 'fi'}
DEPRECATED = {'iw', 'in', 'jw', 'ji', 'mo'}      # replaced by he, id, jv, yi, ro

def shortest(tag):
    """The tag with its primary language subtag in its shortest form ('jpn-Latn' → 'ja-Latn'), or None if not a tag."""
    t = norm(tag) if tag else None
    if not t: return None
    parts = t.split('-')
    parts[0] = SHORT.get(parts[0], parts[0])
    return '-'.join(parts)

def valid_part(tag):
    """True for a tag the language step may write: well formed and in canonical case, its language subtag in its shortest
    form, not deprecated, and a language this module can name (or qaa, reserved for local use). Refuses 'jp', 'cn',
    'eng', 'iw' (review 02, L2)."""
    if not isinstance(tag, str) or norm(tag) != tag or shortest(tag) != tag: return False
    parts = tag.split('-')
    if parts[0] in DEPRECATED: return False
    if parts[0] == 'qaa': return True
    return name(tag) is not None and (len(parts) == 1 or f'{parts[0]}-{parts[1]}' in NAMES or len(parts[1]) == 2 or parts[1].isdigit())

def name(tag):
    """A language tag's name ('en-US' → 'English', 'zh-Hant-TW' → 'Chinese (Traditional)'), or None when the table has no
    name for it (the caller says so in words, never shows the code)."""
    t = norm(tag) if tag else None
    if not t: return None
    parts = t.split('-')
    if len(parts) > 1 and f'{parts[0]}-{parts[1]}' in NAMES: return NAMES[f'{parts[0]}-{parts[1]}']
    return NAMES.get(parts[0])

# A language's name written where a code belongs ("Hawaiian", "Marshallese "): the code, only when the name has one
# certain meaning (#118; review 02 of the scoping: hawaii3 writes "Hawaii", "Hawaiian", "Marshallese"). "Hawaii" is the
# place's name, used by that publisher for the language; no other place name is read as a language.
NAME_ALIASES = {'hawaii': 'haw', 'hawai': 'haw', "hawai'i": 'haw', 'hawaiʻi': 'haw', 'hawai‘i': 'haw', 'olelo hawaii': 'haw', 'ʻōlelo hawaiʻi': 'haw',
                'mandarin': 'zh', 'chinese': 'zh', 'cantonese': 'yue'}

def from_name(value):
    """The code for a language name written as a value ('Hawaiian' → 'haw', 'Japanese' → 'ja'), case and spaces ignored;
    None for anything else (never guessed)."""
    v = ' '.join(str(value or '').split()).strip().lower()
    if not v: return None
    if v in NAME_ALIASES: return NAME_ALIASES[v]
    plain = {n.lower(): c for c, n in NAMES.items() if '(' not in n and c != 'qaa'}
    return plain.get(v)
