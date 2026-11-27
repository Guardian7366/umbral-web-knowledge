const ARCHIVE_QUERY_DELAY = 120;

function archiveOpening(archive, enabled, signal) {
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  if (!enabled || motion.matches) return () => {};

  const effects = [];
  const timing = { duration: 300, easing: "cubic-bezier(.2,.8,.2,1)", fill: "backwards" };
  archive.querySelectorAll("[data-opening-sheet]").forEach((element, index) => {
    effects.push(element.animate([
      { transform: "translate(-6px, 12px)" },
      { transform: "translate(0, 0)" },
    ], { ...timing, delay: index * 60 }));
  });
  archive.querySelectorAll("[data-opening-divider]").forEach((element, index) => {
    effects.push(element.animate([
      { transform: "translateY(6px)" },
      { transform: "translateY(0)" },
    ], { ...timing, delay: index * 60 }));
  });

  const stop = () => {
    effects.forEach(effect => effect.cancel());
    effects.length = 0;
  };
  archive.addEventListener("pointerdown", stop, { once: true, signal });
  archive.addEventListener("keydown", stop, { once: true, signal });
  motion.addEventListener("change", stop, { once: true, signal });
  return stop;
}

function archiveEdge(archive, kind) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return null;
  if (kind === "library_back") {
    const lip = archive.querySelector(".archive-lip");
    if (lip?.getClientRects().length) return lip.animate(
      [{ transform: "translateY(-6px)" }, { transform: "translateY(0)" }],
      { duration: 140, easing: "cubic-bezier(.4,0,1,1)" },
    );
  }
  if (["library_category", "library_query", "library_group"].includes(kind)) {
    const surface = archive.querySelector('[aria-expanded="true"] .archive-divider-face');
    const selection = kind === "library_group";
    return surface?.animate(
      [{ transform: `translateY(${selection ? 4 : 1}px)` }, { transform: "translateY(0)" }],
      { duration: selection ? 140 : 120, easing: "cubic-bezier(.2,.8,.2,1)" },
    );
  }
  return null;
}

function maintainArchive(root, state, data, submitAction, action, prior) {
  const archive = root.querySelector(".archive");
  if (!archive || !data.archive) return null;
  const lifecycle = new AbortController();
  const options = { signal: lifecycle.signal };
  const field = archive.querySelector("#archive-query");
  const category = archive.querySelector("#archive-category");
  const heading = archive.querySelector("#archive-reader-title");
  const original = archive.querySelector(".archive-original");
  const kind = action?.kind;
  const open = kind === "library_open" || kind === "open_document";
  let timer;

  function send(intent) {
    if (state.pending) {
      if (intent.kind !== state.pending.kind || intent.id !== state.pending.id
          || intent.query !== state.pending.query || intent.category !== state.pending.category) {
        state.archiveQueued = intent;
      }
      return;
    }
    submitAction(intent);
  }

  function search() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (field.value !== data.archive.query) {
        send({ kind: "library_query", query: field.value });
      }
    }, ARCHIVE_QUERY_DELAY);
  }

  field.addEventListener("input", event => { if (!event.isComposing) search(); }, options);
  field.addEventListener("compositionend", search, options);
  field.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      clearTimeout(timer);
      if (field.value !== data.archive.query) send({ kind: "library_query", query: field.value });
    }
  }, options);
  category.addEventListener("change", () => {
    clearTimeout(timer);
    send({ kind: "library_category", category: category.value, query: field.value });
  }, options);
  archive.addEventListener("click", event => {
    const control = event.target.closest("button");
    if (!control) return;
    const attrs = control.dataset;
    if (!attrs.archiveOpen && !attrs.archiveGroup && !attrs.archiveAction) return;
    clearTimeout(timer);
    event.stopPropagation();
    if (attrs.archiveOpen) {
      if (!data.archive.reading) state.archiveIndexScroll = scrollParent(archive).scrollTop;
      send({ kind: "library_open", id: attrs.archiveOpen, query: field.value });
    } else if (attrs.archiveGroup && control.getAttribute("aria-expanded") === "false") {
      send({ kind: "library_group", category: attrs.archiveGroup, query: field.value });
    } else if (attrs.archiveAction) {
      send({ kind: attrs.archiveAction, id: data.archive.selected });
    }
  }, options);

  const stopOpening = archiveOpening(archive, data.archive.opening, lifecycle.signal);
  const edge = archiveEdge(archive, kind);
  if (heading && (open || kind === "library_retry")) {
    if (open) {
      scrollParent(archive).scrollTop = 0;
      archive.querySelector(".archive-reader").dataset.motion = "open";
    }
    focus(heading, true);
  } else if (kind === "library_back") {
    scrollParent(archive).scrollTop = state.archiveIndexScroll || 0;
    const sheet = root.querySelector(`#archive-sheet-${CSS.escape(data.archive.selected || "")}`);
    focus(sheet, true);
  } else if (prior && kind?.startsWith("library_")) {
    if (prior.id === "archive-query" && (kind === "library_query" || kind === "library_category")
        && prior.text !== action.query) {
      field.value = prior.text;
      search();
    }
    const target = prior.id ? root.querySelector(`#${CSS.escape(prior.id)}`) : null;
    if (target?.getClientRects().length) {
      focus(target);
      if (target === field) field.setSelectionRange(prior.start, prior.end);
    } else if (["library_clear", "library_reset", "library_restore", "library_query"].includes(kind)) {
      focus(field);
    }
    if (original && prior.selected === data.archive.selected) original.scrollTop = prior.originalScroll;
  } else if (heading) {
    focus(heading, true);
  }

  return {
    snapshot() {
      return {
        id: root.getRootNode().activeElement?.id, text: field.value,
        start: field.selectionStart, end: field.selectionEnd,
        originalScroll: original?.scrollTop || 0, selected: data.archive.selected,
      };
    },
    stop() {
      clearTimeout(timer);
      stopOpening();
      edge?.cancel();
      lifecycle.abort();
    },
  };
}
