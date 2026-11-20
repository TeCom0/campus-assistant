"""The fixture check's guards and comparisons (app/evaluation/run_fixture_check.py).

The check itself runs on campus_scratch by hand (A2.4 step 7); this tests that it can't
run anywhere else, and that its comparisons find what they should.
"""

from app import config
from app.evaluation import run_fixture_check as check


def _snapshot(ranks: dict, results: dict | None = None, counts: dict | None = None) -> dict:
    return {
        "searches": {
            key: {"rank": rank, "results": (results or {}).get(key, [])}
            for key, rank in ranks.items()
        },
        "chunk_counts": counts or {},
    }


def test_run_refuses_any_database_but_the_scratch_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "POSTGRES_DB", "campus")
    assert check.run(tmp_path / "out.txt") == 2
    assert "Nothing changed" in capsys.readouterr().out
    assert not (tmp_path / "out.txt").exists()


def test_setup_refuses_to_copy_the_scratch_database_into_itself(monkeypatch):
    monkeypatch.setattr(config, "POSTGRES_DB", check.SCRATCH_DB)
    assert check.setup() == 2


def test_a_hit_lost_at_3_or_5_fails_coexistence_and_rank_changes_are_reported():
    real = [{"id": "q"}]
    methods = list(check.METHODS)
    s0 = _snapshot({f"q | {m}": 2 for m in methods})
    s3 = _snapshot({f"q | {m}": 2 for m in methods} | {f"q | {methods[0]}": 4})
    lost, changed = check.coexistence(real, s0, s3)
    assert lost == [f"q | {methods[0]}: hit@3 lost (rank 2 -> 4)"]
    assert changed == [f"q | {methods[0]}: rank 2 -> 4"]
    gone = _snapshot({f"q | {m}": 2 for m in methods} | {f"q | {methods[1]}": None})
    assert len(check.coexistence(real, s0, gone)[0]) == 2  # lost at 3 and at 5


def test_a_better_rank_is_reported_but_loses_nothing():
    real = [{"id": "q"}]
    s0 = _snapshot({f"q | {m}": 6 for m in check.METHODS})
    s3 = _snapshot({f"q | {m}": 1 for m in check.METHODS})
    lost, changed = check.coexistence(real, s0, s3)
    assert lost == [] and len(changed) == len(check.METHODS)


def test_withdrawal_differences_compare_results_exactly_and_other_editions_counts():
    before = _snapshot({"a": 1}, {"a": [("x", 0, "0.5")]}, {"x": 3})
    same = _snapshot({"a": 1}, {"a": [("x", 0, "0.5")]}, {"x": 3, "fixture": 2})
    assert check.differences(before, same, "fixture") == []
    score = _snapshot({"a": 1}, {"a": [("x", 0, "0.50000001")]}, {"x": 3})
    assert check.differences(before, score, "fixture") == ["a"]
    count = _snapshot({"a": 1}, {"a": [("x", 0, "0.5")]}, {"x": 4})
    assert check.differences(before, count, "fixture") == ["chunk counts: {'x': 3} -> {'x': 4}"]
