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
  const stateNames = new Set((doc.states || []).map((state) => state.state));
  const template = doc.states.find((state) => state.state === 'Delivered') || doc.states[0] || {};

  for (const stateName of ['Received', 'Failed']) {
    if (!stateNames.has(stateName)) {
      doc.states.push({
        state: stateName,
        doc_status: '0',
        is_optional_state: 0,
        avoid_status_override: 0,
        allow_edit: template.allow_edit || 'Administrator',
        send_email: template.send_email == null ? 1 : template.send_email,
        doctype: 'Workflow Document State'
      });
    }
  }

  doc.states.forEach((state, index) => {
    state.idx = index + 1;
  });

  const updateResponse = await fetch(base + '/api/resource/Workflow/Time%20in%20Time%20out', {
    method: 'PUT',
    headers,
    body: JSON.stringify({ states: doc.states })
  });

  const text = await updateResponse.text();
  console.log(updateResponse.status);
  console.log(text);
  if (!updateResponse.ok) process.exit(1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
