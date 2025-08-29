// Fetching from https://game8.co/games/Pokemon-TCG-Pock et/archives/483152

const tables = Array.from(document.querySelectorAll("table")).slice(1); // Skip first table
const result = [];

tables.forEach((table) => {
  // Find the closest preceding <h3>
  let header = table.previousElementSibling;
  while (header && header.tagName !== "H3") {
    header = header.previousElementSibling;
  }

  if (!header || /cg full/i.test(header.textContent)) return; // Skip if no <h3> or if "CG Full"

  const rows = Array.from(table.querySelectorAll("tr"));

  rows.forEach((tr) => {
    const tds = Array.from(tr.querySelectorAll("td"));

    tds.forEach((td, idx) => {
      if (idx % 2 !== 0) return; // only even-indexed <td>s

      const img = td.querySelector("img");
      const nameAnchor = td.querySelector("a.a-link");

      if (!img || !nameAnchor) return;

      const imageUrl = img.src;
      const name = nameAnchor.innerText.replace(/\n/g, " ").replace(/\s+/g, " ").trim();

      result.push({ name, imageUrl });
    });
  });
});

console.log(result);
