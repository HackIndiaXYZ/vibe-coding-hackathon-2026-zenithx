/***************************************
  GLOBAL STATE
***************************************/
let selectedCategory = "";
let selectedState = "";
let selectedIncome = "";
let selectedRation = "";

/***************************************
  SCREEN REFERENCES
***************************************/
const screens = {
  category: document.getElementById("selectionScreen"),
  state: document.getElementById("stateScreen"),
  form: document.getElementById("formScreen"),
  result: document.getElementById("resultScreen"),
};

const steps = {
  1: document.getElementById("step1"),
  2: document.getElementById("step2"),
  3: document.getElementById("step3"),
  4: document.getElementById("step4"),
};

/***************************************
  SPEECH
  ✅ added onEndCallback so voice can chain
***************************************/
function speakHindi(text, onEndCallback) {
  if (!text || typeof text !== "string") { if (onEndCallback) onEndCallback(); return; }
  if (!("speechSynthesis" in window))    { if (onEndCallback) onEndCallback(); return; }

  const clean = text.replace(/[^\w\s\u0900-\u097F\n,।.()/-]/g, "");
  window.speechSynthesis.cancel();
  const msg = new SpeechSynthesisUtterance(clean);
  msg.lang = "hi-IN";
  msg.rate = 0.9;

  // pick Hindi voice if available
  const voices = window.speechSynthesis.getVoices();
  const hindiVoice = voices.find(v => v.lang && v.lang.startsWith("hi"));
  if (hindiVoice) msg.voice = hindiVoice;

  if (onEndCallback) { msg.onend = onEndCallback; msg.onerror = onEndCallback; }
  window.speechSynthesis.speak(msg);
}

/***************************************
  SCREEN SWITCH
***************************************/
function showScreen(screenName, stepNo, voiceText = "") {
  Object.values(screens).forEach(s => s && s.classList.remove("active"));
  screens[screenName]?.classList.add("active");

  Object.values(steps).forEach(s => s && s.classList.remove("active"));
  steps[stepNo]?.classList.add("active");

  if (voiceText) speakHindi(voiceText);
}

/***************************************
  CATEGORY
***************************************/
function selectCategory(el, category) {
  document.querySelectorAll(".category-card")
    .forEach(c => c.classList.remove("selected"));

  el.classList.add("selected");
  selectedCategory = category;

  setTimeout(() => {
    showScreen("state", 2, "अब अपना राज्य चुनिए।");
  }, 300);
}

/***************************************
  STATE
***************************************/
function selectState(el, state) {
  document.querySelectorAll("#stateScreen .category-card")
    .forEach(c => c.classList.remove("selected"));

  el.classList.add("selected");
  selectedState = state;

  const title = document.getElementById("selectedTitle");
  if (title) {
    title.innerText = `आप ${state} राज्य के ${selectedCategory} के लिए योजनाएँ देख रहे हैं`;
  }

  setTimeout(() => {
    showScreen("form", 3, "अब अपनी जानकारी भरिए।");
  }, 300);
}

