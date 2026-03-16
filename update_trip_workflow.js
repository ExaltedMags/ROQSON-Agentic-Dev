const fs = require('fs');
const env = Object.fromEntries(
  fs.readFileSync('.env', 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf('=');
      return [line.slice(0, idx), line.slice(idx + 1)];
    })
);

const base = 'https://roqson-industrial-sales.s.frappe.cloud';
const headers = {
  Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET,
  'Content-Type': 'application/json'
};

(async () => {
  const response = await fetch(base + '/api/resource/Workflow/Time%20in%20Time%20out', { headers });
  const text = await response.text();
  if (!response.ok) {
    console.log(response.status);
    console.log(text);
    process.exit(1);
  }

  const doc = JSON.parse(text).data;
  const hiddenActions = new Set(['Time In', 'Time Out']);
  doc.transitions = (doc.transitions || []).filter((transition) => !hiddenActions.has((transition.action || '').trim()));

  const stateNames = new Set((doc.states || []).map((state) => state.state));
  const stateTemplate = doc.states.find((state) => state.state === 'Delivered') || doc.states[0] || {};

  for (const stateName of ['Received', 'Failed']) {
    if (!stateNames.has(stateName)) {
      doc.states.push({
        state: stateName,
        doc_status: '0',
        is_optional_state: 0,
        avoid_status_override: 0,
        allow_edit: stateTemplate.allow_edit || 'Administrator',
        send_email: stateTemplate.send_email == null ? 1 : stateTemplate.send_email,
        doctype: 'Workflow Document State'
      });
    }
  }

  const roles = ['Driver', 'Dispatcher', 'Administrator', 'System Manager'];
  const sourceStates = ['In Transit', 'Arrived', 'Delivered'];
  const desiredTransitions = [
    {
      action: 'Finalize Successful Delivery',
      next_state: 'Received',
      condition: 'doc.arrival_time and doc.completion_time and doc.delivery_status == "Successful"'
    },
    {
      action: 'Finalize Failed Delivery',
      next_state: 'Failed',
      condition: 'doc.arrival_time and doc.completion_time and doc.delivery_status == "Failed"'
    }
  ];

  const existingKeys = new Set(
    doc.transitions.map((transition) => [transition.state, transition.action, transition.next_state, transition.allowed].join('|'))
  );

  for (const sourceState of sourceStates) {
    for (const desired of desiredTransitions) {
      for (const role of roles) {
        const key = [sourceState, desired.action, desired.next_state, role].join('|');
        if (!existingKeys.has(key)) {
          doc.transitions.push({
            state: sourceState,
            action: desired.action,
            next_state: desired.next_state,
            allowed: role,
            allow_self_approval: 1,
            send_email_to_creator: 0,
            condition: desired.condition,
            doctype: 'Workflow Transition'
          });
          existingKeys.add(key);
        }
      }
    }
  }

  doc.states.forEach((state, index) => {
    state.idx = index + 1;
  });

  doc.transitions.forEach((transition, index) => {
    transition.idx = index + 1;
  });

  const updateResponse = await fetch(base + '/api/resource/Workflow/Time%20in%20Time%20out', {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      states: doc.states,
      transitions: doc.transitions
    })
  });

  const updateText = await updateResponse.text();
  console.log(updateResponse.status);
  console.log(updateText);
  if (!updateResponse.ok) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
