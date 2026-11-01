"use strict";

const select = (selector, scope = document) => scope.querySelector(selector);
const statusLabels = {active: "Ativo", discontinued: "Descontinuado", coming_soon: "Em breve"};
const state = {databaseReady: false, policiesReady: false, catalogRequest: null, policyRequest: null, detailRequest: null};

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatMoney(value) {
  const [whole, fraction = "00"] = String(value).split(".");
  return `R$ ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${fraction.padEnd(2, "0")}`;
}

function friendlyError(error, fallback) {
  const messages = {
    database_missing: "O catálogo ainda não foi carregado. Use o botão Carregar dados para começar.",
    not_found: "Não encontramos esse item. Atualize a consulta e tente novamente.",
    invalid_request: "Confira os campos da busca e tente novamente.",
    source_error: "Não foi possível ler os dados da loja. Confira se os arquivos fornecidos estão nas pastas configuradas.",
    internal_error: "Não foi possível concluir a consulta. Tente novamente.",
  };
  return messages[error.code] || fallback;
}

async function request(path, options = {}) {
  const response = await fetch(path, {cache: "no-store", ...options});
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "Request failed");
    error.code = payload.code;
    throw error;
  }
  return payload;
}

function showNotice(message, isError = false) {
  const notice = select("#global-message");
  notice.textContent = message;
  notice.classList.toggle("is-error", isError);
  notice.hidden = !message;
}

function showState(target, title, message, options = {}) {
  const panel = select(target);
  panel.replaceChildren();
  panel.classList.toggle("is-error", Boolean(options.error));
  panel.append(createElement("span", "state-symbol", options.error ? "!" : "↗"));
  panel.firstChild.setAttribute("aria-hidden", "true");
  panel.append(createElement("h3", "", title), createElement("p", "", message));
  if (options.load) {
    const button = createElement("button", "button button-primary", "Carregar dados →");
    button.type = "button";
    button.addEventListener("click", importData);
    panel.append(button);
  }
  panel.hidden = false;
}

async function refreshStatus() {
  const status = await request("/api/status");
  state.databaseReady = status.database_ready;
  state.policiesReady = status.policies_ready;
  select("#product-count").textContent = status.product_count ?? "—";
  select("#available-count").textContent = status.available_count ?? "—";
  select("#promotion-count").textContent = status.active_promotion_count ?? "—";
  select("#import-button").textContent = state.databaseReady ? "Atualizar dados ↻" : "Carregar dados ↻";
  return status;
}

function addBadges(target, product) {
  const stock = product.available ? `${product.stock_quantity} em estoque` : statusLabels[product.status] === "Ativo" ? "Sem estoque" : statusLabels[product.status] || "Indisponível";
  target.append(createElement("span", `badge${product.available ? "" : " badge-unavailable"}`, stock));
  if (product.available && product.active_promotions.length === 1 && !product.promotion_note) {
    target.append(createElement("span", "badge badge-promotion", `−${product.active_promotions[0].discount_percent}%`));
  }
}

function addPrice(target, product) {
  if (product.effective_price_brl !== product.price_brl) {
    target.append(createElement("span", "price-original", formatMoney(product.price_brl)));
  } else {
    target.append(createElement("span", "price-label", "Preço de tabela"));
  }
  target.append(createElement("span", "price-current", formatMoney(product.effective_price_brl)));
}

function renderProducts(products) {
  const grid = select("#product-grid");
  grid.replaceChildren();
  products.forEach((product) => {
    const fragment = select("#product-template").content.cloneNode(true);
    select(".card-category", fragment).textContent = product.category_name;
    select(".card-id", fragment).textContent = `#${product.product_id}`;
    select(".card-name", fragment).textContent = product.name;
    addBadges(select(".badge-row", fragment), product);
    addPrice(select(".card-price", fragment), product);
    const details = select(".card-detail-button", fragment);
    details.setAttribute("aria-label", `Ver detalhes de ${product.name}`);
    details.addEventListener("click", () => openProduct(product.product_id));
    grid.append(fragment);
  });
  select("#catalog-result-count").textContent = `${products.length} ${products.length === 1 ? "instrumento encontrado" : "instrumentos encontrados"}${products.length === 100 ? " (limite de 100)" : ""}`;
  select("#catalog-message").hidden = products.length > 0;
  if (!products.length) showState("#catalog-message", "Seu som pode estar em outra busca.", "Nenhum instrumento corresponde aos filtros. Tente outra marca ou ajuste o preço e a disponibilidade.");
}