/***************************************
  CHECK ELIGIBILITY
***************************************/
async function checkEligibility() {
  const resultDiv = document.getElementById("schemesContainer");
  resultDiv.innerHTML = "लोड हो रहा है...";

  selectedIncome = document.getElementById("income")?.value || "";
  selectedRation = document.getElementById("ration")?.value || "";

  sendAnalytics({
    category: selectedCategory,
    state:    selectedState,
    income:   selectedIncome,
    ration:   selectedRation
  });

  try {
    const res = await fetch(
      `http://localhost:5000/api/schemes?category=${encodeURIComponent(selectedCategory)}&state=${encodeURIComponent(selectedState)}`
    );

    if (!res.ok) throw new Error("Scheme API failed");

    const schemes = await res.json();
    resultDiv.innerHTML = "";

    if (!Array.isArray(schemes) || schemes.length === 0) {
      resultDiv.innerHTML = "<p>कोई योजना नहीं मिली।</p>";
      goToResult();
      return;
    }

    schemes.forEach((scheme) => {
      const card = document.createElement("div");
      card.className = "scheme-card";

      card.innerHTML = `
        <h3>${scheme?.name || "योजना नाम"}</h3>

        <p><strong>विवरण:</strong> ${scheme?.description || "उपलब्ध नहीं"}</p>
        <p><strong>श्रेणी:</strong> ${scheme?.category || "निर्दिष्ट नहीं"}</p>
        <p><strong>राज्य:</strong> ${scheme?.state || "सभी राज्य"}</p>

        ${scheme?.officialLink || scheme?.website ? `
          <a href="${scheme.officialLink || scheme.website}" target="_blank" class="apply-btn">
            आधिकारिक वेबसाइट देखें
          </a>` : ""}

        <div id="aiExplanation-${scheme._id}" class="ai-box">
          <div class="ai-box-header">AI व्याख्या (Groq)</div>
          <em>लोड हो रही है...</em>
        </div>
      `;

      resultDiv.appendChild(card);

      setTimeout(() => {
        explainScheme(scheme);
      }, 500);
    });

    goToResult();

    // Load Jan Seva Kendra map after schemes — delay so AI explanations start first
    setTimeout(() => loadNearbyJSK(), 2500);

  } catch (err) {
    console.error("Server Error:", err);
    resultDiv.innerHTML = "<p>सर्वर त्रुटि — बैकएंड चालू है?</p>";
  }
}

/***************************************
  AI EXPLANATION
  ✅ after explanation → auto voice Q&A
***************************************/
async function explainScheme(scheme) {
  if (!scheme || !scheme._id) return;

  const box = document.getElementById(`aiExplanation-${scheme._id}`);
  if (!box) return;

  try {
    const res = await fetch("http://localhost:5000/api/ai-explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scheme: scheme })
    });

    if (!res.ok) throw new Error("AI API failed: " + res.status);

    const data = await res.json();

    if (data?.explanation) {
      renderExplanationWithQA(box, scheme, data.explanation);
    } else {
      box.innerHTML = `
        <div class="ai-box-header">AI व्याख्या</div>
        <div class="ai-text">AI व्याख्या उपलब्ध नहीं है।</div>
      `;
    }

  } catch (err) {
    console.error("AI Error:", err);
    const fallback = `${scheme.name} — यह ${scheme.state || "भारत"} में ${scheme.category} वर्ग के लिए एक सरकारी योजना है।\n\n${scheme.description || ""}\n\nपात्रता: ${scheme.eligibility || "सरकारी मानदंड के अनुसार"}\nआवेदन: नज़दीकी सरकारी कार्यालय या आधिकारिक वेबसाइट पर जाएं।`;
    renderExplanationWithQA(box, scheme, fallback);
  }
}

/***************************************
  RENDER EXPLANATION + INLINE VOICE Q&A
  no popup, no new page — only voice
***************************************/
function renderExplanationWithQA(box, scheme, explanation) {
  box.innerHTML = `
    <div class="ai-box-header">AI व्याख्या (Groq)</div>
    <div class="ai-text">${explanation}</div>
    <div class="voice-qa">
      <div class="voice-qa-status" id="qaStatus-${scheme._id}">🎙️ क्या आपको कुछ पूछना है?</div>
      <div class="voice-qa-transcript" id="qaTranscript-${scheme._id}"></div>
      <div class="voice-qa-answer" id="qaAnswer-${scheme._id}"></div>
      <button class="voice-qa-btn" id="qaBtn-${scheme._id}"
        onclick="startVoiceQA('${scheme._id}', ${JSON.stringify(scheme).replace(/"/g, '&quot;')})">
        🎤 बोलिए / Ask
      </button>
    </div>
  `;

  // only speak + auto-ask on the very first scheme card
  const isFirst = document.querySelectorAll(".ai-text").length === 1;
  if (isFirst) {
    speakHindi(explanation.substring(0, 350), () => {
      setTimeout(() => {
        speakHindi("क्या आपको कुछ पूछना है? बोलिए।", () => {
          setTimeout(() => listenAndAnswer(scheme._id, scheme), 400);
        });
      }, 600);
    });
  }
}

