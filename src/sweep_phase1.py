"""Calibration sweep: which reconstruction choices best match ALL Phase 1 published figures."""
import json, itertools, numpy as np, core
from scipy import sparse
from sklearn.preprocessing import normalize
from phase1_reproduce import run, SEED, N_PAIRS
w = core.World()
rng = np.random.default_rng(SEED); rows = rng.choice(np.where(w.cand_has_text)[0], size=N_PAIRS, replace=False)
onehot = sparse.csr_matrix(np.eye(4)[w.sen])
res = []
for senw, neigh, pool in itertools.product([0.06], [20], [100]):
    w.H = normalize(sparse.hstack([w.J*np.sqrt(1-senw), onehot*np.sqrt(senw)]).tocsr()) if senw>0 else w.J
    core.HIST_NEIGH = neigh; core.POOL_SIZE = pool
    r = run(w, rows, SEED, betas=[0.45])[0.45]
    g = {v: float(np.mean([a-b for a,b in r[v]])*100) for v in core.VALUE_DEFS}
    A = np.mean([a for a,_ in r["primary"]])*100; B = np.mean([b for _,b in r["primary"]])*100
    e = dict(sal=float(np.mean(np.array(r["salA"])-np.array(r["salB"]))), rem=float(np.mean(np.array(r["remA"])-np.array(r["remB"]))*100),
             perm=float(np.mean(np.array(r["permA"])-np.array(r["permB"]))*100), comp=float((np.mean(r["compA"])/np.mean(r["compB"])-1)*100))
    row = dict(senw=senw, neigh=neigh, pool=pool, A=A, B=B, **g, **e); res.append(row)
    print({k:(round(v,2) if isinstance(v,float) else v) for k,v in row.items()}, flush=True)
json.dump(res, open(core.ROOT/"outputs"/"phase1_calibration_sweep3.json","w"), indent=1)
