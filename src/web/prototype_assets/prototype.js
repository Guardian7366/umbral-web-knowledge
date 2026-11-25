const instances = new WeakMap();
const compact = matchMedia("(max-width: 959px)");

function focus(target, scroll = false) {
  if (!target) return;
  target.focus({ preventScroll: true });
  if (scroll) target.scrollIntoView({ block: "nearest", behavior: "instant" });
}

function keepTabInDialog(event) {
  const dialog = event.currentTarget;
  if (event.key !== "Tab") return;
  const controls = Array.from(dialog.querySelectorAll("button:not(:disabled)"));
  const from = event.shiftKey ? controls.at(0) : controls.at(-1);
  const to = event.shiftKey ? controls.at(-1) : controls.at(0);
  if (dialog.getRootNode().activeElement === from) {
    event.preventDefault();
    focus(to);
  }
}

function scrollParent(node) {
  for (let parent = node; parent; parent = parent.parentElement || parent.getRootNode().host) {
    if (/(auto|scroll)/.test(getComputedStyle(parent).overflowY) && parent.scrollHeight > parent.clientHeight) {
      return parent;
    }
  }
  return document.scrollingElement;
}

function jumpToTurn(turns, heading) {
  if (!turns || !heading) return;
  const offset = heading.getBoundingClientRect().top - turns.getBoundingClientRect().top;
  turns.scrollTop += offset - 22;
}

function fitComposer(field, send, busy) {
  if (field.tagName === "TEXTAREA") {
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, 170)}px`;
    send.disabled = busy || !field.value.trim();
  } else {
    send.disabled = busy;
  }
}

function downloadLink(link, doc) {
  link.hidden = !doc?.bytes;
  if (doc?.bytes) {
    link.href = `data:text/plain;base64,${doc.bytes}`;
    link.download = doc.file;
  } else {
    link.removeAttribute("href");
  }
}

function renderReader(root, state, data, moveFocus = true) {
  const panel = root.querySelector(".reader");
  if (!panel) return;
  const selection = state.reader;
  panel.hidden = !selection;
  root.querySelectorAll("[data-source]").forEach(button => {
    button.setAttribute("aria-expanded", String(selection?.trigger === button.id));
  });
  if (!selection) return;

  const doc = data.documents[selection.id];
  const source = data.evidence[selection.key];
  const original = selection.mode === "original";
  const title = panel.querySelector("h2");
  const passage = (source?.fragments || []).join(" ");
  panel.classList.toggle("original-mode", original);
  panel.querySelector(".reader-back span").textContent =
    selection.key ? (original ? "Back to source" : "Back to answer") : "Back to overview";
  panel.querySelector(".reader-kicker").hidden = original;
  panel.querySelector(".reader-id").textContent = selection.id;
  title.textContent = doc?.title || source?.title || selection.id;
  panel.querySelector(".reader-category").textContent = doc?.category || source?.category || "";
  panel.querySelector(".reader-type").textContent = doc?.type || "";
  panel.querySelector(".reader-unavailable").hidden = Boolean(doc?.bytes);
  panel.querySelector(".reader-original-label").hidden = !original;

  const documentText = panel.querySelector(".reader-original");
  documentText.textContent = original ? doc?.original || "" : "";
  documentText.hidden = !original;
  panel.querySelector("[data-original]").hidden = original || !doc?.bytes;
  downloadLink(panel.querySelector("[data-download]"), doc);

  const evidence = panel.querySelector(".evidence");
  evidence.hidden = original || !source;
  evidence.open = Boolean(selection.evidenceOpen);
  panel.querySelector(".similarity").textContent = source ? `Document similarity ${source.similarity}` : "";
  panel.querySelector(".sentences").textContent = source ? `Extracted sentences ${source.fragments.length}` : "";
  panel.querySelector(".fragments").textContent = passage;
  const preview = panel.querySelector(".reader-preview");
  preview.hidden = original || !passage;
  preview.querySelector("p").textContent = (source?.fragments || []).slice(0, 3).join(" ");
  evidence.ontoggle = () => {
    if (state.reader === selection && !original) selection.evidenceOpen = evidence.open;
  };
  if (moveFocus) {
    panel.scrollTop = original ? 0 : (selection.panelScroll || 0);
    if (selection.returnFromOriginal) {
      selection.returnFromOriginal = false;
      focus(panel.querySelector("[data-original]"));
    } else {
      focus(title);
    }
  }
}

function showFeature(root, state, expanded, restore = false) {
  const control = root.querySelector("[data-feature]");
  if (!control) return;
  state.feature = expanded;
  control.setAttribute("aria-expanded", String(expanded));
  root.querySelector("#feature-details").hidden = !expanded;
  root.querySelector(".overview-flow").classList.toggle("featured-open", expanded);
  if (restore) focus(control, true);
}

function openReader(root, state, data, trigger, sourceId) {
  const workspace = root.querySelector(".turns");
  const container = workspace || scrollParent(trigger);
  const turn = trigger.dataset.sourceTurn;
  state.reader = {
    id: sourceId, key: turn !== undefined ? `${turn}-${sourceId}` : undefined,
    trigger: trigger.id || "feature-original", mode: turn !== undefined ? "source" : "original",
    readingScroll: container.scrollTop,
  };
  renderReader(root, state, data);
}

function backFromReader(root, state, data) {
  const selection = state.reader;
  if (!selection) return;
  if (selection.key && selection.mode === "original") {
    selection.mode = "source";
    selection.returnFromOriginal = true;
    renderReader(root, state, data);
    return;
  }
  state.reader = null;
  renderReader(root, state, data);
  const trigger = root.querySelector(`#${CSS.escape(selection.trigger)}`);
  if (trigger) {
    const container = root.querySelector(".turns") || scrollParent(trigger);
    container.scrollTop = selection.readingScroll;
    focus(trigger);
  }
}

