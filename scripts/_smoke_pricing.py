from fastapi.testclient import TestClient

from main import app

c = TestClient(app)
res = c.get('/pricing')
print('STATUS', res.status_code)
if res.status_code == 200:
    print(res.text[:400])
else:
    print(res.text)
