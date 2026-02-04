const API = "/api";

const $ = (id) => document.getElementById(id);

const TYPE_LABELS = {
  casa: "Casa",
  faculdade: "Faculdade",
  saude: "Saúde",
  lazer: "Lazer",
  alimentacao: "Alimentação",
  transporte: "Transporte",
  outros: "Outros",
};

const state = {
  user: null,
  authMode: "login",
};

const elements = {
  authOverlay: $("auth-overlay"),
  authError: $("auth-error"),
  loginForm: $("login-form"),
  registerForm: $("register-form"),
  loginUsername: $("login-username"),
  loginPassword: $("login-password"),
  registerUsername: $("register-username"),
  registerPassword: $("register-password"),
  authTabLogin: $("auth-tab-login"),
  authTabRegister: $("auth-tab-register"),
  headerAuth: $("header-auth"),
  headerUsername: $("header-username"),
  logoutBtn: $("btn-logout"),
  balanceInput: $("balance-input"),
  balanceError: $("balance-error"),
  zoneBadge: $("zone-badge"),
  summaryExpenses: $("summary-expenses"),
  summaryPercent: $("summary-percent"),
  summaryCount: $("summary-count"),
  cardsList: $("cards-list"),
};

function showError(el, message) {
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("hidden", !message);
}

function formatMoney(value) {
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value) {
  return `${Number(value).toFixed(2)}%`;
}

function escapeHtml(value = "") {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showAuthError(message = "") {
  showError(elements.authError, message);
}

function switchAuthMode(mode) {
  state.authMode = mode;
  if (mode === "login") {
    elements.authTabLogin.classList.add("auth-tab--active");
    elements.authTabRegister.classList.remove("auth-tab--active");
    elements.loginForm.classList.remove("hidden");
    elements.registerForm.classList.add("hidden");
    showAuthError();
    setTimeout(() => elements.loginUsername.focus(), 50);
  } else {
    elements.authTabRegister.classList.add("auth-tab--active");
    elements.authTabLogin.classList.remove("auth-tab--active");
    elements.registerForm.classList.remove("hidden");
    elements.loginForm.classList.add("hidden");
    showAuthError();
    setTimeout(() => elements.registerUsername.focus(), 50);
  }
}

function showAuthOverlay(mode = state.authMode) {
  switchAuthMode(mode);
  elements.authOverlay.classList.remove("hidden");
}

function hideAuthOverlay() {
  elements.authOverlay.classList.add("hidden");
  showAuthError();
  elements.loginForm.reset();
  elements.registerForm.reset();
}

function setCurrentUser(user) {
  state.user = user;
  if (user) {
    elements.headerUsername.textContent = user.username;
    elements.headerAuth.classList.remove("hidden");
    elements.logoutBtn.disabled = false;
  } else {
    elements.headerAuth.classList.add("hidden");
    elements.logoutBtn.disabled = true;
  }
}

function resetAppState() {
  elements.balanceInput.value = "";
  showError(elements.balanceError);
  elements.zoneBadge.textContent = "—";
  elements.zoneBadge.className = "zone zone--verde";
  elements.summaryExpenses.textContent = "—";
  elements.summaryPercent.textContent = "—";
  elements.summaryCount.textContent = "—";
  elements.cardsList.innerHTML = '<p class="muted">Faça login para visualizar suas despesas.</p>';
}

function promptLogin(message = "") {
  setCurrentUser(null);
  resetAppState();
  showAuthOverlay("login");
  showAuthError(message);
}

function handleUnauthorized() {
  promptLogin("Sessão expirada. Faça login novamente.");
}

async function api(path, options = {}) {
  const { skipAuthOn401, headers: customHeaders, ...rest } = options;
  const config = {
    method: (rest.method || "GET").toUpperCase(),
    credentials: "include",
    ...rest,
  };
  const headers = {
    "Content-Type": "application/json",
    ...(customHeaders || {}),
  };
  if (!config.body && config.method === "GET") {
    delete headers["Content-Type"];
  }
  config.headers = headers;

  const response = await fetch(API + path, config);
  const text = response.status === 204 ? "" : await response.text();
  let parsed = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (response.status === 401) {
    if (!skipAuthOn401) handleUnauthorized();
    const message = (parsed && parsed.detail) || "Não autorizado";
    const error = new Error(message);
    error.status = 401;
    throw error;
  }

  if (!response.ok) {
    const message =
      (parsed && parsed.detail) ||
      (parsed && parsed.message) ||
      (typeof parsed === "string" ? parsed : "") ||
      response.statusText ||
      "Erro inesperado";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }
  return parsed;
}

async function fetchCurrentUser() {
  try {
    const user = await api("/auth/me", { skipAuthOn401: true });
    if (user) {
      setCurrentUser(user);
      hideAuthOverlay();
      return user;
    }
  } catch (err) {
    if (err.status !== 401) {
      throw err;
    }
  }
  promptLogin();
  return null;
}

async function loadBalance() {
  const data = await api("/balance");
  elements.balanceInput.value = Number.isFinite(data.net_balance) ? data.net_balance : "";
  return data;
}

async function saveBalance() {
  const raw = elements.balanceInput.value.trim().replace(",", ".");
  const value = parseFloat(raw);
  showError(elements.balanceError);
  if (raw === "" || Number.isNaN(value) || value < 0) {
    showError(elements.balanceError, "Informe um valor válido.");
    return;
  }
  await api("/balance", { method: "PUT", body: JSON.stringify({ net_balance: value }) });
  elements.balanceInput.value = value;
  showError(elements.balanceError);
  await loadSummary();
  await loadCards();
}

async function loadSummary() {
  const data = await api("/cards/summary");
  elements.zoneBadge.textContent = data.zone.toUpperCase();
  elements.zoneBadge.className = "zone zone--" + data.zone;
  elements.summaryExpenses.textContent = "R$ " + formatMoney(data.total_expenses);
  elements.summaryPercent.textContent = formatPercent(data.total_percentage);
  elements.summaryCount.textContent = data.cards_count;
  return data;
}

function getFilters() {
  const statusFilter = $("filter-status").value || undefined;
  const expenseType = $("filter-type").value || undefined;
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);
  if (expenseType) params.set("expense_type", expenseType);
  const q = params.toString();
  return q ? "?" + q : "";
}

