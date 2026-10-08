// ---- Config ---------------------------------------------------------------
// Leave API_BASE empty to run in demo mode (fake data, no backend needed).
// Later set it to your FastAPI server, e.g. "http://localhost:8000".
const API_BASE = "";

const $ = (id) => document.getElementById(id);
$("modeBadge").textContent = API_BASE ? "Connected to backend" : "Demo mode";

// ---- Tabs -----------------------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + tab.dataset.view));
  });
});

// ---- Create lesson --------------------------------------------------------
let scenes = [];

function renderScenes() {
  const list = $("sceneList");
  list.innerHTML = "";
  scenes.forEach((s, i) => {
    const li = document.createElement("li");
    li.innerHTML = `${s.title}<small>${s.narration}</small>`;
    li.addEventListener("click", () => selectScene(i));
    list.appendChild(li);
  });
  selectScene(0);
}

function selectScene(i) {
  [...$("sceneList").children].forEach((li, n) => li.classList.toggle("on", n === i));
  $("stageVisual").innerHTML = `<p>${scenes[i].visual_prompt}</p>`;
}

function demoScenes(topic) {
  return [
    { title: "Introduction", narration: `Today we will learn: ${topic}.`, visual_type: "diagram", visual_prompt: "Title card with the lesson topic" },
    { title: "Core idea", narration: "Here is the main idea explained step by step.", visual_type: "diagram", visual_prompt: "Diagram of the main concept" },
    { title: "The equation", narration: "Now let us look at the equation behind it.", visual_type: "diagram", visual_prompt: "Equation shown line by line" },
    { title: "Summary", narration: "Let us quickly recap what we learned.", visual_type: "diagram", visual_prompt: "Bullet summary of key points" },
  ];
}

$("generateBtn").addEventListener("click", async () => {
  const topic = $("topic").value.trim();
  const details = $("details").value.trim();
  if (!topic || !details) {
    $("genStatus").textContent = "Enter a lesson title and the details to explain.";
    return;
  }
  const btn = $("generateBtn");
  btn.disabled = true;
  $("genStatus").textContent = "Writing the script and splitting it into scenes...";

  try {
    if (API_BASE) {
      const res = await fetch(`${API_BASE}/api/lessons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic, details,
          avatar: $("avatar").value,
          visuals: $("visuals").value,
          language: $("lang").value,
        }),
      });
      if (!res.ok) throw new Error("Server returned " + res.status);
      const data = await res.json(); // expected: { scenes: [...], video_url: "..." }
      scenes = data.scenes;
      renderScenes();
      if (data.video_url) {
        $("finalVideo").src = API_BASE + data.video_url;
        $("finalVideo").hidden = false;
        $("downloadBtn").href = API_BASE + data.video_url;
        $("downloadBtn").hidden = false;
        $("uploadYtBtn").hidden = false;
      }
    } else {
      await new Promise((r) => setTimeout(r, 800));
      scenes = demoScenes(topic);
      renderScenes();
    }
    $("genStatus").textContent = "Done. Select a scene to preview it.";
  } catch (err) {
    $("genStatus").textContent = "Could not generate the video: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

$("uploadYtBtn").addEventListener("click", async () => {
  if (!API_BASE) return;
  await fetch(`${API_BASE}/api/youtube/upload`, { method: "POST" });
});

// ---- Live classroom -------------------------------------------------------
const students = [
  { name: "Rahul", score: 85 },
  { name: "Priya", score: 78 },
  { name: "Aman", score: 90 },
  { name: "Sneha", score: 70 },
];
const lowSince = {};          // name -> timestamp when score fell below 40
const pending = new Set();    // names already being handled

function renderTiles() {
  const box = $("tiles");
  box.innerHTML = "";
  students.forEach((s) => {
    const d = document.createElement("div");
    d.className = "tile" + (s.score < 40 ? " low" : "");
    d.id = "tile-" + s.name;
    d.innerHTML = `<span class="name">${s.name}</span><div class="score"><i style="width:${s.score}%"></i></div>`;
    box.appendChild(d);
  });
}

function addLog(text) {
  const log = $("log");
  const first = log.querySelector(".empty");
  if (first) first.remove();
  const li = document.createElement("li");
  li.textContent = new Date().toLocaleTimeString() + "  " + text;
  log.prepend(li);
}

$("camBtn").addEventListener("click", async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    const tile = document.createElement("div");
    tile.className = "tile";
    tile.innerHTML = `<video autoplay muted playsinline></video><span class="name">You</span>`;
    tile.querySelector("video").srcObject = stream;
    $("tiles").prepend(tile);
    $("camBtn").disabled = true;
    addLog("Camera started. Attention detection is not connected yet.");
  } catch {
    addLog("Camera blocked. Allow camera access in your browser and try again.");
  }
});

$("simBtn").addEventListener("click", () => {
  const s = students[Math.floor(Math.random() * students.length)];
  s.score = 20;
  lowSince[s.name] = Date.now() - 11000; // pretend it has been low for 11 s
  renderTiles();
});

setInterval(() => {
  students.forEach((s) => {
    if (s.score >= 40 && !pending.has(s.name)) {
      s.score = Math.max(55, Math.min(95, s.score + (Math.random() * 10 - 5)));
    }
    if (s.score < 40) {
      lowSince[s.name] = lowSince[s.name] || Date.now();
      if (Date.now() - lowSince[s.name] >= 10000 && !pending.has(s.name)) flagStudent(s);
    } else {
      delete lowSince[s.name];
    }
  });
  if (!pending.size) renderTiles();
}, 2000);

function flagStudent(s) {
  pending.add(s.name);
  addLog(`${s.name} looks distracted.`);
  if ($("needApproval").checked) {
    $("callTitle").textContent = `${s.name} looks distracted`;
    $("callText").textContent = `The teacher avatar will say: "${s.name}, please stand up." Call out now?`;
    $("callDialog").showModal();
    $("callApprove").onclick = () => { $("callDialog").close(); callOut(s); };
    $("callDismiss").onclick = () => { $("callDialog").close(); resolve(s, "Dismissed"); };
  } else {
    callOut(s);
  }
}

async function callOut(s) {
  addLog(`Teacher avatar: "${s.name}, please stand up."`);
  if (API_BASE) {
    await fetch(`${API_BASE}/api/callout`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student: s.name }),
    });
  }
  // Placeholder: replace with real pose detection result from the backend.
  setTimeout(() => {
    const stood = Math.random() > 0.5;
    if (stood) {
      addLog(`${s.name} stood up.`);
      resolve(s, null);
    } else {
      addLog(`${s.name} did not stand up.`);
      if ($("autoWhatsapp").checked) sendWhatsapp(s);
      resolve(s, null);
    }
  }, 5000);
}

async function sendWhatsapp(s) {
  const phone = $("teacherPhone").value.trim();
  if (!phone) { addLog("Add your WhatsApp number in Settings to receive complaints."); return; }
  if (API_BASE) {
    await fetch(`${API_BASE}/api/whatsapp`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to: phone, student: s.name }),
    });
  }
  addLog(`WhatsApp complaint about ${s.name} sent to ${phone}.`);
}

function resolve(s, note) {
  if (note) addLog(`${s.name}: ${note}.`);
  s.score = 70;
  delete lowSince[s.name];
  pending.delete(s.name);
  renderTiles();
}

renderTiles();
