# LoL Esports 공식 API에서 전체 리그 일정을 긁어 data.json 스냅샷 생성
# ponytail: retries 3회면 충분, 실패 리그는 건너뜀 — 다음 크론에서 복구됨
import json, time, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

BASE = "https://esports-api.lolesports.com/persisted/gw"
KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"  # lolesports.com 공개 클라이언트 키


def get(path, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-api-key": KEY})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            print("  retry", e)
            time.sleep(2 * (attempt + 1))
    return None


leagues = get("/getLeagues", {"hl": "ko-KR"})["data"]["leagues"]
cutoff = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")

events = {}
team_logos = {}  # 팀 이름 -> 로고 URL (https)
failed = []
for lg in leagues:
    data = get("/getSchedule", {"hl": "ko-KR", "leagueId": lg["id"]})
    if not data:
        print(lg["slug"], "FAILED")
        failed.append(lg["slug"])
        continue
    sched = data["data"]["schedule"]
    evs = sched.get("events") or []
    newer = (sched.get("pages") or {}).get("newer")
    hops = 0
    while newer and hops < 12:
        d2 = get("/getSchedule", {"hl": "ko-KR", "leagueId": lg["id"], "pageToken": newer})
        if not d2:
            break
        s2 = d2["data"]["schedule"]
        evs += s2.get("events") or []
        newer = (s2.get("pages") or {}).get("newer")
        hops += 1
        time.sleep(0.3)
    for ev in evs:
        if ev.get("type") != "match" or not ev.get("match") or ev["startTime"] < cutoff:
            continue
        m = ev["match"]
        for t in m.get("teams", []):
            if t.get("image") and t.get("name") and t["name"] != "TBD":
                team_logos[t["name"]] = t["image"].replace("http://", "https://")
        events[m["id"]] = {
            "id": m["id"], "s": ev["startTime"], "st": ev["state"],
            "l": lg["name"], "lg": lg["slug"], "r": lg["region"], "b": ev.get("blockName"),
            "t": [t["code"] for t in m.get("teams", [])],
            "tn": [t["name"] for t in m.get("teams", [])],
            "bo": (m.get("strategy") or {}).get("count"),
        }
    print(lg["slug"], len(evs), "->", len(events))
    time.sleep(0.4)

# 무결성 가드: 축소된 스냅샷이 조용히 커밋되는 것을 방지
# ponytail: 임계값 하드코딩(실패 3개·이벤트 500) — 리그 구조가 크게 바뀌면 조정
if len(failed) >= 3 or len(events) < 500:
    import sys
    print(f"ABORT: failed={failed}, events={len(events)} — 스냅샷이 불완전해 커밋하지 않음")
    sys.exit(1)

out = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "leagues": [{"id": l["id"], "slug": l["slug"], "name": l["name"], "region": l["region"]} for l in leagues],
    "teams": team_logos,
    "events": sorted(events.values(), key=lambda e: e["s"]),
}
json.dump(out, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("DONE", len(events), "events")
