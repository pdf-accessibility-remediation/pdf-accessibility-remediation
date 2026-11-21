"""tools/dict_measure.py (#141, a measurement): the sponsors' rules as the tool applies them, on made-up data. No download
is needed: the lists here are tiny, written in the test."""
import os, sys
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.join(PIPE, 'tools'))
import dict_measure as dm  # noqa: E402


def test_latin_words_are_matched_without_marks_and_with_u_for_v():
    assert dm.latin_norm('Dīvīsa') == 'diuisa' and dm.latin_norm('Iūlius') == 'iulius' and dm.latin_norm('jam,') == 'iam'
    assert dm.plain('“Kenkyū,”') == 'kenkyū'
    assert dm.latin_norm('Cæsar') == 'caesar' and dm.latin_norm('diŋ') == '' and dm.latin_norm('láɪ') == ''


def test_whitaker_stem_and_ending_of_one_class():
    dictline = ['dic'.ljust(19) + 'dic'.ljust(19) + 'dix'.ljust(19) + 'dict'.ljust(19) + 'V      3 1 TRANS          X X X A O say;',
                'part'.ljust(19) + 'part'.ljust(19) + ''.ljust(19) + ''.ljust(19) + 'N      3 3 F T          X X X A O part;']
    inflects = ['V      3 1 PRES  ACTIVE  IND  1 S  1 1 o             X A',
                'VPAR   0 0 NOM S F PERF PASSIVE PPL 4 1 a            X A',
                'N      3 3 NOM P C  2 2 es        X A']
    stems, ends = dm.whitaker_parse(dictline, inflects)
    assert dm.whitaker_match('dico', stems, ends) and dm.whitaker_match('dicta', stems, ends)    # a participle on the verb's 4th stem
    assert dm.whitaker_match('partes', stems, ends)
    assert not dm.whitaker_match('parto', stems, ends) and not dm.whitaker_match('house', stems, ends)


LAT = {'magna', 'cum', 'laude', 'gallia', 'est', 'omnis', 'in', 'uitro', 'de'}
def is_lat(w): return dm.latin_norm(w) in LAT


def test_a_word_is_decided_only_inside_a_multi_word_latin_span():
    toks = 'the cells grew in vitro over days'.split()
    assert dm.decide_latin_word('vitro', toks, 4, is_lat) == 'span'       # "in vitro": in is Latin too
    toks = 'it is est for the record'.split()
    assert dm.decide_latin_word('est', toks, 2, is_lat) == 'single'       # alone: counted, never decided
    assert dm.decide_latin_word('omnis gallia', [], 0, is_lat) == 'span'  # a passage: every word Latin
    assert dm.decide_latin_word('house', 'a house'.split(), 1, is_lat) is None


def test_a_short_word_shared_with_english_is_never_decided_alone():
    assert dm.decide_latin_word('de', 'the de facto rule'.split(), 1, lambda w: dm.latin_norm(w) in {'de'}) == 'short'
    assert dm.decide_latin_word('in', 'grew in vitro'.split(), 1, is_lat) == 'span'


def test_the_phrase_pass_takes_whole_phrases_only_longest_first():
    hits = dm.phrase_hits('He graduated magna cum laude, in vitro tests; the vitro alone; per sea')
    assert [h[2] for h in hits] == ['magna cum laude', 'in vitro'] or sorted(h[2] for h in hits) == ['in vitro', 'magna cum laude']
    assert not any(h[2] == 'cum laude' for h in hits)                      # inside the longer phrase, not again


def test_gbif_pairs_need_a_listed_genus_and_a_listed_binomial():
    genera, species = {'Metrosideros', 'Homo'}, {'Metrosideros polymorpha', 'Homo sapiens'}
    toks = 'The Metrosideros polymorpha grew; Homo erectus and Metrosideros (shrub) here.'.split()
    assert [p[2] for p in dm.gbif_pairs(toks, genera, species)] == ['Metrosideros polymorpha']


