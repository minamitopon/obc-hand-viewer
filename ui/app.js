const results = document.querySelector("#results");
const search = document.querySelector("#search");
const linksByFolder = new Map();

function formatDate(date) {
  const [year, month, day] = date.split("-");
  return `${year}/${Number(month)}/${Number(day)}`;
}

function linkFileFor(match) { return `../${match.folder}/link.txt`; }

async function loadLinks(match) {
  try {
    const response = await fetch(linkFileFor(match));
    if (!response.ok) return [];
    const lines = (await response.text()).split(/\r?\n/);
    const expandedUrlIndex = lines.findIndex((line) => line.trim() === "展開URL");
    if (expandedUrlIndex < 0) return [];
    const linksByBoard = new Map();
    lines.slice(expandedUrlIndex + 1).forEach((line) => {
      const separator = line.indexOf(":");
      if (separator < 0) return;
      const number = line.slice(0, separator).trim();
      const url = line.slice(separator + 1).trim();
      if (!number || !url.startsWith("http")) return;
      linksByBoard.set(number, { number, url });
    });
    return [...linksByBoard.values()];
  } catch { return []; }
}

function groupedMatches(query) {
  const normalized = query.trim().toLowerCase();
  return window.MATCHES.filter((match) => linksByFolder.get(match.folder)?.length && match.name.toLowerCase().includes(normalized)).reduce((groups, match) => {
    const group = groups.find((item) => item.date === match.date);
    if (group) group.matches.push(match);
    else groups.push({ date: match.date, matches: [match] });
    return groups;
  }, []).sort((left, right) => right.date.localeCompare(left.date));
}

function render(query = "") {
  const groups = groupedMatches(query);
  results.replaceChildren(...groups.map((group, index) => {
    const date = document.createElement("details");
    date.className = "date-group";
    date.open = index === 0;
    date.innerHTML = `<summary><span>${formatDate(group.date)}</span></summary>`;
    const matches = document.createElement("div");
    matches.className = "match-list";
    group.matches.forEach((match) => matches.appendChild(renderMatch(match)));
    date.appendChild(matches);
    return date;
  }));
  if (!groups.length) results.innerHTML = '<p class="empty">該当する試合がありません。</p>';
}

function renderMatch(match) {
  const article = document.createElement("article");
  article.className = "match";
  const links = linksByFolder.get(match.folder);
  const session = match.session ? `<span class="session">${match.session}</span>` : "";
  article.innerHTML = `<div class="match-heading"><div><h2>${match.name}</h2>${session}</div><span class="board-count">${links.length} boards</span></div><div class="boards"></div>`;
  const boards = article.querySelector(".boards");
  renderBoards(boards, links);
  return article;
}

function renderBoards(container, links) {
  if (!links.length) {
    container.innerHTML = '<p class="no-links">展開URLはまだ登録されていません。</p>';
    return;
  }
  container.replaceChildren(...links.map(({ number, url }) => {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "board-link";
    link.innerHTML = `<span>Board ${number}</span><span class="arrow" aria-hidden="true">↗</span>`;
    return link;
  }));
}

search.addEventListener("input", (event) => render(event.target.value));

Promise.all(window.MATCHES.map(async (match) => {
  linksByFolder.set(match.folder, await loadLinks(match));
})).then(() => render());