#!/usr/bin/env python3
"""Publie une vidéo en Reel sur la page Facebook (gratuit, API Graph).

Le token est injecté automatiquement par le proxy pour graph.facebook.com (secret réseau de l'environnement) :
on en déduit le token de la page via /me/accounts, sans jamais l'afficher.

Usage : python3 fbpost.py video.mp4 "description" [--at 2026-11-20T12:00:00+01:00]
"""
import argparse, datetime, json, os, time, urllib.parse, urllib.request

PAGE_ID = "1530591430128708"   # Squish lab
API = "https://graph.facebook.com/v21.0"


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _post(url, data=None, headers=None, body=None):
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Facebook a refusé ({e.code}) : {e.read().decode()[:400]}")


def page_token():
    pages = _get(f"{API}/me/accounts?fields=id,access_token")["data"]
    for p in pages:
        if p["id"] == PAGE_ID:
            return p["access_token"]
    raise RuntimeError("page introuvable : le token n'a pas accès à la page Squish lab")


def post_reel(path, description, at=None):
    """Publie maintenant, ou programme à `at` (datetime avec fuseau, entre 10 min et 29 jours plus tard)."""
    pt = page_token()
    start = _post(f"{API}/{PAGE_ID}/video_reels", {"upload_phase": "start", "access_token": pt})
    vid = start["video_id"]
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        up = _post(f"https://rupload.facebook.com/video-upload/v21.0/{vid}", body=fh.read(),
                   headers={"Authorization": f"OAuth {pt}", "offset": "0", "file_size": str(size)})
    if not up.get("success"):
        raise RuntimeError(f"envoi du fichier échoué : {up}")
    finish = {"upload_phase": "finish", "video_id": vid, "description": description, "access_token": pt}
    if at:
        finish.update(video_state="SCHEDULED", scheduled_publish_time=str(int(at.timestamp())))
    else:
        finish["video_state"] = "PUBLISHED"
    res = _post(f"{API}/{PAGE_ID}/video_reels", finish)
    if not res.get("success"):
        raise RuntimeError(f"publication échouée : {res}")
    return vid


def status(vid):
    pt = page_token()
    return _get(f"{API}/{vid}?fields=status,permalink_url&access_token={pt}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("description")
    ap.add_argument("--at", help="date ISO avec fuseau, ex. 2026-11-20T12:00:00+01:00")
    a = ap.parse_args()
    at = datetime.datetime.fromisoformat(a.at) if a.at else None
    vid = post_reel(a.video, a.description, at)
    print("Reel envoyé, id :", vid)
    for _ in range(12):
        time.sleep(10)
        st = status(vid)
        print(json.dumps(st.get("status", {}))[:300])
        if st.get("status", {}).get("video_status") in ("ready", "error"):
            print("lien :", st.get("permalink_url"))
            break
