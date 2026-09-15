import json, sys, urllib.request, urllib.error

DOMAIN = input("Enter your Signals tenant subdomain: ")
HOST = f"https://{DOMAIN}.signalsresearch2.revvitycloud.com/api/rest/v1.0"
UID = "206"
KEY = input("Enter your API key: ")

def call(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "x-api-key": KEY,
            "Content-Type": "application/vnd.api+json"
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")



def whoami():
    status, r = call("GET", f"{HOST}/profiles/me", f"{HOST}/roles")
    print(status, json.dumps(r))



def find():
    eids, off = [], 0
    while True:
        body = {
            "query": {
                "$and": [
                    {
                        "$match": {
                            "field": "type",
                            "value": "experiment",
                            "mode": "keyword"
                        }
                    },
                    {
                        "$match": {
                            "field": "reviewers",
                            "value": UID,
                            "mode": "keyword"
                        }
                    },
                    {
                        "$match": {
                            "field": "state",
                            "value": "in_review",
                            "mode": "keyword"
                        }
                    }
                ]
            },
            "options":
                {
                    "offset": off,
                    "limit": 100,
                    "sort": {
                        "modifiedAt": "asc"
                    }
                }
        }
        status, r = call("POST", f"{HOST}/entities/search", body)
        if status >= 400:
            print("search failed", status, json.dumps(r)[:500])
            break
        d = r.get("data", [])
        eids += [x["id"] for x in d]
        print(f"offset {off:>5} | got {len(d):>3} | running {len(eids):>5} | api total {r.get('meta', {}).get('total')}")
        off += len(d)
        if len(d) < 100 or off >= 5000:
            break
    with open("eids.txt", "w") as f:
        f.write("\n".join(eids))
    print(len(eids), "eids written to eids.txt")



def reviews(eid=None):
    eid = eid or open("eids.txt").readline().strip()
    status, r = call("GET", f"{HOST}/entities/{eid}/reviews")
    print(eid, status)
    print(json.dumps(r, indent=2))



def close(start="0"):
    REASON = input("Reason for closing without signature? ")
    eids = [l.strip() for l in open("eids.txt") if l.strip()]
    done = set()
    try:
        for l in open("closed_eids.txt"):
            parts = l.strip().split(",")
            if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) < 300:
                done.add(parts[0])
    except FileNotFoundError:
        pass

    todo = [e for e in eids[int(start):] if e not in done]
    print(f"{len(eids)} in list | {len(done)} already closed | {len(todo)} to close")
    if input(f"Close {len(todo)} experiments? Type 'y' to proceed: ").strip() != "y":
        print("aborted")
        return

    body = {"data": {"attributes": {"reason": REASON}}}
    ok = bad = 0
    with open("closed_eids.txt", "a") as log:
        for i, e in enumerate(todo, 1):
            r_status, r_r = call(
                "POST", 
                f"{HOST}/entities/{e}/reviews/reopen",
                body
                )
            if r_status >= 300:
                log.write(f"{e},{r_status},-\n")
                log.flush()
                bad += 1
                print("  REOPEN FAIL", e, r_status, json.dumps(r_r)[:600])
            else:
                c_status, c_r = call(
                    "POST",
                    f"{HOST}/entities/{e}/reviews/close",
                    body
                )
                log.write(f"{e},{r_status},{c_status}\n")
                log.flush()
                if c_status < 300:
                    ok += 1
                else:
                    bad += 1
                    print("  CLOSE FAIL", e, c_status, json.dumps(c_r)[:600])
            if bad >= 10:
                print("10 failures, stopping for inspection.")
                break
            if i % 100 == 0 or i == len(todo):
                print(f"{i}/{len(todo)} ok={ok} bad={bad}")
    print(f"done: {ok} closed, {bad} failed")



def reopen_check(eid):
    REASON = input("Reason for reopening? ")
    status, r = call(
        "POST", 
        f"{HOST}/entities/{eid}/reviews/reopen",
        {"data": {"attributes": {"reason": REASON}}}
        )
    print("reopen", status, json.dumps(r)[:400])



def close_check(eid):
    REASON = input("Reason for closing without signature? ")
    status, r = call(
        "POST", 
        f"{HOST}/entities/{eid}/reviews/close",
        {"data": {"attributes": {"reason": REASON}}}
        )
    print("close", status, json.dumps(r)[:400])



if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    args = sys.argv[2:]
    {
        "whoami": whoami, 
        "find": find,
        "reviews": reviews,
        "close": close,
        "reopen_check": reopen_check,
        "close_check": close_check
    }.get(
        phase, 
        lambda *a: print("usage: python bulk_close_exp.py whoami|find|reviews|close|reopen_check|close_check")
        )(*args)