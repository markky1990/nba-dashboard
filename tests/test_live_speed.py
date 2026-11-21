"""Live stats: the server re-fetches what phones are watching every 5 s, and phones ask every 10 s (Games, Locked picks, My picks)."""
import re, pathlib
import live

def test_server_refreshes_watched_scores_every_5_seconds():
    assert live.LIVE_TTL == 5

def test_phones_ask_every_10_seconds_on_live_screens():
    html = pathlib.Path(__file__).resolve().parent.parent.joinpath("static", "index.html").read_text()
    assert html.count("setInterval(refreshGames,10000)") == 2 and "setInterval(refreshPlaying,10000)" in html
    assert re.search(r'refresh\(\)\},10000\)', html) and "refreshGames,15000" not in html and "refreshPlaying,20000" not in html