async function searchProducts(event) {
  if (event) event.preventDefault();
  if (!state.databaseReady) {
    select("#product-grid").replaceChildren();
    select("#catalog-result-count").textContent = "Catálogo não carregado";
    showState("#catalog-message", "Vamos preparar o catálogo?", "Carregue os arquivos da loja para consultar instrumentos, preços e disponibilidade.", {load: true});
    return;
  }
  const rawPrice = select("#max-price").value.trim();
  if (rawPrice && !/^\d+(?:[,.]\d{1,2})?$/.test(rawPrice)) {
    select("#max-price").setCustomValidity("Informe um valor como 1000,00, sem separador de milhar.");
    select("#max-price").reportValidity();
    return;
  }
  select("#max-price").setCustomValidity("");
  if (state.catalogRequest) state.catalogRequest.abort();
  const controller = new AbortController();
  state.catalogRequest = controller;
  const parameters = new URLSearchParams({name: select("#product-name").value.trim(), availability: select("#availability").value, limit: "100"});
  if (rawPrice) parameters.set("max_price", rawPrice.replace(",", "."));
  select("#product-grid").setAttribute("aria-busy", "true");
  select("#catalog-result-count").textContent = "Consultando catálogo…";
  select("#search-button").disabled = true;
  select("#product-grid").replaceChildren();
  showState("#catalog-message", "Afinando a busca…", "Consultando os instrumentos nos dados da loja.");
  try {
    const payload = await request(`/api/products?${parameters}`, {signal: controller.signal});
    renderProducts(payload.products);
  } catch (error) {
    if (error.name === "AbortError") return;
    select("#catalog-result-count").textContent = "Consulta não concluída";
    showState("#catalog-message", "Não conseguimos abrir o catálogo.", friendlyError(error, "Confira se o servidor local está em execução e tente novamente."), {error: true, load: error.code === "database_missing"});
  } finally {
    if (state.catalogRequest === controller) {
      select("#product-grid").setAttribute("aria-busy", "false");
      select("#search-button").disabled = false;
    }
  }
}

function addFact(target, label, value) {
  const group = createElement("div");
  group.append(createElement("dt", "", label), createElement("dd", "", value));
  target.append(group);
}

async function openProduct(productId) {
  if (state.detailRequest) state.detailRequest.abort();
  const controller = new AbortController();
  state.detailRequest = controller;
  const dialog = select("#product-dialog");
  select("#detail-name").textContent = "Detalhes do instrumento";
  select("#detail-content").hidden = true;
  showState("#detail-message", "Abrindo o instrumento…", "Consultando as informações do catálogo.");
  dialog.showModal();
  try {
    const {product} = await request(`/api/products/${encodeURIComponent(productId)}`, {signal: controller.signal});
    select("#detail-category").textContent = `${product.category_name} · #${product.product_id}`;
    select("#detail-name").textContent = product.name;
    select("#detail-badges").replaceChildren();
    addBadges(select("#detail-badges"), product);
    select("#detail-price").replaceChildren();
    addPrice(select("#detail-price"), product);
    select("#detail-description").textContent = product.description || "Descrição não informada nos dados.";
    const facts = select("#detail-facts");
    facts.replaceChildren();
    addFact(facts, "Status no catálogo", statusLabels[product.status] || product.status);
    addFact(facts, "Quantidade informada", `${product.stock_quantity} unidades`);
    addFact(facts, "Disponível para venda", product.available ? "Sim" : "Não");
    addFact(facts, "Cadastrado em", product.created_at ? product.created_at.split("-").reverse().join("/") : "Não informado");
    const note = select("#detail-promotion-note");
    note.hidden = !product.promotion_note;
    note.textContent = product.active_promotions.length > 1 ? "Há mais de uma promoção ativa para este instrumento. O preço de tabela foi mantido; confirme a oferta válida com a equipe." : "Este instrumento está indisponível. O desconto promocional não foi aplicado ao preço.";
    const offers = select("#detail-promotion-list");
    offers.replaceChildren();
    product.active_promotions.forEach((offer) => offers.append(createElement("li", "", `${offer.discount_percent}% · ${offer.description || "Descrição não informada"}`)));
    select("#detail-promotions").hidden = !product.active_promotions.length;
    const specifications = Object.entries(product.specs || {});
    const specificationList = select("#detail-spec-list");
    specificationList.replaceChildren();
    specifications.forEach(([key, value]) => addFact(specificationList, key.replaceAll("_", " "), value === null ? "Não informado" : typeof value === "object" ? JSON.stringify(value) : String(value)));
    select("#detail-specs").hidden = !specifications.length;
    select("#detail-message").hidden = true;
    select("#detail-content").hidden = false;
  } catch (error) {
    if (error.name === "AbortError") return;
    showState("#detail-message", "Não conseguimos abrir os detalhes.", friendlyError(error, "Confira a conexão com o servidor local e tente novamente."), {error: true});
  }
}

