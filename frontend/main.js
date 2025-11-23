// ==========================
// ESTADO GLOBAL
// ==========================
let conversationId = null;
let preferredFormat = null; // "video" | "audio" | "texto" | null

// contador de alterações no chat
let chatRevision = 0;
// última revisão analisada/gerada
let lastAnalyzedRevision = null;
let lastAnalyzedConversationId = null;

let isAnalyzing = false; // evita flood de chamadas

// ==========================
// ELEMENTOS
// ==========================
const tabChat = document.getElementById("tab-chat");
const tabIngest = document.getElementById("tab-ingest");
const tabStudy = document.getElementById("tab-study");

const sectionChat = document.getElementById("section-chat");
const sectionIngest = document.getElementById("section-ingest");
const sectionStudy = document.getElementById("section-study");

const chatBox = document.getElementById("chat-box");
const chatInput = document.getElementById("chat-input");
const chatForm = document.getElementById("chat-form");
const chatStatus = document.getElementById("chat-status");
const convLabel = document.getElementById("conversation-id-label");

const formatSelect = document.getElementById("format-select");
const formatCurrentLabel = document.getElementById("format-current-label");

const ingestForm = document.getElementById("ingest-form");
const ingestStatus = document.getElementById("ingest-status");

const contentsBox = document.getElementById("contents-box");

// ==========================
// NAV / PÁGINAS
// ==========================
function setActiveTab(page) {
  // Reset classes
  [tabChat, tabIngest, tabStudy].forEach((btn) => {
    btn.className =
      "px-4 py-2 rounded-full font-medium bg-white text-slate-700 border border-slate-300 hover:bg-slate-50";
  });

  if (page === "chat") {
    tabChat.className =
      "px-4 py-2 rounded-full font-medium bg-slate-800 text-white shadow-sm";
  } else if (page === "ingest") {
    tabIngest.className =
      "px-4 py-2 rounded-full font-medium bg-slate-800 text-white shadow-sm";
  } else if (page === "study") {
    tabStudy.className =
      "px-4 py-2 rounded-full font-medium bg-slate-800 text-white shadow-sm";
  }

  sectionChat.classList.toggle("hidden", page !== "chat");
  sectionIngest.classList.toggle("hidden", page !== "ingest");
  sectionStudy.classList.toggle("hidden", page !== "study");

  // Gatilho automático: ao abrir "Estudar", dispara análise/geração (com cache)
  if (page === "study") {
    maybeTriggerAnalysisOnStudyTab();
  }
}

tabChat.addEventListener("click", () => setActiveTab("chat"));
tabIngest.addEventListener("click", () => setActiveTab("ingest"));
tabStudy.addEventListener("click", () => setActiveTab("study"));

// Tela inicial = Chat
setActiveTab("chat");

// ==========================
// UTILIDADES
// ==========================
function appendMessage(role, text) {
  const bubble = document.createElement("div");
  bubble.className =
    "mb-2 max-w-[90%] " +
    (role === "user"
      ? "ml-auto bg-emerald-600 text-white rounded-xl rounded-br-sm px-3 py-2"
      : "mr-auto bg-white border border-slate-200 text-slate-800 rounded-xl rounded-bl-sm px-3 py-2");
  bubble.textContent = text;
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function updatePreferredFormatLabel() {
  if (!preferredFormat) {
    formatCurrentLabel.textContent = "(usando: automático)";
  } else {
    formatCurrentLabel.textContent = "(usando: " + preferredFormat + ")";
  }
}

// ==========================
// FORMATO PREFERIDO
// ==========================
formatSelect.addEventListener("change", () => {
  const value = formatSelect.value || null;
  preferredFormat = value ? value : null;
  updatePreferredFormatLabel();
});

// ==========================
// CHAT (SEM BOTÃO "NOVA CONVERSA")
// ==========================
async function ensureConversationStarted() {
  if (conversationId) return;
  const resp = await fetch("/api/conversation/start", {
    method: "POST",
  });
  const data = await resp.json();
  conversationId = data.conversation_id;
  convLabel.textContent = "Conversa iniciada";
  // nova conversa => nenhuma análise ainda
  lastAnalyzedRevision = null;
  lastAnalyzedConversationId = null;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  chatStatus.textContent = "";
  appendMessage("user", text);
  chatInput.value = "";
  chatStatus.textContent = "Enviando...";

  try {
    // Se ainda não existir conversa, cria aqui (gatilho na 1ª mensagem)
    await ensureConversationStarted();

    const resp = await fetch("/api/conversation/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        top_k: 5,
        conversation_id: conversationId,
      }),
    });
    const data = await resp.json();
    conversationId = data.conversation_id;
    appendMessage("assistant", data.answer);
    chatStatus.textContent = "";

    // Houve uma nova interação no chat -> incrementa revisão
    chatRevision += 1;
  } catch (err) {
    console.error(err);
    chatStatus.textContent = "Erro ao enviar mensagem.";
  }
});