function syncViewport(root) {
  const viewport = window.visualViewport;
  if (!viewport) return () => {};
  const update = () => root.style.setProperty("--visible-height", `${Math.round(viewport.height)}px`);
  viewport.addEventListener("resize", update);
  update();
  return () => viewport.removeEventListener("resize", update);
}

function readyFocus(root, state, data, previousPage, action, oldScroll) {
  const field = root.querySelector("#question");
  const turns = root.querySelector(".turns");
  if (previousPage && previousPage !== data.page) scrollParent(root.querySelector(".page")).scrollTop = 0;
  if (turns) {
    turns.scrollTop = previousPage === data.page ? oldScroll : (state.scroll[data.page] || 0);
  }
  if (action?.kind === "submit" || action?.kind === "retry") {
    if (data.turns > 0 && (action.followLatest || previousPage === "Overview" || action.kind === "retry")) {
      const index = action.kind === "retry" ? action.turn : data.turns - 1;
      const heading = root.querySelector(`#turn-${index}`);
      jumpToTurn(turns, heading);
      const error = root.querySelector(`#turn-error-${index}`);
      if (error && field) {
        field.setAttribute("aria-describedby", error.id);
        field.setAttribute("aria-invalid", "true");
        if (!field.value) field.value = action.text || heading?.textContent || "";
        fitComposer(field, field.form.querySelector('[type="submit"]'), false);
      }
    }
    if (previousPage === "Overview" && action.text.trim()) focus(root.querySelector("#page-title"));
    if (data.page === "Assistant" && !state.reader) focus(field);
  } else if (action?.kind === "clear") {
    focus(field);
  } else if (action?.kind === "navigate") {
    const title = root.querySelector("#page-title");
    if (title) focus(title);
    else requestAnimationFrame(() => {
      const target = document.querySelector(".st-key-umbral-native h1");
      target?.setAttribute("tabindex", "-1");
      focus(target, true);
    });
  }
}

