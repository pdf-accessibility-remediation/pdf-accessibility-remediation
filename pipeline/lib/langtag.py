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
         # #137 (dropped language answers): tags the prompt names or the AI gave with good reason, once refused
         'yue-Latn': 'Cantonese (Romanized)', 'grc-Latn': 'Ancient Greek (Romanized)', 'tpi': 'Tok Pisin',
         # #137, #140: words the stricter line-end join gives back as candidates (Javanese on performing, Anindilyakwa on translation)
         'jv': 'Javanese', 'aoi': 'Anindilyakwa',
         # #137, round 11: languages the AI named in the 27 reference books' answers (3 or more word forms each) and the
         # table lacked, each checked in the IANA language subtag registry (File-Date 2026-09-17). A specific language
         # stays itself, never its macrolanguage (bcl is Central Bikol, not bik). Not added: btk, a collection code
         # ("Batak languages"), not a language.
         'bcl': 'Central Bikol', 'ban': 'Balinese', 'su': 'Sundanese', 'min': 'Minangkabau', 'aly': 'Alyawarr',
         'bbc': 'Batak Toba', 'mak': 'Makasar', 'rar': 'Rarotongan', 'ks': 'Kashmiri', 'kk': 'Kazakh',
         'jv-Latn': 'Javanese (Latin script)',            # jv has no Suppress-Script (it has its own script too): kept as written
         'ryu-Latn': 'Okinawan (Romanized)', 'bo-Latn': 'Tibetan (Romanized)', 'hi-Latn': 'Hindi (Romanized)',
         'ar-Latn': 'Arabic (Romanized)', 'ks-Latn': 'Kashmiri (Romanized)', 'kk-Latn': 'Kazakh (Romanized)',
         'qaa': 'Placeholder (local use)'}

# The table's languages whose Suppress-Script in the IANA registry is Latn (File-Date 2026-09-17): for them a "-Latn"
# script subtag says nothing (BCP 47 says to leave it out), so "ms-Latn" is read as "ms" (#137, round 11). Romanizations of
# languages written in another script keep it (ja-Latn, bo-Latn, ryu-Latn), as does a language with no Suppress-Script.
SUPPRESS_LATN = {'ch', 'cs', 'da', 'de', 'en', 'es', 'fi', 'fj', 'fr', 'hu', 'id', 'it', 'la', 'mh', 'ms', 'nl', 'no', 'pl',
                 'pt', 'sm', 'sv', 'tl', 'to', 'tpi', 'tr', 'vi'}

def without_suppressed_script(tag):
    """'ms-Latn' → 'ms' (the script the registry suppresses for that language); any other value unchanged."""
    if isinstance(tag, str):
        parts = tag.split('-')
        if len(parts) == 2 and parts[1] == 'Latn' and parts[0] in SUPPRESS_LATN: return parts[0]
    return tag

# ISO 639-2 three-letter codes whose language has a two-letter ISO 639-1 code: BCP 47 uses the shortest (jpn → ja). The
# languages above and their neighbours; a three-letter code not listed here is left as it is (haw, chk, pon have no
# two-letter code).
SHORT = {'eng': 'en', 'fra': 'fr', 'fre': 'fr', 'deu': 'de', 'ger': 'de', 'spa': 'es', 'por': 'pt', 'ita': 'it', 'nld': 'nl',
         'dut': 'nl', 'lat': 'la', 'tgl': 'tl', 'vie': 'vi', 'ind': 'id', 'msa': 'ms', 'may': 'ms', 'mri': 'mi', 'mao': 'mi',
         'smo': 'sm', 'ton': 'to', 'jpn': 'ja', 'kor': 'ko', 'zho': 'zh', 'chi': 'zh', 'ara': 'ar', 'heb': 'he', 'rus': 'ru',
         'ell': 'el', 'gre': 'el', 'tha': 'th', 'san': 'sa', 'pli': 'pi', 'mah': 'mh', 'cha': 'ch', 'tah': 'ty', 'fij': 'fj',
         'bod': 'bo', 'tib': 'bo', 'mon': 'mn', 'hin': 'hi', 'urd': 'ur', 'fas': 'fa', 'per': 'fa', 'tur': 'tr', 'khm': 'km',
         'mya': 'my', 'bur': 'my', 'lao': 'lo', 'uig': 'ug', 'swe': 'sv', 'dan': 'da', 'nor': 'no', 'pol': 'pl', 'ces': 'cs',
         'cze': 'cs', 'hun': 'hu', 'fin': 'fi', 'jav': 'jv'}
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

# ------------------------------------------------------------------ a publisher's language name on its words
# Moved unchanged from apply.py (review 12, C): the review page shows the value a kept tag writes, from the same rule.
NON_LATIN = {'ja', 'zh', 'ko', 'yue', 'ru', 'uk', 'bg', 'sr', 'mk', 'be', 'el', 'ar', 'fa', 'ur', 'he', 'yi', 'th', 'lo', 'km', 'my',
             'hi', 'mr', 'ne', 'bn', 'ta', 'te', 'kn', 'ml', 'gu', 'pa', 'si', 'ka', 'hy', 'am', 'bo', 'mn'}
POLYNESIAN = {'mi', 'to', 'sm', 'ty', 'rap', 'mrq', 'mqm', 'mrv', 'mnv', 'rar', 'niu', 'tkl', 'tvl', 'wls', 'fud', 'pkp'}   # Polynesian languages (review 10, L1; Rennell-Bellona is mnv, review 12)
def name_misfit(code, text):
    """Why a language's name written as /Lang doesn't fit its words (review 08, M4), or None when nothing local says so:
    the script differs (a Latin-script language on Chinese characters, or the reverse), most words are Hawaiian in shape
    for a language that isn't Hawaiian or another Polynesian one ("Hungarian" on "Kaleo Mahoe Akana"), or a Hawaiian tag
    holds a word Hawaiian can't spell (the letter guard: "Sustʻāinable") or mostly English words. Never a guess at the
    right language: a person decides."""
    from lib import ocrwords, langcands
    words = [w for w in (ocrwords.core(x) for x in str(text or '').split()) if len(w) >= 2 and any(ch.isalpha() for ch in w)]
    if not words: return None
    p = code.split('-')[0].lower(); other = langcands.other_script(text)
    if other and p not in NON_LATIN: return f'its words are in {other}'
    if not other and p in NON_LATIN: return 'its words are in Latin script'
    if p == 'haw':
        bad = [w for w in words if ocrwords.not_hawaiian_letters(w)]
        if bad: return f'"{bad[0]}" is not spelled with Hawaiian letters'
        eng = [w for w in words if langcands.in_english(w) and not ocrwords.hawaiian_shape(w)]
        return 'most of its words are English' if len(eng) * 2 > len(words) else None     # "Oʻahu, a Giant Military Base" (review 10, L2)
    if p in POLYNESIAN: return None                    # Māori, Tongan, Samoan …: Hawaiian-shaped words are theirs too (review 10, L1)
    haw = [w for w in words if ocrwords.hawaiian_shape(w) and not langcands.in_english(w)]
    return 'its words look Hawaiian' if len(haw) * 2 >= len(words) else None

def kept_value(raw, text=''):
    """The /Lang a publisher's value carried by a tag-tree element leaves after apply.py's fix_lang_values (#118, review 12,
    C): a language tag in its shortest form; a language's name as its code when its words fit (name_misfit); anything else
    as written (a name that doesn't fit, or a value that is no tag), for a person."""
    tag = norm(raw)
    if tag is None:
        code = from_name(raw)
        return code if code and not name_misfit(code, text) else str(raw)
    return shortest(tag)
