"""Sweet spot: Pts + Reb + Ast picks at 1.70-2.20 that beat the price after leaning halfway to the bookmaker; at most one per player, five a night."""
import datetime as dt
import pytest
import app

NOW = dt.datetime.now(dt.timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%MZ")
PAST, FUTURE = iso(NOW - dt.timedelta(minutes=20)), iso(NOW + dt.timedelta(hours=3))

def line(l, p_over, price, under=None, book="sportsbet", under_book="neds", alt=None):
    return dict(line=l, p_over=p_over, price=price, book=book, under=under, under_book=under_book, alt=alt, hit=6, n=10)

def player(pid, start, lines, injury=None, age=1.0):
    return dict(player_id=pid, game_id="g" + pid, player="P" + pid, team="A", opp="B", home=1, start=start, injury=injury, odds_age_h=age, book={"pra": lines},
                proj={"pts": 20., "reb": 6., "ast": 5.}, absent=[], last10=[], evidence=[], opp_factor={})

@pytest.fixture
def run(monkeypatch):
    monkeypatch.setattr(app, "model_status", lambda preds=None: (object(), None))
    monkeypatch.setattr(app, "plain_why", lambda *a, **k: "")
    def go(pl):
        monkeypatch.setattr(app, "enriched", lambda: pl); monkeypatch.setattr(app, "next_game_day", lambda ps: ps)
        return app.compute_sweet()["picks"]
    return go

def test_picks_over_and_under_inside_price_band(run):
    # over: 0.5*(0.66-1/1.9)=0.067 >= 0.06 ; under: chance 0.66, price 1.95 -> 0.5*(0.66-0.513)=0.074
    picks = run([player("1", FUTURE, [line(30.5, .66, 1.9)]), player("2", FUTURE, [line(28.5, .34, 1.6, under=1.95)])])
    got = {p["player_id"]: (p["side"], p["price"], p["book"]) for p in picks}
    assert got == {"1": ("over", 1.9, "sportsbet"), "2": ("under", 1.95, "neds")}

def test_outside_band_or_small_gap_is_left_out(run):
    picks = run([player("1", FUTURE, [line(30.5, .80, 1.5)]),           # price too short
                 player("2", FUTURE, [line(30.5, .45, 2.5)]),           # price too long
                 player("3", FUTURE, [line(30.5, .60, 1.9)])])          # gap 0.037: not enough
    assert picks == []

def test_one_per_player_best_gap_and_at_most_five(run):
    pl = [player("1", FUTURE, [line(30.5, .66, 1.9), line(29.5, .72, 1.8)])] + [player(str(i), FUTURE, [line(30.5, .66, 1.9)]) for i in range(2, 9)]
    picks = run(pl)
    assert len(picks) == app.SWEET_MAX and len({p["player_id"] for p in picks}) == len(picks)
    assert picks[0]["player_id"] == "1" and picks[0]["line"] == 29.5

def test_started_out_and_old_prices_are_left_out(run):
    picks = run([player("1", PAST, [line(30.5, .7, 1.9)]), player("2", FUTURE, [line(30.5, .7, 1.9)], injury={"status": "Out"}),
                 player("3", FUTURE, [line(30.5, .7, 1.9)], age=20.0), player("4", FUTURE, [line(30.5, .7, 1.9)])])
    assert [p["player_id"] for p in picks] == ["4"]

def test_better_price_elsewhere_is_used(run):
    picks = run([player("1", FUTURE, [line(30.5, .64, 1.8, alt=[2.0, "ladbrokes_au"])])])
    assert picks and picks[0]["price"] == 2.0 and picks[0]["book"] == "ladbrokes_au"

def test_results_count_sweet_spot_on_its_own(tmp_path, monkeypatch):
    import sqlite3
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app, "DB", str(tmp_path / "t.db")); monkeypatch.setattr(app, "ACCESS_CODE", ""); monkeypatch.setattr(app, "RATE", (10**6, 60))
    monkeypatch.setattr(app, "grade_picks", lambda: None); app.init(); cl = TestClient(app.app)
    c = sqlite3.connect(app.DB)
    for i, (kind, res) in enumerate((("sweet", "won"), ("sweet", "lost"), ("sweet", "won"), ("leg", "won"))):
        c.execute("INSERT INTO pick_log(day,game_id,player_id,player,team,kind,stat,line,side,model_p,price,created,result) VALUES('2026-11-18','g',?,?,?,?,?,?,?,?,?,?,?)",
                  (f"p{i}", "X", "A", kind, "pra", 30.5, "under", .6, 1.9, "t", res))
    c.commit(); t = cl.get("/api/track").json()
    s = t["by_kind"]["sweet"]
    assert (s["n"], s["won"]) == (3, 2) and t["by_kind"]["legs"]["n"] == 1
    assert round(s["bank"]["profit"], 2) == round(2 * 9.0 - 10, 2)
    assert len(t["days"][0]["sweet"]) == 3 and t["days"][0]["value"] == []