async function searchPolicies(event) {
  if (event) event.preventDefault();
  const query = select("#policy-query").value.trim();
  if (!query) { select("#policy-query").focus(); return; }
  if (state.policyRequest) state.policyRequest.abort();
  const controller = new AbortController();
  state.policyRequest = controller;
  select("#policy-results").replaceChildren();
  select("#policy-results").setAttribute("aria-busy", "true");
  select("#policy-search-button").disabled = true;
  select("#policy-result-count").textContent = "Consultando o manual…";
  showState("#policy-message", "Buscando uma boa referência…", "Consultando as palavras no manual da loja.");
  try {
    const {matches} = await request(`/api/policies?${new URLSearchParams({q: query, limit: "5"})}`, {signal: controller.signal});
    select("#policy-result-count").textContent = `${matches.length} ${matches.length === 1 ? "página encontrada" : "páginas encontradas"}`;
    select("#policy-message").hidden = matches.length > 0;
    if (!matches.length) showState("#policy-message", "Não encontramos essas palavras.", "Tente um termo mais simples, como devolução, horário ou pagamento. A busca não interpreta perguntas completas.");
    matches.forEach((match) => {
      const card = createElement("article", "policy-card");
      const heading = createElement("div", "policy-card-heading");
      heading.append(createElement("span", "page-badge", `Página ${match.page}`), createElement("span", "policy-source", match.source));
      card.append(heading, createElement("p", "policy-excerpt", match.text), createElement("p", "policy-card-footer", "Trecho original do manual · Referência à página física do PDF"));
      select("#policy-results").append(card);
    });
  } catch (error) {
    if (error.name === "AbortError") return;
    select("#policy-result-count").textContent = "Consulta não concluída";
    showState("#policy-message", "Não conseguimos consultar o manual.", friendlyError(error, "Confira se o PDF de políticas está na pasta configurada e tente novamente."), {error: true});
  } finally {
    if (state.policyRequest === controller) {
      select("#policy-results").setAttribute("aria-busy", "false");
      select("#policy-search-button").disabled = false;
    }
  }
}

async function importData() {
  const button = select("#import-button");
  if (button.disabled) return;
  button.disabled = true;
  button.textContent = "Carregando dados…";
  showNotice("Validando os arquivos e atualizando o catálogo…");
  try {
    const payload = await request("/api/load", {method: "POST", headers: {"X-Emporio-Client": "browser"}});
    await refreshStatus();
    await searchProducts();
    const warningCount = payload.warnings?.length || 0;
    showNotice(`${payload.counts.products} instrumentos carregados. ${warningCount ? "Os dados têm limitações registradas: a disponibilidade considera o status e o estoque, e as promoções refletem os arquivos fornecidos." : "O catálogo está pronto para consulta."}`);
  } catch (error) {
    showNotice(friendlyError(error, "Não foi possível concluir a atualização. Confira os arquivos e a conexão com a aplicação local."), true);
  } finally {
    button.disabled = false;
    button.textContent = state.databaseReady ? "Atualizar dados ↻" : "Carregar dados ↻";
  }
}

function activateTab(tab, moveFocus = false) {
  document.querySelectorAll('[role="tab"]').forEach((item) => {
    const active = item === tab;
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    select(`#${item.getAttribute("aria-controls")}`).hidden = !active;
  });
  if (moveFocus) tab.focus();
}

select("#catalog-form").addEventListener("submit", searchProducts);
select("#policy-form").addEventListener("submit", searchPolicies);
select("#import-button").addEventListener("click", importData);
select("#clear-filters").addEventListener("click", () => { select("#catalog-form").reset(); select("#max-price").setCustomValidity(""); searchProducts(); });
select("#max-price").addEventListener("input", () => select("#max-price").setCustomValidity(""));
select("#close-dialog").addEventListener("click", () => select("#product-dialog").close());
select("#product-dialog").addEventListener("close", () => { if (state.detailRequest) state.detailRequest.abort(); });
select("#product-dialog").addEventListener("click", (event) => { if (event.target === event.currentTarget) { const bounds = event.currentTarget.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.currentTarget.close(); } });
document.querySelectorAll("[data-policy-query]").forEach((button) => button.addEventListener("click", () => { select("#policy-query").value = button.dataset.policyQuery; searchPolicies(); }));
const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateTab(tab));
  tab.addEventListener("keydown", (event) => {
    let nextIndex;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex !== undefined) { event.preventDefault(); activateTab(tabs[nextIndex], true); }
  });
});

refreshStatus().then(() => searchProducts()).catch((error) => {
  showNotice(friendlyError(error, "Não foi possível conectar ao servidor local. Confira se a aplicação está em execução e recarregue a página."), true);
  showState("#catalog-message", "A consulta ainda não está disponível.", "Confira a conexão com a aplicação local e recarregue a página.", {error: true});
});
