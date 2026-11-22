"""#167 (whole-book work redone per item), memory: a single run of a book over 1,000 pages runs alone in the app, as a batch
does: it starts only when nothing counted runs, and nothing counted starts while it runs (webapp/jobs.py LONG_PAGES).
Made-up PDFs of blank pages; the dispatcher's start is replaced, so nothing runs."""
import os, sys, json
import pikepdf
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from webapp import jobs  # noqa: E402


def pdf(path, n):
    p = pikepdf.new()
    for _ in range(n): p.add_blank_page()
    p.save(path); return str(path)


def setup(tmp_path, monkeypatch):
    J = str(tmp_path / 'jobs'); os.makedirs(os.path.join(J, 'jobs'), exist_ok=True)
    started = []
    def fake_start(J_, job):
        job.update(status='running', started=jobs.now(), pid=1, pgid=1); jobs.save(J_, job); started.append(job['run'])
    monkeypatch.setattr(jobs, '_start', fake_start)
    monkeypatch.setattr(jobs, 'group_alive', lambda J_, j: True)
    return J, started


def test_a_long_book_runs_alone(tmp_path, monkeypatch):
    J, started = setup(tmp_path, monkeypatch)
    s = {'max_jobs': 3, 'runs': str(tmp_path / 'runs')}
    small, big = pdf(tmp_path / 'a.pdf', 3), pdf(tmp_path / 'b.pdf', jobs.LONG_PAGES + 1)
    a = jobs.create(J, 'run', 'a/x', ['bash', 'run_api.sh', small, 'a', 'x'], {})
    b = jobs.create(J, 'run', 'b/x', ['bash', 'run_api.sh', big, 'b', 'x'], {})
    c = jobs.create(J, 'run', 'c/x', ['bash', 'run_api.sh', small, 'c', 'x'], {})
    assert b['pages'] == jobs.LONG_PAGES + 1 and a['pages'] == 3
    jobs.tick(J, s)
    assert started == ['a/x']                        # the long book waits for the small one; the newer small one waits behind it
    a = next(j for j in jobs.all_jobs(J) if j['run'] == 'a/x'); a.update(status='done', ended=jobs.now(), exit=0); jobs.save(J, a)
    jobs.tick(J, s)
    assert started == ['a/x', 'b/x']                 # alone now
    jobs.tick(J, s)
    assert started == ['a/x', 'b/x']                 # nothing starts beside it
    b = next(j for j in jobs.all_jobs(J) if j['run'] == 'b/x'); b.update(status='done', ended=jobs.now(), exit=0); jobs.save(J, b)
    jobs.tick(J, s)
    assert started == ['a/x', 'b/x', 'c/x']


def test_books_up_to_the_limit_share_places(tmp_path, monkeypatch):
    J, started = setup(tmp_path, monkeypatch)
    s = {'max_jobs': 3, 'runs': str(tmp_path / 'runs')}
    for k in 'abc': jobs.create(J, 'run', f'{k}/x', ['bash', 'run_api.sh', pdf(tmp_path / f'{k}.pdf', jobs.LONG_PAGES), k, 'x'], {})
    jobs.tick(J, s)
    assert sorted(started) == ['a/x', 'b/x', 'c/x']



def test_a_job_naming_no_pdf_takes_its_page_count_from_the_run_folder(tmp_path, monkeypatch):
    """Review 04 M5: "Apply session N" of a run whose input is a copy names no PDF; its run folder's record says how long
    the book is, so a long one still runs alone."""
    J, started = setup(tmp_path, monkeypatch)
    R = tmp_path / 'runs' / 'big' / 'x'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'pages': jobs.LONG_PAGES + 300}}))
    j = jobs.create(J, 'apply', 'big/x', ['python3', 'review_workorder.py', str(R), '--apply'], {}, R=str(R))
    assert j['pages'] == jobs.LONG_PAGES + 300 and jobs.long_book(j)