def test_the_review_sheet_is_filled_from_known_answers():
    rows = [{'form': 'vitro', 'places': 9}, {'form': 'hale', 'places': 12}, {'form': 'pele', 'places': 1}, {'form': 'ignotum', 'places': 2}]
    ans = {'vitro': 'la', 'hale': 'haw', 'pele': 'haw'}
    got = {r['form']: r['decision'] for r in dm.fill_sheet(rows, ans.get, stop_min=3)}
    assert got == {'vitro': 'approve', 'hale': 'stoplist', 'pele': 'reject', 'ignotum': ''}


def test_answers_agree_by_language_with_or_without_a_script():
    assert dm.same('la', 'la') and dm.same('ja-Latn', 'ja-Latn') and dm.same('ja', 'ja-Jpan')
    assert not dm.same('ja-Latn', 'ja-Hira') and not dm.same('la', 'English') and not dm.same('la', None)


def test_tally_counts_right_and_wrong_by_language():
    t = dm.tally([('la', 'la'), ('la', 'English'), ('haw', 'haw')])
    assert t['decided'] == 3 and t['right'] == 2 and t['wrong'] == 1 and t['by_lang'] == {'la': [1, 1], 'haw': [1, 0]}


def test_lewis_short_headwords_are_read_from_the_latin_orth_lines(tmp_path):
    (tmp_path / 'lewis-short').mkdir()
    (tmp_path / 'lewis-short' / 'lat.ls.perseus-eng2.xml').write_text(
        '<entryFree><orth lang="la" extent="full">Dīvīsus</orth>, a, um</entryFree>\n'
        '<entryFree><orth extent="full" lang="la">jam</orth> <orth lang="greek">nai</orth></entryFree>\n', encoding='utf-8')
    assert dm.build_lewis_short(str(tmp_path)) == {'headwords': 2}
    assert dm._read(str(tmp_path / 'lewis-short' / '_lists' / 'latin.txt')) == {'diuisus', 'iam'}


def test_ncbi_names_keep_genera_and_binomials_of_scientific_names_only(tmp_path):
    import io, tarfile
    (tmp_path / 'ncbi').mkdir()
    nodes = '1\t|\t1\t|\tgenus\t|\n2\t|\t1\t|\tspecies\t|\n3\t|\t1\t|\tspecies\t|\n'
    names = ('1\t|\tMetrosideros\t|\t\t|\tscientific name\t|\n2\t|\tMetrosideros polymorpha\t|\t\t|\tscientific name\t|\n'
             '2\t|\tohia lehua\t|\t\t|\tcommon name\t|\n3\t|\tuncultured bacterium\t|\t\t|\tscientific name\t|\n')
    with tarfile.open(tmp_path / 'ncbi' / 'taxdump.tar.gz', 'w:gz') as t:
        for n, s in (('nodes.dmp', nodes), ('names.dmp', names)):
            b = s.encode(); i = tarfile.TarInfo(n); i.size = len(b); t.addfile(i, io.BytesIO(b))
    assert dm.build_ncbi(str(tmp_path)) == {'genera': 1, 'species': 1}


def test_catalogue_of_life_reads_genus_and_epithet_by_rank(tmp_path):
    import zipfile
    (tmp_path / 'col').mkdir()
    rows = ['dwc:taxonID\tdwc:scientificName\tdwc:taxonRank\tdwc:genericName\tdwc:specificEpithet',
            '1\tHomo\tgenus\tHomo\t', '2\tHomo sapiens Linnaeus\tspecies\tHomo\tsapiens', '3\tHominidae\tfamily\t\t']
    with zipfile.ZipFile(tmp_path / 'col' / 'latest_dwca.zip', 'w') as z: z.writestr('Taxon.tsv', '\n'.join(rows) + '\n')
    assert dm.build_col(str(tmp_path)) == {'genera': 1, 'species': 1}
    assert dm._read(str(tmp_path / 'col' / '_lists' / 'species.txt')) == {'Homo sapiens'}


def test_a_name_is_checked_in_each_list_on_its_own():
    genera, species = {'Homo'}, {'Homo sapiens'}
    ep = {'sapiens': {'Homo sapiens'}}
    assert dm.name_checked('Homo sapiens', 2, genera, species, ep) and dm.name_checked('H. sapiens', 2, genera, species, ep)
    assert dm.name_checked('Homo', 1, genera, species, ep) and not dm.name_checked('Homo erectus', 2, genera, species, ep)
