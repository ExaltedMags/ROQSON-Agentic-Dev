import roqson
import json

def investigate_workflow():
    wf_list = roqson.list_docs('Workflow', fields=['name', 'document_type'], filters={'document_type': 'Order Form', 'is_active': 1})
    if not wf_list:
        print("No active workflow found for Order Form.")
        return
    
    wf_name = wf_list[0]['name']
    doc = roqson.get_doc('Workflow', wf_name)
    
    # Let's see all states
    print("CURRENT STATES:")
    for s in doc.get('states', []):
        print(f"  - {s.get('state')}")
        
    print("\nTRANSITIONS INVOLVING 'Approved' OR 'Reserve Stock':")
    for t in doc.get('transitions', []):
        if t.get('state') == 'Approved' or t.get('next_state') == 'Approved' or t.get('action') == 'Reserve Stock':
            print(f"  {t.get('state')} --[{t.get('action')}]--> {t.get('next_state')}")

if __name__ == '__main__':
    investigate_workflow()