async function loadCards() {
  const list = elements.cardsList;
  try {
    const data = await api("/cards" + getFilters());
    if (!Array.isArray(data) || data.length === 0) {
      list.innerHTML = '<p class="muted">Nenhuma despesa cadastrada. Clique em "Nova despesa" para adicionar.</p>';
      return;
    }
    list.innerHTML = data
      .map((c) => {
        const title = (c.title || "").trim() || "(sem título)";
        const safeTitle = escapeHtml(title);
        const safeType = escapeHtml(TYPE_LABELS[c.expense_type] ?? c.expense_type);
        return `
        <article class="card-item" data-id="${c.id}">
          <span class="card-item__title" title="${safeTitle}">${safeTitle}</span>
          <span class="card-item__urgency">${c.urgency}</span>
          <span class="card-item__type">${safeType}</span>
          <span class="card-item__value">${formatMoney(c.value)}</span>
          <span class="card-item__percent">${formatPercent(c.percentage ?? 0)}</span>
          <span class="card-item__due">${c.due_date}</span>
          <span class="card-item__status card-item__status--${c.status}">${c.status}</span>
          <div class="card-item__actions">
            <button type="button" class="btn btn--secondary btn--small" data-edit="${c.id}" aria-label="Editar">Editar</button>
            <button type="button" class="btn btn--danger btn--small" data-delete="${c.id}" aria-label="Excluir">Excluir</button>
          </div>
        </article>
      `;
      })
      .join("");

    list.querySelectorAll("[data-edit]").forEach((btn) => btn.addEventListener("click", () => openModal(Number(btn.dataset.edit))));
    list.querySelectorAll("[data-delete]").forEach((btn) => btn.addEventListener("click", () => deleteCard(Number(btn.dataset.delete))));
  } catch (e) {
    list.innerHTML = '<p class="error">Erro ao carregar: ' + escapeHtml(e.message) + "</p>";
  }
}

