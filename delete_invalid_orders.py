import roqson
import requests

key, secret = roqson._auth()
headers = {"Authorization": f"token {key}:{secret}"}

invalid_docs = [
    'Order-000309', 'Order-000273', 'Order-000258', 'Order-000308', 'Order-000307', 
    'Order-000305', 'Order-000306', 'Order-000259', 'Order-000304', 'Order-000263',
    'Order-000303', 'Order-000275', 'Order-000291', 'Order-000274', 'Order-000301',
    'Order-000300', 'Order-000299', 'Order-000292', 'Order-000266', 'Order-000264',
    'Order-000297', 'Order-000295', 'Order-000272', 'Order-000268', 'Order-000269',
    'Order-000271', 'Order-000116', 'Order-000155', 'Order-000160', 'Order-000159',
    'Order-000151', 'Order-000150', 'Order-000149', 'Order-000148', 'Order-000147',
    'Order-000146', 'Order-000145', 'Order-000144', 'Order-000143', 'Order-000142',
    'Order-000141', 'Order-000140', 'Order-000139', 'Order-000138', 'Order-000137',
    'Order-000136', 'Order-000135', 'Order-000134', 'Order-000133', 'Order-000132',
    'Order-000131', 'Order-000130', 'Order-000129', 'Order-000128', 'Order-000127',
    'Order-000126', 'Order-000125', 'Order-000124', 'Order-000123', 'Order-000121',
    'Order-000122', 'Order-000120', 'Order-000119', 'Order-000118', 'Order-000117',
    'Order-000115', 'Order-000114', 'Order-000112', 'Order-000110', 'Order-000079',
    'Order-000074', 'Order-000077', 'Order-000037', 'Order-000013'
]

success = 0
for name in invalid_docs:
    url = f"{roqson.BASE}/api/resource/Order Form/{name}"
    print(f"Deleting {name}...")
    res = requests.delete(url, headers=headers)
    if res.status_code == 202 or res.status_code == 200:
        success += 1
        print(f"Deleted {name}")
    else:
        print(f"Failed to delete {name}: {res.status_code} {res.text}")

print(f"Successfully deleted {success} of {len(invalid_docs)}")
