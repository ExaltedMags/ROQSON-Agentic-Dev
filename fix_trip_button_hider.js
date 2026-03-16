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

(async () => {
  const res = await fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Client%20Script/Full%20Order%20Script', {
    headers: { Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET }
  });
  const data = (await res.json()).data;
  let script = data.script;

  const oldBlock = `    $(frm.page.wrapper).find("a, button, .dropdown-item").each(function () {

      const text = ($(this).text() || "").trim();

      if (HIDDEN_WORKFLOW_ACTIONS.includes(text)) {

        $(this).hide();

        $(this).closest("li").hide();

      }

    });`;

  const newBlock = `    $(frm.page.wrapper).find(".menu-item, .dropdown-item, a.grey-link").each(function () {

      const text = ($(this).text() || "").trim();

      if (HIDDEN_WORKFLOW_ACTIONS.includes(text)) {

        $(this).hide();

        $(this).closest("li").hide();

        $(this).closest(".menu-item-container").hide();

      }

    });`;

  if (!script.includes(oldBlock)) {
    throw new Error('target block not found');
  }

  script = script.replace(oldBlock, newBlock);

  const put = await fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Client%20Script/Full%20Order%20Script', {
    method: 'PUT',
    headers: {
      Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ script })
  });

  const text = await put.text();
  console.log(put.status);
  console.log(text);
  if (!put.ok) process.exit(1);
})();
