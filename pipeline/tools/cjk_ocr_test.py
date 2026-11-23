"""cjk_ocr_test.py: the CJK OCR test set and its scoring (#119). Builds synthetic test pages, runs Tesseract the way
intake does and with the local improvements, sends pages or hard lines to an AI model (paid), matches page readings
back to Tesseract's lines (lib/cjkocr.py) and scores everything on CJK characters: read, invented, CER.

    python3 tools/cjk_ocr_test.py synth OUT                      synthetic pages and their answer key (free; macOS fonts)
    python3 tools/cjk_ocr_test.py ocr OUT VARIANT [--book-set D]  Tesseract over the test pages (free): today | cjk-only |
                                                                 vert | hanja | 2pass | 2pass-conf
    python3 tools/cjk_ocr_test.py noruby OUT RESULT             a result with the furigana lines dropped (free)
    python3 tools/cjk_ocr_test.py ai OUT page|lines MODEL [--max-usd N] [--total-usd N] [--run K] [--dry-run]   (paid)
    python3 tools/cjk_ocr_test.py align OUT RESULT-OF-PAGES     page readings matched back to Tesseract's lines (free)
    python3 tools/cjk_ocr_test.py score OUT RESULT ...          read / invented / CER per group

The synthetic pages (vertical Japanese and Chinese, Japanese with furigana, Japanese only, Korean with Hanja) use text
written for this test, so they may be committed; their answer key is the text typeset. Pages made from books (the
born-digital test set of 2026-11-12: --book-set DIR with <group>.pdf and truth.json) stay local, under OUT (runs/, never
committed). Paid requests go to OpenRouter with data collection denied, are cached by their exact content (a rerun never
pays twice) and logged in OUT/spend-*.json; a run refuses over its own cap (--max-usd) or the test's total (--total-usd).
Results of 2026-11-22: docs/cjk-ocr.md.
"""
import sys, os, json, re, io, csv, random, glob, subprocess, collections, hashlib, base64, time, urllib.request, urllib.error
from io import BytesIO
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cjkocr as C  # noqa: E402
import pypdfium2  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps  # noqa: E402

