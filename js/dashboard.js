const app = document.getElementById("app");
document.title = "Dashboard · " + SITE.name;
document.getElementById("brand").textContent = SITE.name;
document.getElementById("tagline").textContent = SITE.tagline;

const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const sum = (arr, f) => arr.reduce((n, x) => n + f(x), 0);
const studentsOf = (d) => sum(d.classes, (c) => sum(c.divisions, (v) => v.students));

function card(href, badge, title, meta) {
  return `<a class="card" href="${href}"><span class="badge">${esc(badge)}</span><h3>${esc(title)}</h3><p>${esc(meta)}</p></a>`;
}

function render() {
  const path = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const dept = DATA.find((d) => d.id === path[0]);
  const cls = dept && dept.classes.find((c) => c.id === path[1]);
  const div = cls && cls.divisions.find((v) => v.id === path[2]);
  const sub = div && div.subjects.find((s) => s.id === path[3]);
  const depth = sub ? 4 : div ? 3 : cls ? 2 : dept ? 1 : 0;

  // Fix invalid or extra path parts
  if (path.length !== depth) { location.hash = "#/" + path.slice(0, depth).join("/"); return; }

  // Breadcrumb
  const trail = [["Home", "#/"]];
  if (dept) trail.push([dept.name, "#/" + dept.id]);
  if (cls) trail.push([cls.name, `#/${dept.id}/${cls.id}`]);
  if (div) trail.push([div.name, `#/${dept.id}/${cls.id}/${div.id}`]);
  if (sub) trail.push([sub.name, null]);
  const crumbs = trail.map(([t, h], i) =>
    (h && i < trail.length - 1 ? `<a href="${h}">${esc(t)}</a>` : `<strong>${esc(t)}</strong>`)
  ).join('<span class="sep">›</span>');

  let html = `<nav class="crumbs" aria-label="Breadcrumb">${crumbs}</nav>`;

  if (depth === 0) {
    const allClasses = sum(DATA, (d) => d.classes.length);
    const allDivs = sum(DATA, (d) => sum(d.classes, (c) => c.divisions.length));
    const allStudents = sum(DATA, studentsOf);
    html += `<div class="hero"><h2>Departments</h2><p>Pick a department to open its classes, divisions and subjects.</p></div>
      <div class="stats">
        <div class="stat"><b>${DATA.length}</b><span>Departments</span></div>
        <div class="stat"><b>${allClasses}</b><span>Classes</span></div>
        <div class="stat"><b>${allDivs}</b><span>Divisions</span></div>
        <div class="stat"><b>${allStudents}</b><span>Students</span></div>
      </div>
      <div class="grid">${DATA.map((d) =>
        card("#/" + d.id, d.code, d.name, `${d.classes.length} classes · ${studentsOf(d)} students`)).join("")}</div>`;
  } else if (depth === 1) {
    html += `<div class="hero"><h2>${esc(dept.name)}</h2><p>Select a class.</p></div>
      <div class="grid">${dept.classes.map((c) =>
        card(`#/${dept.id}/${c.id}`, c.name, c.full,
          `${c.divisions.length} divisions · ${sum(c.divisions, (v) => v.students)} students`)).join("")}</div>`;
  } else if (depth === 2) {
    html += `<div class="hero"><h2>${esc(cls.full)} (${esc(cls.name)})</h2><p>${esc(dept.name)} · select a division.</p></div>
      <div class="grid">${cls.divisions.map((v) =>
        card(`#/${dept.id}/${cls.id}/${v.id}`, v.id.toUpperCase(), v.name,
          `${v.students} students · ${v.subjects.length} subjects`)).join("")}</div>`;
  } else if (depth === 3) {
    html += `<div class="hero"><h2>${esc(cls.name)} ${esc(div.name)}</h2><p>${esc(dept.name)} · select a subject.</p></div>
      <div class="grid">${div.subjects.map((s) =>
        card(`#/${dept.id}/${cls.id}/${div.id}/${s.id}`, s.name.slice(0, 2).toUpperCase(), s.name,
          `${s.teacher} · ${s.lessons} lessons`)).join("")}</div>`;
  } else {
    const ctx = encodeURIComponent(`${dept.name} › ${cls.name} › ${div.name} › ${sub.name}`);
    html += `<div class="hero"><h2>${esc(sub.name)}</h2><p>${esc(sub.teacher)} · ${esc(cls.name)} ${esc(div.name)} · ${sub.lessons} lessons</p></div>
      <div class="detail">
        <a class="tile" href="studio.html?tab=lesson&ctx=${ctx}"><h3>Create lesson from PPT</h3><p>Upload slides and let the teacher avatar explain them.</p></a>
        <a class="tile" href="studio.html?tab=live&ctx=${ctx}"><h3>Start live class</h3><p>Open the classroom view with attention tracking.</p></a>
        <div class="tile off" aria-disabled="true"><h3>Attendance</h3><p>Live code check-in. Coming next.</p></div>
      </div>`;
  }

  app.innerHTML = html;
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", render);
render();
