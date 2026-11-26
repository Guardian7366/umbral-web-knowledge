function maintainClassification(root, state, data, submitAction, action, prior) {
  const form = root.querySelector(".classification-sheet");
  if (!form || !data.classification) return null;
  const scope = new AbortController();
  const options = { signal: scope.signal };
  const field = form.querySelector("textarea");
  const method = () => form.querySelector("input:checked").value;
  const view = root.querySelector(".classification-result");
  const details = view.querySelector("details");
  const result = view.querySelector(".classification-tab");
  const message = form.querySelector("#classification-message");
  const busy = form.querySelector(".classification-busy");
  const send = form.querySelector(".primary");
  let effect;

  if (prior && (prior.text !== data.classification.text || prior.method !== data.classification.method)) {
    field.value = prior.text;
    form.querySelector(`input[value="${prior.method}"]`).checked = true;
  } else {
    field.value = data.classification.text;
  }
  details.open = Boolean(prior?.expanded);

  function update(edit = false) {
    form.querySelector("#classification-method-help").textContent = data.classification.help[method()];
    details.querySelectorAll("[data-method-info]").forEach(info => { info.hidden = info.dataset.methodInfo !== method(); });
    const changed = field.value !== data.classification.text || method() !== data.classification.method;
    if (result) result.hidden = changed || state.pending?.kind === "classify_text";
    if (edit || changed) {
      effect?.cancel();
      message.hidden = true;
      field.removeAttribute("aria-invalid");
    }
    return changed;
  }

  form.addEventListener("input", () => update(true), options);
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (state.pending) return;
    effect?.cancel();
    if (result) result.hidden = true;
    message.hidden = true;
    send.disabled = true;
    busy.hidden = !field.value.trim();
    submitAction({kind:"classify_text", classificationText:field.value, classificationMethod:method()}, () => {
      busy.hidden = true;
      send.disabled = false;
      message.textContent = "Couldn’t classify this text. Try again.";
      message.dataset.state = "error";
      message.hidden = false;
    });
  }, options);
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  if (!update() && action?.kind === "classify_text") {
    const notice = data.classification.notice?.[0];
    if (notice === "empty" || notice === "unknown") {
      field.setAttribute("aria-invalid", "true");
      focus(field, true);
    } else if (result) {
      root.querySelector(".announcements").textContent = `Suggested category: ${result.querySelector("h2").textContent}.`;
      if (!motion.matches) {
        effect = result.querySelector(".classification-cant").animate(
          [{transform:"translateX(-10px)"}, {transform:"translateX(0)"}],
          {duration:200, easing:"cubic-bezier(.2,.8,.2,1)"},
        );
        motion.addEventListener("change", () => effect.cancel(), { once:true, signal:scope.signal });
      }
      if (prior?.editing) focus(field);
      else focus(send);
    } else {
      focus(form.querySelector("[name=retry]"));
    }
  } else if (prior?.editing) {
    focus(field);
    field.setSelectionRange(prior.start, prior.end);
  }

  return {
    snapshot() {
      return {
        text:field.value, method:method(), expanded:details.open,
        editing:root.getRootNode().activeElement === field, start:field.selectionStart, end:field.selectionEnd,
      };
    },
    stop() { effect?.cancel(); scope.abort(); },
  };
}
