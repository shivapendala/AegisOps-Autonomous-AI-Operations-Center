# test_step17_e2e.py
from fastapi.testclient import TestClient
def test_step17_full_end_to_end_demonstration(client: TestClient):
    reset = client.post('/api/simulation/reset')
    assert reset.status_code == 200
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['status'].lower() in ('healthy', 'ok')
    imcs = client.get('/api/incidents').json()
    active = [i for i in imcs if i['status'] in ('OPEN', 'INVESTIGATING')]
    assert len(active) == 0
    sim = client.post('/api/simulation/payment-failure').json()
    assert sim['status'] == 'success'
    assert sim['alerts_count'] == 4
    inc = sim['incident']
    assert '101' in str(inc['id'])
    assert inc['service'] == 'Payment API'
    assert inc['severity'] == 'CRITICAL'
    assert inc['correlation_score'] == 91.0
    details = client.get(f"/api/incidents/{inc['id']}").json()
    assert 'Database connection pool exhaustion' in details['probable_cause']
    assert details['confidence_score'] == 91.0
    assert details['status'] == 'OPEN'
    recs = client.get(f"/api/incidents/{inc['id']}/recommendations").json()
    assert len(recs) == 4
    inv_res = client.post(f"/api/incidents/{inc['id']}/investigate")
    assert inv_res.json()['status'] == 'INVESTIGATING'
    res_res = client.post(f"/api/incidents/{inc['id']}/resolve")
    assert res_res.json()['status'] == 'RESOLVED'
    close_res = client.post(f"/api/incidents/{inc['id']}/close")
    assert close_res.json()['status'] == 'CLOSED'