/***************************************
  VOICE Q&A — manual trigger via button
***************************************/
function startVoiceQA(schemeId, scheme) {
  window.speechSynthesis.cancel();
  document.getElementById(`qaTranscript-${schemeId}`).textContent = "";
  document.getElementById(`qaAnswer-${schemeId}`).textContent     = "";
  listenAndAnswer(schemeId, scheme);
}

/***************************************
  LISTEN → SEND TO BACKEND → SPEAK ANSWER
***************************************/
function listenAndAnswer(schemeId, scheme) {
  const statusEl     = document.getElementById(`qaStatus-${schemeId}`);
  const transcriptEl = document.getElementById(`qaTranscript-${schemeId}`);
  const answerEl     = document.getElementById(`qaAnswer-${schemeId}`);
  const btn          = document.getElementById(`qaBtn-${schemeId}`);
  if (!statusEl) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    statusEl.textContent = "❌ Chrome browser में खोलें — voice support नहीं मिला।";
    return;
  }

  const recognition        = new SpeechRecognition();
  recognition.lang         = "hi-IN";
  recognition.interimResults  = false;
  recognition.maxAlternatives = 1;

  statusEl.textContent = "🎙️ सुन रहा हूँ... बोलिए";
  statusEl.style.color = "#e74c3c";
  if (btn) btn.disabled = true;

  recognition.start();

  recognition.onresult = async (event) => {
    const question = event.results[0][0].transcript;
    transcriptEl.textContent = `आपने पूछा: "${question}"`;
    statusEl.textContent     = "⏳ जवाब ढूंढा जा रहा है...";
    statusEl.style.color     = "#f39c12";

    try {
      // backend reads GROQ_API_KEY from .env
      const res = await fetch("http://localhost:5000/api/ai-explain", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ scheme, question })
      });
      if (!res.ok) throw new Error("backend " + res.status);

      const data   = await res.json();
      const answer = data?.explanation || data?.answer || "";
      if (!answer) throw new Error("empty");

      answerEl.textContent = answer;
      statusEl.textContent = "✅ जवाब मिल गया";
      statusEl.style.color = "#2ecc71";

      speakHindi(answer, () => {
        setTimeout(() => {
          statusEl.textContent = "🎙️ और कुछ पूछना है?";
          statusEl.style.color = "";
        }, 500);
      });

    } catch (err) {
      console.error("Q&A Error:", err);
      const fallback = "माफ़ करें, अभी जवाब नहीं मिला। आधिकारिक वेबसाइट देखें।";
      answerEl.textContent = fallback;
      statusEl.textContent = "⚠️ त्रुटि हुई";
      statusEl.style.color = "#e74c3c";
      speakHindi(fallback);
    }

    if (btn) btn.disabled = false;
  };

  recognition.onerror = () => {
    statusEl.textContent = "❌ आवाज़ नहीं सुनाई दी। फिर से कोशिश करें।";
    statusEl.style.color = "#e74c3c";
    if (btn) btn.disabled = false;
  };

  recognition.onend = () => { if (btn) btn.disabled = false; };
}

/***************************************
  ANALYTICS
***************************************/
function sendAnalytics(data) {
  fetch("http://localhost:5000/api/analytics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      category:  data.category,
      state:     data.state,
      income:    data.income,
      ration:    data.ration,
      timestamp: new Date().toISOString()
    })
  })
  .then(() => console.log("Analytics saved"))
  .catch(() => {});
}

/***************************************
  HAVERSINE DISTANCE HELPER (km)
***************************************/
function getDistKm(lat1, lon1, lat2, lon2) {
  const R    = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a    = Math.sin(dLat/2)**2 +
               Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) *
               Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

/***************************************
  JAN SEVA KENDRA MAP
  — shows centers within 2km
  — if none in 2km, shows the nearest one
  — automatic voice narration
***************************************/
let _jskMap = null;