# ================================================================ synthetic pages
DPI = 200
W, H = int(8.5 * DPI), int(11 * DPI)
YU = (glob.glob('/System/Library/AssetsV2/com_apple_MobileAsset_Font8/*/AssetData/YuMincho.ttc') or [None])[0]
FONTS = {
    'mincho': ('/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 0),
    'yumincho': (YU, 0) if YU else ('/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 0),
    'gothic': ('/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc', 0),
    'myungjo': ('/System/Library/Fonts/Supplemental/AppleMyungjo.ttf', 0),
    'sdgothic': ('/System/Library/Fonts/AppleSDGothicNeo.ttc', 0),
    'songti_tc': ('/System/Library/Fonts/Supplemental/Songti.ttc', 5),
}
def font(name, size):
    p, i = FONTS[name]; return ImageFont.truetype(p, size, index=i)

# ---- the texts, written for this test (no book content)
JA_1 = ('図書館の朝は静かである。開館の鐘が鳴ると、近所の学生や年配の利用者が少しずつ集まってくる。窓際の席はすぐに埋まり、'
        '新聞を広げる人、辞書を引く人、ノートに細かい字を書き込む人がいる。職員は返却された本を棚に戻しながら、'
        '利用者の質問に丁寧に答えていく。古い地図を探している人には郷土資料の部屋を案内し、子どもには絵本の場所を教える。'
        '午後になると雨が降り始め、館内はさらに静かになった。濡れた傘を入口に立てかけて、また一人、本を読みに来た。'
        '閉館の時間が近づくと、職員は机の上に残された本を集め、明日の準備を始める。')
JA_2 = ('島の港には小さな市場がある。朝早くから漁師が魚を運び、店の人は氷を砕いて並べていく。観光客は珍しい貝や海藻を眺め、'
        '値段を尋ねては写真を撮る。昼には市場の奥の食堂で、焼いた魚と味噌汁と白いご飯を食べることができる。'
        '食堂の主人は七十歳を過ぎているが、毎日休まずに台所に立っている。若い頃は遠い国の船に乗っていたという。'
        '壁には古い写真と海図が飾られ、客はそれを見ながら主人の話を聞く。夕方になると風が強くなり、船は港に戻ってくる。')
JA_RUBY = ('{今日|きょう}は{朝|あさ}から{風|かぜ}が{強|つよ}く、{山|やま}の{上|うえ}には{白|しろ}い{雲|くも}がかかっていた。'
           '{祖母|そぼ}は{縁側|えんがわ}に{座|すわ}って、{庭|にわ}の{柿|かき}の{木|き}を{眺|なが}めている。'
           '{秋|あき}になると{実|み}が{赤|あか}く{熟|じゅく}し、{近所|きんじょ}の{子供|こども}たちが{取|と}りに{来|く}る。'
           '{私|わたし}は{台所|だいどころ}でお{茶|ちゃ}を{入|い}れ、{祖母|そぼ}の{隣|となり}に{腰|こし}を{下|お}ろした。'
           '{遠|とお}くの{田|た}んぼでは{稲刈|いねか}りが{始|はじ}まり、{機械|きかい}の{音|おと}が{聞|き}こえてくる。'
           '{祖母|そぼ}は{昔|むかし}の{村|むら}の{話|はなし}を{始|はじ}めた。{電気|でんき}もなく、{夜|よる}は{月|つき}の{光|ひかり}で{本|ほん}を{読|よ}んだという。')
KO_1 = ('大韓民國의 首都 서울에는 오래된 宮闕과 現代的인 建物이 함께 있다. 朝鮮 時代의 宮闕은 오늘날 博物館과 公園으로 '
        '使用되며, 市民과 觀光客이 自由롭게 訪問한다. 圖書館에서는 古文書와 族譜를 硏究하는 學者들을 볼 수 있다. '
        '漢字는 오랫동안 公式 文書에 使用되었으며, 지금도 新聞의 題目이나 法律 用語에 남아 있다. 學生들은 中學校에서 '
        '基礎 漢字를 배우고, 大學에서는 專攻에 따라 더 많은 漢字를 익힌다.')
KO_2 = ('地方 都市의 市場은 아침 일찍 門을 연다. 農夫들은 新鮮한 野菜와 果日을 가지고 오고, 商人들은 價格을 적은 紙를 붙인다. '
        '市場 안에는 오래된 食堂이 있어서 國밥과 김치를 便하게 먹을 수 있다. 主人은 四十年 동안 같은 자리에서 장사를 했다고 '
        '말한다. 午後가 되면 學生들이 下校하면서 떡과 飮料를 사 간다. 저녁에는 地域 住民들이 모여 會議를 열고, 市場의 '
        '未來와 環境 問題에 대해 意見을 나눈다.')
ZH_T = ('臺灣的圖書館大多在早上九點開門。週末的時候，許多家長會帶著孩子來借書，兒童閱覽室總是十分熱鬧。'
        '大學生則喜歡在安靜的自習室裡準備考試，有的人從早到晚都不離開座位。館員除了整理書架以外，還要協助讀者查詢資料，'
        '並且舉辦各種講座與展覽。最近幾年，許多圖書館開始提供電子書與線上資料庫，讀者在家裡也能閱讀報紙和期刊。'
        '不過，仍然有不少老年人習慣親自到館，坐在窗邊翻閱當天的報紙，度過一個悠閒的上午。')

RUBY = re.compile(r'\{([^|}]+)\|([^}]+)\}')
def base_text(t): return RUBY.sub(lambda m: m.group(1), t)

def scanned(img, rnd):
    """Grayscale, slight skew, blur, speckle and JPEG: the same office-scanner look as the born-digital test pages."""
    g = ImageOps.grayscale(img)
    g = g.rotate(rnd.uniform(-0.8, 0.8), resample=Image.BICUBIC, expand=False, fillcolor=255)
    g = g.filter(ImageFilter.GaussianBlur(0.7))
    noise = Image.effect_noise(g.size, 18)
    px, nz = g.load(), noise.load(); w, h = g.size
    for y in range(h):
        for x in range(0, w, 3):
            v = px[x, y] + (nz[x, y] - 128) // 2
            px[x, y] = 0 if v < 0 else 255 if v > 255 else v
    b = BytesIO(); g.save(b, 'JPEG', quality=60); b.seek(0)
    return Image.open(b).convert('L')

def horizontal(text, fname, size, margin=1.0, lead=1.7, ruby=False):
    img = Image.new('L', (W, H), 255); d = ImageDraw.Draw(img); f = font(fname, size); rf = font(fname, int(size * 0.45))
    x0, y = int(margin * DPI), int(margin * DPI) + (int(size * 0.55) if ruby else 0); right = W - int(margin * DPI)
    toks = []                                                   # (base, ruby or None)
    pos = 0
    for m in RUBY.finditer(text):
        toks += [(c, None) for c in text[pos:m.start()]]; toks.append((m.group(1), m.group(2))); pos = m.end()
    toks += [(c, None) for c in text[pos:]]
    x = x0
    for base, rb in toks:
        if base == ' ':
            x += size // 3; continue
        bw = d.textlength(base, font=f)
        if x + bw > right: x = x0; y += int(size * lead) + (int(size * 0.5) if ruby else 0)
        d.text((x, y), base, font=f, fill=0)
        if rb:
            rw = d.textlength(rb, font=rf); d.text((x + (bw - rw) / 2, y - int(size * 0.55)), rb, font=rf, fill=0)
        x += bw
    return img

VERT = {'。': '︒', '、': '︑', '「': '﹁', '」': '﹂', '，': '︐', '：': '︓', '（': '︵', '）': '︶'}
ROTATE = set('ー－—…')
def vertical(text, fname, size, margin=1.0, col=1.6):
    img = Image.new('L', (W, H), 255); d = ImageDraw.Draw(img); f = font(fname, size)
    x = W - int(margin * DPI) - size; y0 = int(margin * DPI); y = y0; bottom = H - int(margin * DPI)
    for c in text:
        if y + size > bottom: y = y0; x -= int(size * col)
        g = VERT.get(c, c)
        if c in ROTATE:
            t = Image.new('L', (size, size), 255); ImageDraw.Draw(t).text((0, 0), c, font=f, fill=0)
            img.paste(t.rotate(-90, fillcolor=255), (x, y))
        else:
            d.text((x, y), g, font=f, fill=0)
        y += size
    return img

PAGES = {   # group: [(text, kind, font, size)]
    'ja-vertical': [(JA_1, 'vertical', 'mincho', 34), (JA_2, 'vertical', 'yumincho', 30)],
    'ja-furigana': [(JA_RUBY, 'ruby', 'mincho', 34)],
    'ja-only': [(JA_2 + JA_1, 'horizontal', 'gothic', 28)],
    'ko-hanja': [(KO_1, 'horizontal', 'myungjo', 30), (KO_2, 'horizontal', 'sdgothic', 28)],
    'zh-traditional-vertical': [(ZH_T, 'vertical', 'songti_tc', 32)],
}


def synth(out):
    os.makedirs(out, exist_ok=True); rnd = random.Random(119); truth = {}
    for group, pages in PAGES.items():
        imgs, rows = [], []
        for text, kind, fname, size in pages:
            img = vertical(text, fname, size) if kind == 'vertical' else horizontal(text, fname, size, ruby=(kind == 'ruby'))
            imgs.append(scanned(img.convert('RGB'), rnd))
            rows.append({'source': f'synthetic:{kind}:{fname}', 'pdf_page': None, 'text': base_text(text),
                         **({'ruby': ''.join(m.group(2) for m in RUBY.finditer(text))} if kind == 'ruby' else {})})
        imgs[0].save(os.path.join(out, f'{group}.pdf'), 'PDF', resolution=DPI, save_all=True, append_images=imgs[1:])
        truth[group] = rows
        print(group, len(imgs), 'pages')
    json.dump(truth, open(os.path.join(out, 'truth.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ================================================================ the test set
CJK_LANG = {'zh-simplified': 'chi_sim', 'zh-traditional': 'chi_tra', 'ko': 'kor', 'ja-in-english': 'jpn', 'ja-only': 'jpn',
            'ja-furigana': 'jpn', 'ko-hanja': 'kor', 'ja-vertical': 'jpn', 'zh-traditional-vertical': 'chi_tra'}
VERTICAL = {'ja-vertical', 'zh-traditional-vertical'}
CJK_SPACE = re.compile(r'(?<=[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]) (?=[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af])')
RENDER_DPI = 300

class Set:
    """The test pages: OUT/synth (built by synth) and, when given, the local book set (--book-set)."""
    def __init__(self, out, book_set=None):
        self.out = out; self.groups = collections.OrderedDict()
        for d in [book_set, os.path.join(out, 'synth')]:
            if not d or not os.path.exists(os.path.join(d, 'truth.json')): continue
            t = json.load(open(os.path.join(d, 'truth.json'), encoding='utf-8'))
            for g, rows in t.items():
                if os.path.exists(os.path.join(d, f'{g}.pdf')): self.groups[g] = (os.path.join(d, f'{g}.pdf'), rows)
        if not self.groups: sys.exit(f'no test pages: run "synth {out}/synth" first (and give --book-set for the book pages)')
    def pages(self, g): return len(pypdfium2.PdfDocument(self.groups[g][0]))
    def truth(self, g): return self.groups[g][1]
    def image(self, g, k):
        p = os.path.join(self.out, 'pages', g, f'p{k + 1}.png')
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            pypdfium2.PdfDocument(self.groups[g][0])[k].render(scale=RENDER_DPI / 72).to_pil().convert('L').save(p)
        return p

# ================================================================ Tesseract
def tess_lines(img, lang, psm=3):
    """[{key, box, words: [(text, conf)], text}] in Tesseract's reading order."""
    tsv = subprocess.run(['tesseract', img, '-', '-l', lang, '--psm', str(psm), 'tsv'], capture_output=True, text=True).stdout
    lines = collections.OrderedDict()
    for r in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
        if r.get('level') != '5' or not (r.get('text') or '').strip(): continue
        key = (int(r['block_num']), int(r['par_num']), int(r['line_num']))
        L = lines.setdefault(key, {'key': key, 'words': [], 'box': [10 ** 9, 10 ** 9, 0, 0]})
        x, y, w, h = (int(r[c]) for c in ('left', 'top', 'width', 'height'))
        L['words'].append((r['text'], float(r['conf'])))
        b = L['box']; L['box'] = [min(b[0], x), min(b[1], y), max(b[2], x + w), max(b[3], y + h)]
    return [{**L, 'text': CJK_SPACE.sub('', ' '.join(w for w, _ in L['words']))} for L in lines.values()]

def lang_of(group, variant):
    cjk = CJK_LANG[group]
    return {'today': f'{cjk}+eng', 'cjk-only': cjk, 'vert': f'{cjk}_vert+{cjk}+eng' if group in VERTICAL else f'{cjk}+eng',
            'hanja': f'{cjk}+chi_tra+eng' if cjk == 'kor' else f'{cjk}+eng'}[variant]

def run_ocr(S, variant):
    """OUT/ocr-<variant>.json {group: [[line, ...] per page]}. 2pass: today, then each line holding CJK read again from its
    crop with the CJK language alone (psm 7; _vert and psm 5 on vertical groups); 2pass-conf: also lines with no CJK whose
    lowest word confidence is under 60 (jpn+eng reads some Japanese as Latin junk)."""
    base = 'today' if variant.startswith('2pass') else variant
    src = os.path.join(S.out, f'ocr-{base}.json')
    res = json.load(open(src, encoding='utf-8')) if variant.startswith('2pass') and os.path.exists(src) else {}
    for g in S.groups:
        if g not in res: res[g] = [tess_lines(S.image(g, k), lang_of(g, base)) for k in range(S.pages(g))]
        if not variant.startswith('2pass'): continue
        cjk, vert = CJK_LANG[g], g in VERTICAL
        for k, page in enumerate(res[g]):
            img = Image.open(S.image(g, k))
            for L in page:
                if not (C.CJK.search(L['text']) or (variant == '2pass-conf' and min(c for _, c in L['words']) < 60)): continue
                b, pad = L['box'], 8
                p = os.path.join(S.out, 'tmp-line.png')
                img.crop((max(0, b[0] - pad), max(0, b[1] - pad), min(img.width, b[2] + pad), min(img.height, b[3] + pad))).save(p)
                t = subprocess.run(['tesseract', p, '-', '-l', f'{cjk}_vert' if vert else cjk, '--psm', '5' if vert else '7'], capture_output=True, text=True).stdout
                t = CJK_SPACE.sub('', ' '.join(t.split()))
                if t and C.CJK.search(t): L['pass1'] = L['text']; L['text'] = t
        print(variant, g, sum(len(p) for p in res[g]), 'lines')
    json.dump(res, open(os.path.join(S.out, f'ocr-{variant}.json'), 'w', encoding='utf-8'), ensure_ascii=False)

def load(out, name):
    for p in (os.path.join(out, f'{name}.json'), os.path.join(out, f'ocr-{name}.json')):
        if os.path.exists(p): return json.load(open(p, encoding='utf-8'))
    sys.exit(f'no result {name} in {out}')

def noruby(out, name):
    d = load(out, name); n = 0
    for g, pages in d.items():
        for k, page in enumerate(pages):
            if isinstance(page, str): continue
            hs = sorted(L['box'][3] - L['box'][1] for L in page) or [0]; med = hs[len(hs) // 2]
            keep = [L for L in page if not C.is_ruby(L.get('local', L['text']), L['box'][3] - L['box'][1], med)]
            n += len(page) - len(keep); pages[k] = keep
    json.dump(d, open(os.path.join(out, f'{name}-noruby.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(name, 'furigana lines dropped:', n)

# ================================================================ AI readings (paid)
LINE_PROMPT = ('Each image is one line cut from a scanned page; the text may be Chinese, Japanese or Korean, mixed with English. '
               'Transcribe each line exactly as printed: the same characters (traditional or simplified as printed, Hanja as Hanja), '
               'the same punctuation, Latin text as printed. Do not translate, correct or complete anything. Leave out small '
               'pronunciation glosses printed above or beside characters (furigana, ruby). A vertical strip is one column, read top '
               'to bottom. If a character can\'t be read, write it as \u25a1. Answer with JSON only: {"lines": [{"n": <number>, "text": "..."}]}.')
PAGE_PROMPT = ('This is a scanned page; the text may be Chinese, Japanese or Korean, mixed with English. Transcribe all of the '
               'page\'s text exactly as printed, in reading order (vertical text: columns from right to left, each top to bottom), '
               'one printed line or column per line of output. Keep the characters as printed (traditional or simplified, Hanja as '
               'Hanja). Do not translate, correct or complete anything. Leave out furigana (ruby) and page headers and numbers. If a '
               'character can\'t be read, write \u25a1. Output only the text.')

def key():
    if os.environ.get('OPENROUTER_API_KEY'): return os.environ['OPENROUTER_API_KEY']
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for line in open(os.path.join(d, '.env'), encoding='utf-8'):
        if line.strip().startswith('OPENROUTER_API_KEY='): return line.split('=', 1)[1].strip().strip('"').strip("'")

def price(model):
    m = next(x for x in json.load(urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=30))['data'] if x['id'] == model)
    return float(m['pricing']['prompt']), float(m['pricing']['completion'])

def b64(path, long=None):
    im = Image.open(path).convert('L')
    if long and max(im.size) > long:
        s = long / max(im.size); im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()

def call(out, model, content, max_tokens, run=1):
    """One request, cached by its exact content: a rerun never pays twice."""
    h = hashlib.sha256(json.dumps([model, content, max_tokens, run], sort_keys=True).encode()).hexdigest()[:24]
    cp = os.path.join(out, 'cache', f'{h}.json')
    if os.path.exists(cp): r = json.load(open(cp)); r['cached'] = True; return r
    body = {'model': model, 'max_tokens': max_tokens, 'messages': [{'role': 'user', 'content': content}], 'usage': {'include': True},
            'provider': {'data_collection': 'deny'}, 'reasoning': {'effort': 'low'}}
    if not model.startswith('anthropic/'): body['temperature'] = 0
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Authorization': f'Bearer {key()}', 'Content-Type': 'application/json', 'X-Title': 'UH PDF remediation #119 test'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp: d = json.load(resp)
    u = d.get('usage') or {}; ch = (d.get('choices') or [{}])[0]
    r = {'text': (ch.get('message') or {}).get('content') or '', 'finish': ch.get('finish_reason'), 'in': u.get('prompt_tokens'),
         'out': u.get('completion_tokens'), 'cost': u.get('cost'), 'seconds': round(time.time() - t0, 1)}
    if r['text']: os.makedirs(os.path.dirname(cp), exist_ok=True); json.dump(r, open(cp, 'w'))
    return r

def spent(out): return sum(x.get('cost') or 0 for p in glob.glob(os.path.join(out, 'spend*.json')) for x in json.load(open(p)))

def hard(L, rule='conf'):
    """A line the AI reads in lines mode: it holds CJK, or its lowest word confidence is under 60; and (rule conf) its
    lowest word confidence is under 90 or its mean under 93."""
    confs = [c for _, c in L['words']]
    if not (C.CJK.search(L['text']) or C.CJK.search(L.get('pass1', '')) or min(confs) < 60): return False
    return rule == 'all' or min(confs) < 90 or sum(confs) / len(confs) < 93

def ai(S, mode, model, base='2pass-conf', cap=1.5, total=42.0, dry=False, run=1, per=20):
    pin, pout = price(model); tag = model.split('/')[-1] + (f'-run{run}' if run > 1 else '')
    res = load(S.out, base); jobs = []
    if mode == 'lines':
        cs = []
        for g, pages in res.items():
            for k, page in enumerate(pages):
                for n, L in enumerate(page):
                    if hard(L): cs.append((g, k, n))
        jobs = [cs[i:i + per] for i in range(0, len(cs), per)]
        est = len(jobs) * (per * 250 * pin + per * 180 * pout)
    else:
        jobs = [(g, k) for g in S.groups for k in range(S.pages(g))]
        est = len(jobs) * (2600 * pin + 5000 * pout)          # output doubled for reasoning tokens (measured: Gemini ~2x its text)
    print(f'{mode} {model}: {len(jobs)} requests, worst about ${est:.2f} (cap ${cap:.2f}); spent so far ${spent(S.out):.2f} of ${total:.2f}')
    if dry: return
    if est > cap or spent(S.out) + est > total: sys.exit('refusing: over the cap')
    pages_out = {g: ['' for _ in p] for g, p in res.items()} if mode == 'page' else res
    LG = os.path.join(S.out, f'spend-{mode}-{tag}.json'); ledger = json.load(open(LG)) if os.path.exists(LG) else []; run_cost = 0.0
    for j in jobs:
        if run_cost > cap: print('stopping: this run reached its cap'); break
        try:
            if mode == 'lines':
                content = [{'type': 'text', 'text': LINE_PROMPT}]
                img_cache = {}
                for n, (g, k, li) in enumerate(j, 1):
                    L = res[g][k][li]; b, pad = L['box'], 10
                    img = img_cache.setdefault((g, k), Image.open(S.image(g, k)))
                    p = os.path.join(S.out, 'lines', g, f'p{k + 1}', f'l{li + 1}.png'); os.makedirs(os.path.dirname(p), exist_ok=True)
                    img.crop((max(0, b[0] - pad), max(0, b[1] - pad), min(img.width, b[2] + pad), min(img.height, b[3] + pad))).save(p)
                    content += [{'type': 'text', 'text': f'Line {n}:'}, {'type': 'image_url', 'image_url': {'url': b64(p)}}]
                r = call(S.out, model, content, 300 + 120 * len(j), run)
                m = re.search(r'\{.*\}', r['text'], re.S); got = {}
                try: got = {int(x['n']): str(x.get('text') or '') for x in json.loads(m.group(0))['lines']} if m else {}
                except (ValueError, KeyError, TypeError): pass
                for n, (g, k, li) in enumerate(j, 1):
                    L = pages_out[g][k][li]; L.setdefault('local', L['text'])
                    if got.get(n, '').strip(): L['text'] = CJK_SPACE.sub('', got[n].strip()); L['ai'] = True
            else:
                g, k = j
                r = call(S.out, model, [{'type': 'text', 'text': PAGE_PROMPT}, {'type': 'image_url', 'image_url': {'url': b64(S.image(g, k), 2000)}}], 6000, run)
                pages_out[g][k] = '' if C.refused(r['text'], '\n'.join(L['text'] for L in res[g][k])) else r['text']
        except urllib.error.HTTPError as e: print('HTTP', e.code, e.read()[:300]); continue
        except (urllib.error.URLError, TimeoutError) as e: print('no reply', e); continue
        if r.get('cached'): continue
        run_cost += r['cost'] or 0
        ledger.append({'mode': mode, 'model': model, 'run': run, 'in': r['in'], 'out': r['out'], 'cost': r['cost'], 'finish': r['finish'], 'seconds': r['seconds']})
        json.dump(ledger, open(LG, 'w'), indent=1)
    p = os.path.join(S.out, f'ai-{mode}-{tag}.json'); json.dump(pages_out, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{mode} {model}: ${run_cost:.4f} this run; ${spent(S.out):.4f} in all -> {p}')

def align(out, name, base='ocr-2pass-conf-noruby'):
    """A page-readings result matched back to Tesseract's lines (lib/cjkocr.align_page) -> <name>-aligned, and per page
    the lines matched, the share and the AI text left unused."""
    lines, pages = load(out, base), load(out, name); res, stats = {}, []
    for g, pl in lines.items():
        res[g] = []
        for k, page in enumerate(pl):
            read, unused, share = C.align_page([L['text'] for L in page], pages[g][k])
            res[g].append([{**L, 'text': read.get(i, L['text']), **({'ai': True} if i in read else {})} for i, L in enumerate(page)])
            stats.append((g, k + 1, len(page), len(read), round(share, 2), len(unused), sum(len(C.norm(u)) for u in unused)))
    json.dump(res, open(os.path.join(out, f'{name}-aligned.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for s in stats: print(f'{s[0]:24s} p{s[1]:<3d} lines {s[2]:4d} matched {s[3]:4d} share {s[4]:.2f} unused {s[5]} lines, {s[6]} chars' + ('  -> a person' if s[4] < C.MATCH_MIN else ''))

def score(S, names):
    print(f"{'result':40s} {'group':24s} {'read':>7s} {'invented':>9s} {'CER':>7s} {'chars':>6s}")
    for name in names:
        d = load(S.out, name); tot = collections.Counter()
        for g in S.groups:
            if g not in d: continue
            texts = [x if isinstance(x, str) else '\n'.join(L['text'] for L in x) for x in d[g]]
            s = collections.Counter()
            for k, row in enumerate(S.truth(g)): s.update(C.score(row['text'], texts[k] if k < len(texts) else ''))
            tot.update(s); show(name, g, s)
        show(name, 'ALL', tot)

def show(name, g, s):
    print(f"{name:40s} {g:24s} {s['matched'] / max(1, s['ref']):7.1%} {(s['ocr'] - s['matched']) / max(1, s['ocr']):9.1%} {s['edits'] / max(1, s['ref']):7.1%} {s['ref']:6d}")

def main(argv):
    cmd, out = argv[0], argv[1]; opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    if cmd == 'synth': return synth(out)
    if cmd == 'noruby': return noruby(out, argv[2])
    if cmd == 'align': return align(out, argv[2])
    S = Set(out, opt('--book-set'))
    if cmd == 'ocr': return run_ocr(S, argv[2])
    if cmd == 'score': return score(S, [a for a in argv[2:] if not a.startswith('--') and a != opt('--book-set')])
    if cmd == 'ai': return ai(S, argv[2], argv[3], cap=float(opt('--max-usd', 1.5)), total=float(opt('--total-usd', 42)), dry='--dry-run' in argv, run=int(opt('--run', 1)))
    sys.exit(__doc__)

if __name__ == '__main__': main(sys.argv[1:])
