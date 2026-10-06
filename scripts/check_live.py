import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://showline.s2.havano.pro/web/login')
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
        print("HTTP STATUS:", response.status)
        print("LOGIN PAGE OK")
except Exception as e:
    print("HTTP ERROR:", e)