export default function render({ parentElement, data, setTriggerValue }) {
  const root = parentElement.querySelector("#umbral-root");
  if (!root || !data) return;
  let state = instances.get(root);
  if (!state) {
    state = { drafts: {}, scroll: {}, feature: false, reader: null, cleanup: syncViewport(root) };
    instances.set(root, state);
  }
  if (state.revision === data.revision && state.markup === data.markup) {
    return () => unmount(root, state);
  }

  const previousPage = state.page;
  const lastAction = state.pending;
  const accepted = lastAction && state.revision !== data.revision;
  const oldScroll = root.querySelector(".turns")?.scrollTop || 0;
  const oldField = root.querySelector("#question");
  if (oldField) state.drafts[previousPage] = oldField.value;
  state.scroll[previousPage] = oldScroll;
  if (previousPage !== data.page || lastAction?.kind === "clear") state.reader = null;
  if (accepted && lastAction.kind === "submit") {
    const saved = state.drafts[previousPage];
    if (saved?.trim() === lastAction.text.trim()) state.drafts[previousPage] = "";
  } else if (accepted && lastAction.kind === "retry") {
    const stillFailed = data.markup.includes(`id="turn-error-${lastAction.turn}"`);
    if (!stillFailed && state.drafts.Assistant?.trim() === lastAction.text) state.drafts.Assistant = "";
  } else if (accepted && lastAction.kind === "clear") {
    state.drafts.Assistant = "";
    state.scroll.Assistant = 0;
  }

  clearTimeout(state.timer);
  state.pending = null;
  state.page = data.page;
  state.revision = data.revision;
  state.markup = data.markup;
  root.innerHTML = data.markup;

  const field = root.querySelector("#question");
  const send = root.querySelector('[type="submit"]');
  const announcements = root.querySelector(".announcements");
  const rail = root.querySelector(".rail");
  const drawer = root.querySelector(".drawer");
  const confirm = root.querySelector(".confirm-dialog");
  const menu = root.querySelector("[data-menu]");
  const transportError = root.querySelector(".transport-error");
  const turns = root.querySelector(".turns");

  function submitAction(action) {
    if (state.pending) return;
    action.followLatest = !turns || turns.scrollHeight - turns.clientHeight - turns.scrollTop < 72;
    state.pending = action;
    if (field) fitComposer(field, send, true);
    const expectingAnswer = action.kind === "retry" || (action.kind === "submit" && action.text.trim());
    let waiting;
    if (expectingAnswer) {
      waiting = document.createElement("p");
      waiting.className = "notice processing";
      waiting.setAttribute("role", "status");
      waiting.textContent = "Finding passages…";
      (field?.form || root.querySelector(".page")).prepend(waiting);
    }
    if (transportError) transportError.hidden = true;
    state.timer = setTimeout(() => {
      state.pending = null;
      waiting?.remove();
      if (expectingAnswer && transportError) {
        transportError.hidden = false;
        field.setAttribute("aria-describedby", transportError.id);
        focus(field);
      } else {
        announcements.textContent = "The action could not be completed. Try again.";
      }
      if (field) fitComposer(field, send, false);
    }, 15000);
    setTriggerValue("action", { ...action, revision: data.revision });
  }

  if (field) {
    field.value = state.drafts[data.page] || "";
    fitComposer(field, send, false);
    field.form.onsubmit = event => {
      event.preventDefault();
      if (data.page === "Overview" || field.value.trim()) submitAction({ kind: "submit", text: field.value });
    };
    field.oninput = () => {
      field.removeAttribute("aria-invalid");
      field.removeAttribute("aria-describedby");
      if (transportError) transportError.hidden = true;
      fitComposer(field, send, Boolean(state.pending));
    };
    let composing = false;
    field.oncompositionstart = () => { composing = true; };
    field.oncompositionend = () => { composing = false; };
    field.onkeydown = event => {
      if (event.key !== "Enter" || event.shiftKey || event.isComposing || composing || event.keyCode === 229) return;
      if (data.page === "Assistant" && (matchMedia("(pointer: coarse)").matches || compact.matches)) return;
      event.preventDefault();
      if (!send.disabled) field.form.requestSubmit();
    };
  }

  function closeMenu(restore) {
    drawer.close();
    menu.setAttribute("aria-expanded", "false");
    if (restore) focus(menu);
  }

  function openMenu() {
    drawer.showModal();
    menu.setAttribute("aria-expanded", "true");
    focus(drawer.querySelector("[aria-current]"));
  }

  function closeConfirm() {
    confirm.close();
    if (compact.matches) {
      openMenu();
      focus(drawer.querySelector("[data-confirm]"));
    } else {
      focus(rail.querySelector("[data-confirm]"));
    }
  }

  menu.setAttribute("aria-expanded", "false");
  drawer.oncancel = event => { event.preventDefault(); closeMenu(true); };
  confirm.oncancel = event => { event.preventDefault(); closeConfirm(); };
  drawer.onkeydown = keepTabInDialog;
  confirm.onkeydown = keepTabInDialog;
  const closeResize = () => { if (!compact.matches && drawer.open) closeMenu(false); };
  compact.addEventListener("change", closeResize);
  state.closeResize?.();
  state.closeResize = () => compact.removeEventListener("change", closeResize);
  root.onclick = event => {
    const target = event.target.closest("button");
    if (event.target === drawer) {
      const rect = drawer.getBoundingClientRect();
      if (event.clientX > rect.right || event.clientX < rect.left) closeMenu(true);
    }
    if (!target || target.disabled) return;
    const command = target.dataset;

    if ("menu" in command) openMenu();
    else if ("closeMenu" in command) closeMenu(true);
    else if ("route" in command) {
      if (drawer.open) closeMenu(false);
      if (command.route === data.page) focus(root.querySelector("#page-title"));
      else submitAction({ kind: "navigate", page: command.route });
    } else if ("skip" in command) {
      const main = root.querySelector("#page-title") || document.querySelector(".st-key-umbral-native h1");
      main?.setAttribute("tabindex", "-1");
      focus(main, true);
    } else if ("confirm" in command) {
      if (state.pending) return;
      if (drawer.open) closeMenu(false);
      confirm.showModal();
      focus(confirm.querySelector("[data-cancel]"));
    } else if ("cancel" in command) closeConfirm();
    else if ("clear" in command) {
      confirm.close();
      submitAction({ kind: "clear" });
    } else if ("feature" in command) showFeature(root, state, !state.feature);
    else if ("hideFeature" in command) showFeature(root, state, false, true);
    else if ("featureOriginal" in command) openReader(root, state, data, target, "UW04");
    else if ("source" in command) {
      if (state.reader?.trigger === target.id) backFromReader(root, state, data);
      else openReader(root, state, data, target, command.source);
    } else if ("original" in command && state.reader) {
      state.reader.panelScroll = root.querySelector(".reader").scrollTop;
      state.reader.mode = "original";
      renderReader(root, state, data);
    } else if ("readerBack" in command) backFromReader(root, state, data);
    else if ("suggest" in command) submitAction({ kind: "submit", text: data.suggestions[Number(command.suggest)] });
    else if ("retry" in command) submitAction({
      kind: "retry", turn: Number(command.retry), text: root.querySelector(`#turn-${command.retry}`).textContent,
    });
    else if ("rephrase" in command) focus(field);
    else if ("turnLink" in command || "latest" in command) {
      root.querySelector(".previous").open = false;
      const index = "latest" in command ? data.turns - 1 : Number(command.turnLink);
      const heading = root.querySelector(`#turn-${index}`);
      jumpToTurn(turns, heading);
      focus(heading);
    }
  };
  root.onkeydown = event => {
    if (event.key === "Escape" && !drawer.open && !confirm.open && state.reader) {
      event.preventDefault();
      backFromReader(root, state, data);
    }
  };

  showFeature(root, state, state.feature);
  renderReader(root, state, data, false);
  readyFocus(root, state, data, previousPage, accepted ? lastAction : null, oldScroll);
  if (accepted) announcements.textContent = lastAction.kind === "submit" && data.turns ? "Conversation updated." : `${data.page}.`;
  return () => unmount(root, state);
}

function unmount(root, state) {
  clearTimeout(state.timer);
  state.closeResize?.();
  state.cleanup();
  instances.delete(root);
}
