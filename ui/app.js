const dateFormatter = new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "long", day: "numeric", weekday: "short" });
const results = document.querySelector("#results");
const search = document.querySelector("#search");
const linksByFolder = new Map();

function linkFileFor(match) { return `../${match.folder}/link.txt`; }

async function loadLinks(match) {
  try {
    const response = await fetch(linkFileFor(match));
    if (!response.ok) return [];
    const linksByBoard = new Map();
    (await response.text()).split(/\r?\n/).slice(1).forEach((line) => {
      const separator = line.indexOf(":");
      if (separator < 0) return;
      const number = line.slice(0, separator).trim();
      const url = line.slice(separator + 1).trim();
      if (!number || !url.startsWith("http")) return;
      const current = linksByBoard.get(number);
      if (!current || !url.includes("tinyurl.bridgebase.com")) linksByBoard.set(number, { number, url });
    });
    return [...linksByBoard.values()];
  } catch { return []; }
}

function groupedMatches(query) {
  const normalized = query.trim().toLowerCase();
  return window.MATCHES.filter((match) => match.name.toLowerCase().includes(normalized)).reduce((groups, match) => {
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
    date.innerHTML = `<summary><span>${dateFormatter.format(new Date(`${group.date}T00:00:00`))}</span></summary>`;
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
  article.innerHTML = `<div class="match-heading"><div><h2>${match.name}</h2>${session}</div><span class="board-count">${links ? `${links.length} boards` : "読み込み中"}</span></div><div class="boards"></div>`;
  const boards = article.querySelector(".boards");
  if (links) renderBoards(boards, links);
  else loadLinks(match).then((loadedLinks) => {
    linksByFolder.set(match.folder, loadedLinks);
    renderBoards(boards, loadedLinks);
    article.querySelector(".board-count").textContent = loadedLinks.length ? `${loadedLinks.length} boards` : "URL未登録";
  });
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
render();