// ==========================
// INGESTÃO
// ==========================
ingestForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const titleInput = document.getElementById("title-input");
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (titleInput.value.trim()) {
    formData.append("title", titleInput.value.trim());
  }

  ingestStatus.textContent = "Enviando arquivo para ingestão...";
  try {
    const resp = await fetch("/api/ingest", {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    if (data.skipped) {
      ingestStatus.textContent =
        "Ingestão ignorada: " + (data.reason || "já ingerido.");
    } else {
      ingestStatus.textContent =
        "Ingestão concluída. Chunks inseridos: " + data.inserted_chunks;
    }
  } catch (err) {
    console.error(err);
    ingestStatus.textContent = "Erro na ingestão.";
  }
});

// ==========================
// ESTUDAR – APENAS CONTEÚDOS, COM CACHE
// ==========================
function shouldReanalyze() {
  if (!conversationId) {
    // sem conversa -> sempre mostra mensagem padrão
    return true;
  }
  // Se nunca houve análise para essa conversa
  if (
    lastAnalyzedConversationId === null ||
    lastAnalyzedConversationId !== conversationId
  ) {
    return true;
  }
  // Se houve novas mensagens desde a última análise
  if (lastAnalyzedRevision === null || chatRevision > lastAnalyzedRevision) {
    return true;
  }
  // Nenhuma mudança no chat e mesma conversa -> não precisa gerar de novo
  return false;
}

async function maybeTriggerAnalysisOnStudyTab() {
  // Se não precisa re-analisar, só deixa os conteúdos já renderizados
  if (!shouldReanalyze()) {
    return;
  }

  contentsBox.innerHTML = "";

  if (!conversationId) {
    contentsBox.innerHTML =
      '<p class="text-sm text-slate-500">Nenhuma conversa encontrada. Vá para a aba Chat, converse um pouco e volte para Estudar.</p>';
    return;
  }

  if (isAnalyzing) {
    return; // evita chamadas duplicadas se clicar rápido
  }

  isAnalyzing = true;
  contentsBox.innerHTML =
    '<p class="text-sm text-slate-500">Gerando conteúdos personalizados...</p>';

  try {
    const resp = await fetch(
      `/api/conversation/${conversationId}/analyze-and-generate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preferred_format: preferredFormat,
        }),
      }
    );
    const data = await resp.json();

    const contents = data.contents || [];
    if (!contents.length) {
      contentsBox.innerHTML =
        '<p class="text-sm text-slate-500">Nenhum conteúdo gerado.</p>';
    } else {
      contentsBox.innerHTML = "";
      for (const c of contents) {
        const card = document.createElement("article");
        card.className =
          "border border-slate-200 bg-slate-50 rounded-xl p-3 flex flex-col gap-2 text-sm";
        const badge = document.createElement("span");
        badge.className =
          "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-white w-fit";
        badge.textContent = `${c.content_type.toUpperCase()} • ${c.subtema}`;
        const title = document.createElement("h3");
        title.className = "font-semibold text-slate-800 text-sm";
        title.textContent = c.title || "(sem título)";
        const script = document.createElement("p");
        script.className = "text-slate-700 whitespace-pre-wrap text-xs";
        script.textContent = c.script || "";
        card.appendChild(badge);
        card.appendChild(title);
        card.appendChild(script);
        contentsBox.appendChild(card);
      }
    }

    // Marca que essa conversa + revisão já foi analisada
    lastAnalyzedConversationId = conversationId;
    lastAnalyzedRevision = chatRevision;
  } catch (err) {
    console.error(err);
    contentsBox.innerHTML =
      '<p class="text-sm text-red-500">Erro ao gerar conteúdos.</p>';
  } finally {
    isAnalyzing = false;
  }
}
