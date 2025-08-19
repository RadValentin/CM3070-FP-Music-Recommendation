# better_recommendations.py
import io, os, sys, time
import numpy as np
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity

# --- Django setup (same as your script) ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
import django
django.setup()
from recommend_api.models import Track

# -------- knobs you can tweak --------
TARGET_MBID = "62c2e20a-559e-422f-a44c-9afa7882f0c4"  # Enter Sandman
TOP_K = 10
ARTIST_CAP = 2              # max recs per artist
USE_ROS = True              # True: ROS filter; False: Dortmund filter
DECADE_STRICT = True        # True: exact decade; False: +/-10y window
BONUS_GENRE = 0.05          # re-rank bonus weights
BONUS_ROS   = 0.05
BONUS_DECADE= 0.02
MIN_CANDIDATES = 50         # widen filters if fewer than this
# -------------------------------------

def main():
    dat = np.load("features_and_index.npz", allow_pickle=True)
    X   = dat["feature_matrix"]           # (N, d), L2-normalized rows
    MB  = dat["mbids"]
    YR  = dat["years"]
    GD  = dat["genre_dortmund"]
    GR  = dat["genre_rosamerica"]

    # map MBID -> row
    mbid_to_row = {mbid: i for i, mbid in enumerate(MB)}
    if TARGET_MBID not in mbid_to_row:
        print("Target MBID not found.")
        return

    qi = mbid_to_row[TARGET_MBID]
    q  = X[qi:qi+1]                       # keep 2D
    q_year = int(YR[qi])
    q_gd, q_gr = GD[qi], GR[qi]

    # decade/window mask
    if DECADE_STRICT:
        decade = (q_year // 10) * 10
        decade_mask = (YR >= decade) & (YR < decade + 10)
    else:
        decade_mask = (YR >= q_year - 10) & (YR < q_year + 10)

    # genre mask (choose ROS or Dortmund)
    genre_mask = (GR == q_gr) if USE_ROS else (GD == q_gd)

    # combine mask; exclude rows with missing years if desired
    cand_mask = decade_mask & genre_mask
    cand_idx = np.where(cand_mask)[0]
    if cand_idx.size < MIN_CANDIDATES:
        # widen: drop genre constraint first, then decade if still small
        cand_idx = np.where(decade_mask)[0]
        if cand_idx.size < MIN_CANDIDATES:
            cand_idx = np.arange(X.shape[0])

    # cosine similarities on candidates
    t0 = time.time()
    s = (q @ X[cand_idx].T).ravel()
    # self index (if target survived the mask) inside cand_idx
    # find where MB[cand_idx] == TARGET_MBID; if none, self_in = None
    self_in = None
    if qi in cand_idx:
        pos = np.where(cand_idx == qi)[0]
        self_in = int(pos[0]) if pos.size else None

    # small re-rank bonuses (do not dominate cosine)
    bonus = np.zeros_like(s, dtype=float)
    if BONUS_GENRE:
        bonus += BONUS_GENRE * (GD[cand_idx] == q_gd).astype(float)
    if BONUS_ROS:
        bonus += BONUS_ROS * (GR[cand_idx] == q_gr).astype(float)
    if BONUS_DECADE:
        if DECADE_STRICT:
            bonus += BONUS_DECADE * (((YR[cand_idx] // 10) * 10) == decade).astype(float)
        else:
            bonus += BONUS_DECADE * decade_mask[cand_idx].astype(float)

    score = s + bonus

    # take top-(K + buffer), sort properly
    kbuf = TOP_K + 5
    part = np.argpartition(score, -kbuf)[-kbuf:]
    part = part[np.argsort(score[part])[::-1]]

    # drop self if present, enforce artist cap, keep order
    qs = Track.objects.get(musicbrainz_recordingid=TARGET_MBID)
    q_artist = qs.artists.first()
    q_artist_name = q_artist.name if q_artist else "Unknown Artist"

    # batch fetch tracks for top slice (will further filter by artist cap)
    top_cand_mbids = MB[cand_idx[part]].tolist()
    tmap = {t.musicbrainz_recordingid: t
            for t in Track.objects.filter(musicbrainz_recordingid__in=top_cand_mbids).prefetch_related("artists")}

    picked = []
    artist_counts = defaultdict(int)
    for local_i in part:
        global_row = cand_idx[local_i]
        if global_row == qi and self_in is not None:
            continue  # drop self
        mbid = MB[global_row]
        t = tmap.get(mbid)
        if not t:
            continue
        artist = t.artists.first()
        artist_name = artist.name if artist else "Unknown Artist"
        if artist_counts[artist_name] >= ARTIST_CAP:
            continue
        artist_counts[artist_name] += 1
        picked.append((global_row, float(score[local_i])))
        if len(picked) == TOP_K:
            break

    # table header
    print(f"Cosine similarity search took {time.time() - t0:.2f} seconds")
    print(f"Tracks similar to: {q_artist_name} - {qs.title} ({q_year}) [{q_gd}] [{q_gr}]")
    print("\nRecommendations:")
    header = f"{'Artist':20} | {'Title':30} | {'Year':6} | {'Dort.':10} | {'Ros.':10} | {'Sim':6}"
    print(header)
    print("-" * len(header))

    for row, sc in picked:
        mbid = MB[row]
        t = tmap.get(mbid)
        a = t.artists.first() if t else None
        name = a.name if a else "Unknown Artist"
        title = t.title if t else "(unknown)"
        year = int(YR[row])
        g_dor = GD[row]
        g_ros = GR[row]
        # recompute cosine (not strictly needed; shows pure sim alongside bonus if you prefer)
        cos = float((q @ X[row:row+1].T).ravel()[0])
        print(f"{name[:20]:20} | {title[:30]:30} | {str(year):6} | "
              f"{g_dor:10} | {g_ros:10} | {cos:6.3f}")

    # stats excluding self (if present among candidates)
    if self_in is not None:
        others = np.delete(s, self_in)  # stats on raw cosine, not score
    else:
        others = s
    print("\nStats for similarities (raw cosine, candidates only):")
    print("mean:", float(others.mean()),
          "std:", float(others.std()),
          "p95:", float(np.quantile(others, 0.95)),
          "max:", float(others.max()))

if __name__ == "__main__":
    main()
