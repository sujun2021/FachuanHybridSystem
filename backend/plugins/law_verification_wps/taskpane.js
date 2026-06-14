"use strict";

Office.onReady(function (info) {
  console.log("Office.js ready, host:", info.host);
});

async function startScan() {
  var btnEl = document.getElementById("btn-scan");
  var loadingEl = document.getElementById("loading");
  var resultsEl = document.getElementById("results-section");
  var errorEl = document.getElementById("error-section");

  var backendUrl = document.getElementById("backend-url").value.replace(/\/+$/, "");
  var credentialId = parseInt(document.getElementById("credential-id").value, 10);

  if (!backendUrl) { showError("请填写后端地址"); return; }
  if (!credentialId) { showError("请填写凭证 ID"); return; }

  errorEl.classList.add("hidden");
  resultsEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");
  btnEl.disabled = true;

  try {
    var text = await getDocumentText();
    if (!text || text.trim().length === 0) throw new Error("文档内容为空");

    var result = await callVerificationApi(backendUrl, credentialId, text);
    renderResults(result);
    resultsEl.classList.remove("hidden");
  } catch (err) {
    showError(err.message || String(err));
  } finally {
    loadingEl.classList.add("hidden");
    btnEl.disabled = false;
  }
}

function getDocumentText() {
  return new Promise(function (resolve, reject) {
    Word.run(function (context) {
      var body = context.document.body;
      body.load("text");
      return context.sync().then(function () { resolve(body.text); });
    }).catch(function (err) {
      try {
        Office.context.document.getSelectedDataAsync(Office.CoercionType.Text, function (result) {
          if (result.status === Office.AsyncResultStatus.Succeeded) resolve(result.value);
          else reject(new Error("无法读取文档内容"));
        });
      } catch (e) {
        reject(new Error("无法读取文档内容。请确保在 WPS/Word 中打开此插件。"));
      }
    });
  });
}

async function callVerificationApi(backendUrl, credentialId, text) {
  var resp = await fetch(backendUrl + "/api/v1/legal-research/law-verification/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text, credential_id: credentialId }),
  });
  if (!resp.ok) throw new Error("API 请求失败: HTTP " + resp.status);
  var data = await resp.json();
  if (data.error) throw new Error(data.error);
  return data;
}

function renderResults(data) {
  var refs = data.references || [];
  var verified = 0, mismatch = 0, notFound = 0, deprecated = 0;
  refs.forEach(function (r) {
    if (r.status === "verified") verified++;
    else if (r.status === "mismatch") mismatch++;
    else if (r.status === "not_found") notFound++;
    else if (r.status === "deprecated") deprecated++;
  });

  document.getElementById("summary").innerHTML =
    '<div class="summary-item summary-total"><span class="count">' + refs.length + '</span>总计</div>' +
    '<div class="summary-item summary-pass"><span class="count">' + verified + '</span>通过</div>' +
    '<div class="summary-item summary-warn"><span class="count">' + mismatch + '</span>存疑</div>' +
    '<div class="summary-item summary-fail"><span class="count">' + (notFound + deprecated) + '</span>异常</div>';

  var html = "";
  refs.forEach(function (r) {
    var simText = r.similarity != null ? " · 相似度 " + Math.round(r.similarity * 100) + "%" : "";
    html += '<div class="result-card status-' + r.status + '" onclick="this.classList.toggle(\'expanded\')">';
    html += '<div class="result-header"><span class="result-title">《' + esc(r.law_name) + '》第' + r.article_num + '条</span>';
    html += '<span class="result-badge badge-' + r.status + '">' + getStatusLabel(r.status) + '</span></div>';
    html += '<div class="result-meta">' + esc(r.validity || "") + simText + '</div>';
    html += '<div class="result-detail">';
    if (r.article_text) html += '<div class="detail-block"><div class="detail-label">条文原文</div><div class="detail-text">' + esc(r.article_text) + '</div></div>';
    if (r.reference_text) html += '<div class="detail-block"><div class="detail-label">文档引用</div><div class="detail-text">' + esc(r.reference_text) + '</div></div>';
    if (r.weike_url) html += '<a class="btn-link" href="' + esc(r.weike_url) + '" target="_blank">📖 在威科先行中查看 →</a>';
    html += '</div></div>';
  });

  document.getElementById("results-list").innerHTML = html || '<p style="text-align:center;color:#999;">未发现法规引用</p>';
}

function showError(msg) {
  document.getElementById("error-message").textContent = msg;
  document.getElementById("error-section").classList.remove("hidden");
}

function getStatusLabel(s) {
  return { verified: "✅ 通过", mismatch: "⚠️ 存疑", not_found: "❌ 未找到", deprecated: "⛔ 已废止" }[s] || s;
}

function esc(t) { var d = document.createElement("div"); d.textContent = t; return d.innerHTML; }
