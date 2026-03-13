import roqson
import json
import requests

wf_name = 'Order Workflow'
doc = roqson.get_doc('Workflow', wf_name)
new_transitions = []

for t in doc.get('transitions', []):
    # Skip any transitions that originate from Approved, or are Release Reservation
    if t.get('state') == 'Approved' or t.get('action') == 'Release Reservation' or t.get('action') == 'Reserve Stock':
        continue
        
    # Change Approve to jump to Reserved
    if t.get('action') == 'Approve':
        t['next_state'] = 'Reserved'
        
    new_transitions.append(t)
    
new_states = [s for s in doc.get('states', []) if s.get('state') != 'Approved']

try:
    roqson.update_doc('Workflow', wf_name, {
        'transitions': new_transitions,
        'states': new_states
    })
    print('Success')
except requests.exceptions.HTTPError as e:
    print(f'Error: {e.response.status_code}')
    try:
        print(json.dumps(e.response.json(), indent=2))
    except:
        print(e.response.text)
