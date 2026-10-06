import os
import subprocess

def run(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"CMD: {cmd}")
    print(f"STDOUT:\n{res.stdout}")
    print(f"STDERR:\n{res.stderr}")

print("=== Checking SSH Keys ===")
run("ls -la /home/ttembo/.ssh /root/.ssh")

print("=== Checking Git Config ===")
run("git config --list --show-origin")
