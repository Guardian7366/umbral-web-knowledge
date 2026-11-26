function maintainTools(root, state, data, submitAction, accepted, prior) {
  const workspace = root.querySelector(".tool-workspace");
  if (!workspace) return null;
  const form = workspace.querySelector(".tool-form");
  const notice = form.querySelector("#tool-notice");
  const waiting = form.querySelector(".tool-wait");
  const send = form.querySelector(".tool-submit");
  const dirty = workspace.querySelector(".tool-dirty");
  const index = workspace.querySelector(".tool-index");
  const reader = workspace.querySelector(".archive-reader");
  const position = scrollParent(workspace);
  const settings = form.querySelector(".tool-settings");
  const recommendation = Boolean(settings);
  const {defaults, sources} = data.tools;
  const limits = recommendation && {...defaults.limits};
  const thresholds = recommendation && {...defaults.thresholds};
  const connector = workspace.querySelector(".tool-connection path");
  let observer;
  let previousMode;
  let previousMethod;
  const scope = new AbortController();
  const options = {signal:scope.signal};
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  let effect;

  const draft = () => {
    const {query, limit, threshold, mode, method, source} = form.elements;
    if (!recommendation) return {query:query.value, limit:Number(limit.value)};
    return {
      query:query.value, source:source.value, mode:mode.value, method:method.value,
      limits:{...limits, [mode.value]:Number(limit.value)},
      thresholds:{...thresholds, [method.value]:Number(threshold.value)},
    };
  };
  const enter = (kind, id) => submitAction({kind, documentId:id, toolDraft:draft()});
  const animate = (node, from, duration, easing = "cubic-bezier(.2,.8,.2,1)") => {
    effect?.cancel();
    if (node && !motion.matches) {
      effect = node.animate([{transform:from}, {transform:"none"}], {duration,easing});
    }
  };

  function drawConnection() {
    const source = form.querySelector(".tool-source-card:not([hidden]), .tool-context-query:not([hidden])");
    const row = index?.querySelector(".tool-row.is-active");
    if (!connector || !source || !row || index.hidden || reader) {
      connector?.removeAttribute("d");
      return;
    }
    const bounds = form.getBoundingClientRect();
    const origin = source.getBoundingClientRect();
    const destination = row.getBoundingClientRect();
    const x = origin.right - bounds.left;
    const end = destination.left - bounds.left;
    if (end <= x) return connector.removeAttribute("d");
    const toY = destination.top - bounds.top + 46;
    const fromY = Math.min(origin.bottom - bounds.top - 18, Math.max(origin.top - bounds.top + 32, toY + 25));
    const gap = end - x;
    connector.setAttribute("d", `M${x},${fromY} H${x+gap*.34} L${end-gap*.27},${toY} H${end}`);
  }

  function updateRecommendation() {
    const {mode,method,source,limit,threshold} = form.elements;
    if (previousMode && mode.value !== previousMode) {
      limits[previousMode] = Number(limit.value);
      const count = Object.keys(sources).length - (mode.value === "document" ? 1 : 0);
      limit.replaceChildren(...Array.from({length:count}, (_,n) => new Option(n+1,n+1)));
      limit.value = limits[mode.value];
    }
    if (previousMethod && method.value !== previousMethod) {
      thresholds[previousMethod] = Number(threshold.value);
      threshold.value = thresholds[method.value].toFixed(2);
    }
    const semantic = method.value === "semantic";
    form.querySelector(".tool-method-help").textContent = semantic
      ? "Related ideas compares meanings in context. Its first use may need to download the model."
      : "Shared words finds documents with overlapping weighted terms.";
    form.querySelector(".tool-threshold-help").textContent = semantic
      ? "The initial threshold of 0.55 comes from preliminary validation."
      : "Raise the threshold to exclude weaker word matches.";
    const card = form.querySelector(".tool-source-card");
    card.hidden = mode.value !== "document";
    form.querySelector(".tool-context-query").hidden = mode.value !== "query";
    card.querySelector(".tool-source-id").textContent = source.value;
    card.querySelector("h2").textContent = sources[source.value].title;
    card.querySelector(".tool-source-category").textContent = sources[source.value].category;
    form.dataset.mode = mode.value;
    previousMode = mode.value;
    previousMethod = method.value;
  }

  function update(edit = false) {
    if (recommendation) updateRecommendation();
    const value = draft();
    const criteria = recommendation ? {
      ...value, limit:value.limits[value.mode], threshold:value.thresholds[value.method],
    } : value;
    criteria.query = criteria.query.trim();
    const confirmed = data.tools.confirmed;
    const differs = confirmed && Object.keys(confirmed).some(key => criteria[key] !== confirmed[key]);
    if (index) index.hidden = Boolean(differs);
    if (reader) reader.hidden = Boolean(differs);
    workspace.classList.toggle("is-reading", Boolean(reader && !differs));
    dirty.hidden = !differs;
    if (edit) {
      notice.hidden = true;
      form.elements.query.removeAttribute("aria-invalid");
      effect?.cancel();
    }
    if (recommendation) drawConnection();
  }

  workspace.addEventListener("click", event => {
    const trigger = event.target.closest("[data-tool-action]");
    if (trigger && !state.pending) {
      if (trigger.dataset.toolAction === "tool_open" && !reader) {
        state.toolReturnScroll = {top:position.scrollTop, index:index.scrollTop};
      }
      enter(trigger.dataset.toolAction, trigger.dataset.id);
    }
  }, options);
  form.addEventListener("input", () => update(true), options);
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (state.pending) return;
    send.disabled = true;
    notice.hidden = true;
    const criteria = draft();
    waiting.hidden = criteria.mode !== "document" && !criteria.query.trim();
    const controls = [...form.querySelectorAll("input,textarea,select")];
    for (const control of controls) control.disabled = true;
    if (index) index.hidden = true;
    if (reader) reader.hidden = true;
    workspace.classList.remove("is-reading");
    submitAction({kind:"tool_submit", toolDraft:criteria}, () => {
      for (const control of controls) control.disabled = false;
      waiting.hidden = true;
      send.disabled = false;
      notice.textContent = "The request could not be completed. Try again.";
      notice.hidden = false;
      update();
    });
  }, options);
  form.elements.query.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      form.requestSubmit();
    }
  }, options);
  motion.addEventListener("change", () => effect?.cancel(), options);
  if (prior && prior.page === data.page) {
    if (settings) settings.open = prior.settings;
    const detail = [...workspace.querySelectorAll("details")].find(item => item.id === prior.detail);
    if (detail) detail.open = true;
    if (index) index.scrollTop = prior.indexScroll;
  }
  update();
  if (connector) {
    observer = new ResizeObserver(drawConnection);
    observer.observe(form);
    observer.observe(form.querySelector(".tool-source"));
    if (index) observer.observe(index);
  }
  if (accepted?.kind === "tool_submit") {
    state.toolReturnScroll = null;
    if (notice.dataset.status === "empty") {
      form.elements.query.setAttribute("aria-invalid","true");
      focus(form.elements.query);
    } else if (notice.dataset.status === "error") {
      focus(notice.querySelector("[name=retry]"));
    } else if (index) {
      focus(index.querySelector("h2"), true);
      if (!recommendation && data.tools.count) animate(index.querySelector(".tool-ranking"), "translateX(6px)", 160);
    }
  } else if (accepted?.kind === "tool_inspect") {
    focus(workspace.querySelector(`.tool-record[data-id="${accepted.documentId}"]`));
    if (connector?.hasAttribute("d") && !motion.matches) {
      effect = connector.animate([{strokeDashoffset:1},{strokeDashoffset:0}], {
        duration:180, easing:"cubic-bezier(.2,.8,.2,1)",
      });
    }
  } else if (accepted?.kind === "tool_open" || accepted?.kind === "tool_retry_file") {
    focus(reader?.querySelector("h2"), true);
    if (accepted.kind === "tool_open") animate(reader, "translateX(8px)", 180);
  } else if (accepted?.kind === "tool_back") {
    const saved = state.toolReturnScroll;
    if (saved && index) {
      position.scrollTop = saved.top;
      index.scrollTop = saved.index;
    }
    focus(workspace.querySelector(recommendation
      ? `[data-tool-action="tool_open"][data-id="${data.tools.selected}"]`
      : `.tool-record[data-id="${data.tools.selected}"]`));
    animate(index?.querySelector(".tool-ranking"), "translateX(-6px)", 140, "cubic-bezier(.4,0,1,1)");
    state.toolReturnScroll = null;
  }
  return {
    draft,
    snapshot:() => ({
      page:data.page, detail:workspace.querySelector(".tool-match[open]")?.id,
      settings:settings?.open || false, indexScroll:index?.scrollTop || 0,
    }),
    stop() { observer?.disconnect(); effect?.cancel(); scope.abort(); },
  };
}
