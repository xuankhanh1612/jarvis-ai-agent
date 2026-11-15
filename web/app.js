"use strict";

// The access key stays in memory only. Conversation history is sessionStorage
// (this tab only), and is sent to the server/model as context on each turn.
const STORAGE_KEY = "jarvis-web-conversation-v1";
const MAX_HISTORY = 24;
const MAX_CONTEXT_CHARS = 10000;
const MAX_MESSAGE_CHARS = 4000;
const $ = (id) => document.getElementById(id);
const shell = $("app-shell");
const overlay = $("lock-overlay");
const unlockForm = $("unlock-form");
const keyInput = $("access-key");
const unlockButton = $("unlock-button");
const unlockError = $("unlock-error");
const showKey = $("show-key");
const chatForm = $("chat-form");
const input = $("message-input");
const sendButton = $("send");
const micButton = $("mic");
const welcome = $("welcome");
const messagesNode = $("messages");
const threadScroll = $("thread-scroll");
const replyStatus = $("reply-status");
const statusPill = $("status-pill");
const statusText = $("connection-status");
const panelStatus = $("panel-status");
const newChatButtons = [$("new-chat"), $("new-chat-mobile")];

let accessKey = "";
let messages = loadHistory();
let busy = false;
let generation = 0;
let pendingController = null;
let recognition = null;

function loadHistory() {
  try {
    const data = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "[]");
    if (!Array.isArray(data)) return [];
    return data.filter((item) => item && ["user", "assistant"].includes(item.role) &&
      typeof item.content === "string" && item.content.trim() && item.content.length <= 30000)
      .slice(-MAX_HISTORY);
  } catch (_) {
    return [];
  }
}

function saveHistory() {
  messages = messages.slice(-MAX_HISTORY);
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages)); } catch (_) { /* usable without storage */ }
}

function setStatus(label, state) {
  statusText.textContent = label;
  panelStatus.textContent = label;
  statusPill.dataset.state = state;
}

function setBusy(value) {
  busy = value;
  input.disabled = value;
  sendButton.disabled = value;
  newChatButtons.forEach((button) => { button.disabled = value; });
  document.querySelectorAll(".suggestion").forEach((button) => { button.disabled = value; });
  micButton.disabled = value || !recognition;
  if (value) setStatus("Đang trả lời", "busy");
  else if (accessKey) setStatus("Sẵn sàng", "ready");
}

function scrollToLatest() {
  threadScroll.scrollTop = threadScroll.scrollHeight;
}

function renderText(container, text) {
  // Render as text nodes, not HTML. Fenced code gets a scrollable block.
  const pieces = text.split(/(```[^\n]*\n[\s\S]*?```)/g);
  for (const piece of pieces) {
    if (piece.startsWith("```") && piece.endsWith("```")) {
      const firstNewline = piece.indexOf("\n");
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = piece.slice(firstNewline + 1, -3).replace(/\n$/, "");
      pre.append(code);
      container.append(pre);
    } else {
      container.append(document.createTextNode(piece));
    }
  }
}

function appendMessage(message) {
  const row = document.createElement("article");
  row.className = `message ${message.role}`;
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = message.role === "user" ? "BẠN" : "✦";
  const body = document.createElement("div");
  body.className = "message-body";
  const heading = document.createElement("div");
  heading.className = "message-heading";
  const name = document.createElement("strong");
  name.textContent = message.role === "user" ? "Bạn" : "JARVIS";
  const detail = document.createElement("span");
  detail.textContent = message.role === "assistant" ? "Trợ lý AI" : "";
  heading.append(name, detail);
  const content = document.createElement("div");
  content.className = "message-content";
  renderText(content, message.content);
  body.append(heading, content);
  if (message.role === "assistant") {
    const tools = document.createElement("div");
    tools.className = "message-tools";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Sao chép";
    copy.setAttribute("aria-label", "Sao chép câu trả lời");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(message.content);
        copy.textContent = "Đã sao chép";
      } catch (_) { copy.textContent = "Không sao chép được"; }
      window.setTimeout(() => { copy.textContent = "Sao chép"; }, 2500);
    });
    tools.append(copy);
    if ("speechSynthesis" in window && "SpeechSynthesisUtterance" in window) {
      const speak = document.createElement("button");
      speak.type = "button";
      speak.textContent = "Đọc câu trả lời";
      speak.addEventListener("click", () => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(message.content);
        utterance.lang = "vi-VN";
        window.speechSynthesis.speak(utterance);
      });
      tools.append(speak);
    }
    body.append(tools);
  }
  row.append(avatar, body);
  messagesNode.append(row);
  welcome.hidden = true;
}