function loadNearbyJSK() {
  const section  = document.getElementById("jskSection");
  const statusEl = document.getElementById("jskStatus");
  const listEl   = document.getElementById("jskList");
  if (!section) return;

  section.style.display = "block";
  statusEl.textContent  = "📡 आपकी लोकेशन ढूंढी जा रही है...";

  if (!navigator.geolocation) {
    statusEl.textContent = "❌ आपका ब्राउज़र location support नहीं करता।";
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;

      statusEl.textContent = "🗺️ 2 किमी के अंदर जन सेवा केंद्र ढूंढे जा रहे हैं...";

      try {
        // First try: 2km radius
        const res  = await fetch(`http://localhost:5000/api/nearby-jsk?lat=${lat}&lon=${lon}&radius=2000`);
        const data = await res.json();
        let centers = data.centers || [];

        // Sort all by distance
        centers = centers
          .map(c => ({ ...c, distKm: getDistKm(lat, lon, c.lat, c.lon) }))
          .sort((a, b) => a.distKm - b.distKm);

        // Split: within 2km vs beyond
        const within2km = centers.filter(c => c.distKm <= 2);
        let   fallbackNearest = null;
        let   isFallback      = false;

        if (!within2km.length) {
          // No center within 2km — fetch wider (20km) to find the nearest one
          isFallback = true;
          statusEl.textContent = "🔍 2 किमी में नहीं मिला, सबसे नज़दीकी ढूंढा जा रहा है...";

          const res2  = await fetch(`http://localhost:5000/api/nearby-jsk?lat=${lat}&lon=${lon}&radius=20000`);
          const data2 = await res2.json();
          const wider = (data2.centers || [])
            .map(c => ({ ...c, distKm: getDistKm(lat, lon, c.lat, c.lon) }))
            .sort((a, b) => a.distKm - b.distKm);

          if (wider.length) {
            fallbackNearest = wider[0];
            centers = [fallbackNearest]; // show only the nearest on map
          }
        } else {
          centers = within2km;
        }

        // Init / reset Leaflet map
        if (_jskMap) { _jskMap.remove(); _jskMap = null; }
        const zoom  = isFallback ? 13 : 15;
        _jskMap = L.map("jskMap").setView([lat, lon], zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: "© OpenStreetMap"
        }).addTo(_jskMap);

        // User marker
        const userIcon = L.divIcon({ className:"", html:`<div style="font-size:28px">📍</div>`, iconAnchor:[14,28] });
        L.marker([lat, lon], { icon: userIcon })
          .addTo(_jskMap)
          .bindPopup("<b>आपकी लोकेशन</b>")
          .openPopup();

        listEl.innerHTML = "";

        if (!centers.length) {
          // Truly nothing found anywhere
          statusEl.textContent = "ℹ️ नज़दीक कोई केंद्र नहीं मिला। Google Maps पर खोजें।";
          speakHindi("आपके नज़दीक कोई जन सेवा केंद्र नहीं मिला। कृपया गूगल मैप्स पर जन सेवा केंद्र खोजें।");
          return;
        }

        // CSC icon — green for within 2km, orange for fallback
        const cscHtml  = isFallback
          ? `<div style="font-size:24px;filter:sepia(1) saturate(5) hue-rotate(10deg)">🏛️</div>`
          : `<div style="font-size:24px">🏛️</div>`;
        const cscIcon  = L.divIcon({ className:"", html: cscHtml, iconAnchor:[12,24] });

        centers.forEach((c) => {
          const distStr = c.distKm < 1
            ? `${(c.distKm * 1000).toFixed(0)} मीटर`
            : `${c.distKm.toFixed(2)} किमी`;

          // Map marker with popup
          L.marker([c.lat, c.lon], { icon: cscIcon })
            .addTo(_jskMap)
            .bindPopup(`<b>${c.name}</b><br>${c.address || ""}<br><small>📏 ${distStr} दूर</small>`);

          // Draw line from user to center
          L.polyline([[lat, lon], [c.lat, c.lon]], {
            color: isFallback ? "#e67e22" : "#2980b9",
            weight: 2, dashArray: "6,4", opacity: 0.7
          }).addTo(_jskMap);

          // List card
          const badge = isFallback
            ? `<span class="jsk-badge jsk-badge-far">📍 निकटतम केंद्र</span>`
            : `<span class="jsk-badge jsk-badge-near">✅ 2 किमी के अंदर</span>`;

          const item = document.createElement("div");
          item.className = "jsk-item";
          item.innerHTML = `
            <div class="jsk-item-icon">🏛️</div>
            <div style="flex:1">
              ${badge}
              <div class="jsk-item-name">${c.name}</div>
              <div class="jsk-item-addr">${c.address || "पता उपलब्ध नहीं"}</div>
              ${c.phone ? `<div class="jsk-item-addr">📞 ${c.phone}</div>` : ""}
              <div class="jsk-item-dist">📏 ${distStr} दूर</div>
            </div>
            <a class="jsk-directions-btn"
              href="https://www.google.com/maps/dir/?api=1&origin=${lat},${lon}&destination=${c.lat},${c.lon}"
              target="_blank">🗺️ Directions</a>
          `;
          listEl.appendChild(item);
        });

        // Status bar update
        if (isFallback) {
          statusEl.textContent = `⚠️ 2 किमी में कोई केंद्र नहीं — सबसे नज़दीकी: ${centers[0].name} (${centers[0].distKm.toFixed(1)} किमी)`;
        } else {
          statusEl.textContent = `✅ ${centers.length} जन सेवा केंद्र मिले — 2 किमी के अंदर`;
        }

        // ── AUTOMATIC VOICE NARRATION ──
        const nearest  = centers[0];
        const distStr  = nearest.distKm < 1
          ? `${(nearest.distKm * 1000).toFixed(0)} मीटर`
          : `${nearest.distKm.toFixed(1)} किलोमीटर`;
        const addrText = nearest.address ? `यह ${nearest.address} में स्थित है।` : "";

        let voiceText;
        if (isFallback) {
          voiceText = `2 किलोमीटर के अंदर कोई जन सेवा केंद्र नहीं मिला। लेकिन सबसे नज़दीकी केंद्र ${nearest.name} है, जो आपसे लगभग ${distStr} दूर है। ${addrText} आप वहाँ जाकर इन योजनाओं के लिए आवेदन कर सकते हैं।`;
        } else {
          voiceText = `आपके 2 किलोमीटर के अंदर ${centers.length} जन सेवा केंद्र मिले हैं। सबसे नज़दीकी केंद्र ${nearest.name} है, जो आपसे सिर्फ ${distStr} दूर है। ${addrText} वहाँ जाकर आप इन योजनाओं के लिए आवेदन कर सकते हैं।`;
        }

        speakHindi(voiceText);

      } catch (err) {
        console.error("JSK Error:", err);
        statusEl.textContent = "⚠️ केंद्र लोड नहीं हो सके। बैकएंड चालू है?";
      }
    },
    () => {
      statusEl.textContent = "❌ Location access नहीं मिली। Browser में location allow करें।";
      speakHindi("लोकेशन की अनुमति नहीं मिली। कृपया ब्राउज़र में लोकेशन allow करें।");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

/***************************************
  SEARCH
***************************************/
function filterSchemes() {
  const input = document.getElementById("searchInput");
  if (!input) return;

  const value = input.value.toLowerCase();

  document.querySelectorAll(".scheme-card").forEach(card => {
    card.style.display =
      card.innerText.toLowerCase().includes(value) ? "block" : "none";
  });
}

/***************************************
  NAVIGATION
***************************************/
function goToResult() {
  showScreen("result", 4, "आपके लिए योजनाएँ दिखा दी गई हैं।");
}

function goBackToCategory() {
  showScreen("category", 1);
}

function goBackToState() {
  showScreen("state", 2, "कृपया राज्य चुनिए।");
}

function goBackToForm() {
  showScreen("form", 3, "अब अपनी जानकारी फिर से भरें।");
}

function restart() {
  selectedCategory = "";
  selectedState    = "";
  selectedIncome   = "";
  selectedRation   = "";
  // hide map section on restart
  const jskSection = document.getElementById("jskSection");
  if (jskSection) jskSection.style.display = "none";
  if (_jskMap) { _jskMap.remove(); _jskMap = null; }
  showScreen("category", 1, "नई खोज शुरू करें।");
}

/***************************************
  AUTO LOAD
***************************************/
window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
window.onload = () => {
  window.speechSynthesis.getVoices();
  showScreen("category", 1, "सरकार सेतु में आपका स्वागत है।");
};