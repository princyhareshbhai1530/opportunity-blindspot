"""Download JTH v1.1 tables from Zenodo record 21390581 and check their SHA-256."""
import hashlib, urllib.request
from core import RAW

FILES = {
    "candidates.csv": "4328ceb1678757ce19b62105e97cca70759f38c332bef13cf9746badbbf3f692",
    "jobs.csv": "5bcd9e4379e558b98418e2242d321757612a96887b934e0d3ece6eb4a9952628",
    "history.csv": "0348bb0017156a91fe40fdd4346846982587940a0796dae3941da55312ade2a3",
}
RAW.mkdir(parents=True, exist_ok=True)
for name, sha in FILES.items():
    path = RAW / name
    if not path.exists():
        urllib.request.urlretrieve(f"https://zenodo.org/api/records/21390581/files/{name}/content", path)
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    assert got == sha, f"{name}: sha256 {got} does not match the version used for this submission"
    print("ok", name)