function renderHistory() {
  messagesNode.replaceChildren();
  welcome.hidden = messages.length > 0;
  messages.forEach(appendMessage);
  scrollToLatest();
}

function showReplyStatus(text, isError = false, canRetry = false) {
  replyStatus.hidden = false;
  replyStatus.classList.toggle("error", isError);
  replyStatus.replaceChildren(document.createTextNode(text));
  if (canRetry) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Thử lại";
    retry.addEventListener("click", () => { if (!busy && accessKey) requestReply(); });
    replyStatus.append(retry);
  }
  scrollToLatest();
}

function hideReplyStatus() {
  replyStatus.hidden = true;
  replyStatus.replaceChildren();
}

function contextForRequest() {
  const context = [];
  let count = 0;
  for (let i = messages.length - 1; i >= 0 && context.length < MAX_HISTORY; i--) {
    const remaining = MAX_CONTEXT_CHARS - count;
    if (remaining <= 0) break;
    const content = messages[i].content.slice(0, Math.min(MAX_MESSAGE_CHARS, remaining));
    if (!content.trim()) continue;
    context.unshift({ role: messages[i].role, content });
    count += content.length;
  }
  return context;
}

class RequestError extends Error {
  constructor(message, code, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function readResponse(response) {
  let data;
  try { data = await response.json(); }
  catch (_) { throw new RequestError("Máy chủ không trả về dữ liệu hợp lệ.", "invalid_response", response.status); }
  if (!response.ok) throw new RequestError(data.error || "Không thể kết nối tới JARVIS.", data.code, response.status);
  return data;
}

function lockSession(message = "") {
  generation += 1;
  if (pendingController) {
    pendingController.abort();
    if (messages.length && messages[messages.length - 1].role === "user") {
      showReplyStatus("Yêu cầu đã dừng. Mở khóa để thử lại.", true, true);
    }
  }
  pendingController = null;
  if (recognition) { try { recognition.abort(); } catch (_) { /* already stopped */ } }
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  accessKey = "";
  keyInput.value = "";
  keyInput.type = "password";
  showKey.textContent = "Hiện";
  showKey.setAttribute("aria-pressed", "false");
  showKey.setAttribute("aria-label", "Hiện khóa truy cập");
  unlockError.textContent = message;
  unlockError.hidden = !message;
  shell.inert = true;
  overlay.hidden = false;
  setBusy(false);
  setStatus("Đang khóa", "locked");
  keyInput.focus();
}

unlockForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const candidate = keyInput.value;
  unlockError.hidden = true;
  unlockButton.disabled = true;
  unlockButton.textContent = "Đang kết nối...";
  try {
    await readResponse(await fetch("/api/chat", {
      method: "GET", headers: { Authorization: `Bearer ${candidate}` }, cache: "no-store",
    }));
    accessKey = candidate;
    keyInput.value = "";
    overlay.hidden = true;
    shell.inert = false;
    setStatus("Sẵn sàng", "ready");
    input.focus();
    scrollToLatest();
  } catch (error) {
    unlockError.textContent = error instanceof RequestError ? error.message : "Không kết nối được máy chủ. Hãy thử lại.";
    unlockError.hidden = false;
  } finally {
    unlockButton.disabled = false;
    unlockButton.replaceChildren(document.createTextNode("Tiếp tục "));
    const arrow = document.createElement("span");
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "↗";
    unlockButton.append(arrow);
  }
});

