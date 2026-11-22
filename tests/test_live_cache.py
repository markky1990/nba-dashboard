"""Live scores: an old copy is returned at once and refreshed in the background, so a page never waits for ESPN."""
import time, live

def test_old_copy_returned_at_once_and_refreshed_in_background():
    live._cache.clear(); calls = []
    def slow(): calls.append(1); time.sleep(0.3); return len(calls)
    assert live.cached("k", 10, slow) == 1                      # first time: fetched now
    live._cache["k"] = (time.time() - 20, 1)                     # make it a little old
    t = time.time(); assert live.cached("k", 10, slow) == 1; assert time.time() - t < 0.1     # old copy straight away
    assert live.cached("k", 10, slow) == 1 and len(calls) == 2   # only one refresh running at a time
    time.sleep(0.5); assert live.cached("k", 10, slow) == 2      # fresh copy in place


def test_very_old_copy_is_fetched_again_first():
    live._cache.clear(); live._cache["k"] = (time.time() - 3600, "in-game numbers")       # nobody watched for an hour; the game has finished since
    assert live.cached("k", 5, lambda: "final numbers") == "final numbers"
    assert live._cache["k"][1] == "final numbers"

def test_very_old_copy_kept_when_espn_fails():
    live._cache.clear(); live._cache["k"] = (time.time() - 3600, "last good")
    def boom(): raise RuntimeError("ESPN down")
    assert live.cached("k", 5, boom) == "last good"
