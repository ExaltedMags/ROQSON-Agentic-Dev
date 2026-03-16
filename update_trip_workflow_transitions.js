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
  const doc = (await response.json()).data;

  const hiddenActions = new Set(['Time In', 'Time Out']);
  doc.transitions = (doc.transitions || []).filter((transition) => !hiddenActions.has((transition.action || '').trim()));

  const roles = ['Driver', 'Dispatcher', 'Administrator', 'System Manager'];
  const sourceStates = ['In Transit', 'Arrived', 'Delivered'];
  const desiredTransitions = [
    {
      action: 'Mark Delivered',
      next_state: 'Received',
      condition: 'doc.arrival_time and doc.completion_time and doc.delivery_status == "Successful"'
    },
    {
      action: 'Mark Delivery Failed',
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

  doc.transitions.forEach((transition, index) => {
    transition.idx = index + 1;
  });

  const updateResponse = await fetch(base + '/api/resource/Workflow/Time%20in%20Time%20out', {
    method: 'PUT',
    headers,
    body: JSON.stringify({ transitions: doc.transitions })
  });

  const text = await updateResponse.text();
  console.log(updateResponse.status);
  console.log(text);
  if (!updateResponse.ok) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