showKey.addEventListener("click", () => {
  const showing = keyInput.type === "text";
  keyInput.type = showing ? "password" : "text";
  showKey.textContent = showing ? "Hiện" : "Ẩn";
  showKey.setAttribute("aria-pressed", String(!showing));
  showKey.setAttribute("aria-label", showing ? "Hiện khóa truy cập" : "Ẩn khóa truy cập");
  keyInput.focus();
});
$("lock").addEventListener("click", () => lockSession());

async function requestReply() {
  const requestGeneration = generation;
  const controller = new AbortController();
  pendingController = controller;
  setBusy(true);
  showReplyStatus("JARVIS đang suy nghĩ…");
  const timer = window.setTimeout(() => controller.abort(), 65000);
  try {
    const result = await readResponse(await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessKey}` },
      body: JSON.stringify({ messages: contextForRequest() }),
      signal: controller.signal,
      cache: "no-store",
    }));
    if (requestGeneration !== generation) return;
    if (typeof result.message !== "string" || !result.message.trim()) {
      throw new RequestError("Mô hình không trả về nội dung. Hãy thử lại.", "empty_response", 502);
    }
    const answer = { role: "assistant", content: result.message };
    messages.push(answer);
    saveHistory();
    hideReplyStatus();
    appendMessage(answer);
    scrollToLatest();
  } catch (error) {
    if (requestGeneration !== generation) return;
    if (error instanceof RequestError && error.status === 401) {
      lockSession("Phiên truy cập không còn hợp lệ. Vui lòng mở khóa lại.");
      return;
    }
    const explanation = error instanceof RequestError ? error.message :
      (error.name === "AbortError" ? "Yêu cầu đã hết thời gian chờ." : "Không kết nối được máy chủ. Hãy thử lại.");
    showReplyStatus(explanation, true, true);
  } finally {
    window.clearTimeout(timer);
    if (requestGeneration === generation) {
      pendingController = null;
      setBusy(false);
      input.focus();
    }
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || busy || !accessKey) return;
  const message = { role: "user", content: text };
  messages.push(message);
  saveHistory();
  input.value = "";
  hideReplyStatus();
  appendMessage(message);
  scrollToLatest();
  requestReply();
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt || "";
    input.focus();
  });
});

function newChat() {
  if (busy || (messages.length && !window.confirm("Xóa lịch sử trò chuyện trong tab này?"))) return;
  messages = [];
  saveHistory();
  hideReplyStatus();
  renderHistory();
  input.value = "";
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  input.focus();
}
newChatButtons.forEach((button) => button.addEventListener("click", newChat));

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (Recognition) {
  recognition = new Recognition();
  recognition.lang = "vi-VN";
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.onstart = () => { micButton.querySelector("span").textContent = "Đang nghe…"; };
  recognition.onend = () => { micButton.querySelector("span").textContent = "Giọng nói"; };
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = `${input.value}${input.value ? " " : ""}${transcript}`.slice(0, MAX_MESSAGE_CHARS);
    input.focus();
  };
  recognition.onerror = () => { showReplyStatus("Không thể nhận giọng nói. Hãy kiểm tra quyền micro của trình duyệt.", true); };
  micButton.title = "Nhận dạng giọng nói do trình duyệt cung cấp; âm thanh có thể được gửi tới dịch vụ của trình duyệt.";
  micButton.addEventListener("click", () => { try { recognition.start(); } catch (_) { recognition.stop(); } });
} else {
  micButton.disabled = true;
  micButton.title = "Trình duyệt này không hỗ trợ nhập bằng giọng nói.";
}

renderHistory();
setStatus("Đang khóa", "locked");
keyInput.focus();