function openModal(cardId = null) {
  if (!state.user) {
    promptLogin();
    return;
  }
  const modal = $("modal-card");
  const form = $("form-card");
  $("modal-title").textContent = cardId ? "Editar despesa" : "Nova despesa";
  $("card-id").value = cardId ?? "";
  showError($("form-error"));
  if (cardId) {
    api("/cards/" + cardId)
      .then((c) => {
        $("card-title").value = c.title ?? "";
        $("card-urgency").value = c.urgency;
        $("card-type").value = c.expense_type;
        $("card-value").value = c.value;
        $("card-due").value = c.due_date;
        $("card-status").value = c.status;
      })
      .catch((e) => showError($("form-error"), e.message));
  } else {
    form.reset();
    $("card-title").value = "";
    $("card-status").value = "pendente";
  }
  modal.showModal();
}

function closeModal() {
  $("modal-card").close();
}

async function submitCard(event) {
  event.preventDefault();
  if (!state.user) {
    promptLogin();
    return;
  }
  const id = $("card-id").value;
  const payload = {
    title: ($("card-title").value || "").trim(),
    urgency: parseInt($("card-urgency").value, 10),
    expense_type: $("card-type").value,
    value: parseFloat($("card-value").value.replace(",", ".")),
    due_date: $("card-due").value,
    status: $("card-status").value,
  };
  if (!Number.isFinite(payload.value) || payload.value <= 0) {
    showError($("form-error"), "Informe um valor maior que zero.");
    return;
  }
  showError($("form-error"));
  try {
    if (id) {
      await api(`/cards/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    } else {
      await api("/cards", { method: "POST", body: JSON.stringify(payload) });
    }
    closeModal();
    await loadSummary();
    await loadCards();
  } catch (err) {
    showError($("form-error"), err.message);
  }
}

async function deleteCard(id) {
  if (!state.user) {
    promptLogin();
    return;
  }
  if (!confirm("Excluir esta despesa?")) return;
  await api(`/cards/${id}`, { method: "DELETE" });
  await loadSummary();
  await loadCards();
}

function onFilterChange() {
  if (!state.user) return;
  loadCards();
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const username = elements.loginUsername.value.trim();
  const password = elements.loginPassword.value;
  if (!username || !password) {
    showAuthError("Informe usuário e senha.");
    return;
  }
  try {
    const user = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
      skipAuthOn401: true,
    });
    setCurrentUser(user);
    hideAuthOverlay();
    await loadBalance();
    await loadSummary();
    await loadCards();
  } catch (err) {
    showAuthError(err.message || "Não foi possível fazer login.");
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const username = elements.registerUsername.value.trim();
  const password = elements.registerPassword.value;
  if (!username || !password) {
    showAuthError("Informe usuário e senha.");
    return;
  }
  try {
    const user = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
      skipAuthOn401: true,
    });
    setCurrentUser(user);
    hideAuthOverlay();
    await loadBalance();
    await loadSummary();
    await loadCards();
  } catch (err) {
    showAuthError(err.message || "Não foi possível cadastrar.");
  }
}

async function handleLogout() {
  try {
    await api("/auth/logout", { method: "POST", skipAuthOn401: true });
  } catch (err) {
    console.warn("Erro ao fazer logout:", err);
  }
  promptLogin();
}

$("balance-save").addEventListener("click", saveBalance);
$("btn-add-card").addEventListener("click", () => openModal());
$("form-card").addEventListener("submit", submitCard);
$("modal-cancel").addEventListener("click", closeModal);
$("filter-status").addEventListener("change", onFilterChange);
$("filter-type").addEventListener("change", onFilterChange);

elements.authTabLogin.addEventListener("click", () => switchAuthMode("login"));
elements.authTabRegister.addEventListener("click", () => switchAuthMode("register"));
elements.loginForm.addEventListener("submit", handleLoginSubmit);
elements.registerForm.addEventListener("submit", handleRegisterSubmit);
elements.logoutBtn.addEventListener("click", handleLogout);

$("modal-card").addEventListener("click", (event) => {
  if (event.target === $("modal-card")) closeModal();
});

$("modal-card").addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModal();
});

async function init() {
  resetAppState();
  const user = await fetchCurrentUser();
  if (!user) return;
  try {
    await loadBalance();
    await loadSummary();
    await loadCards();
  } catch (error) {
    elements.cardsList.innerHTML =
      '<p class="error">Erro ao conectar na API. Verifique se o servidor está rodando (uvicorn app.main:app --reload).</p>';
    elements.zoneBadge.textContent = "Erro";
    elements.zoneBadge.className = "zone zone--vermelho";
  }
}

init();
