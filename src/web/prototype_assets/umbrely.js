function createUmbrelyPlayer(config, initiallyPaused, onPause) {
  const metrics = globalThis[Symbol.for("umbral.umbrely.probe")] ??= {
    players: 0, timers: 0, observers: 0, listeners: 0, pendingImages: 0, frames: 0,
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const sprite = document.createElement("div");
  sprite.className = "umbrely-sprite";
  const base = new URL("./app/static/umbrely-local/", document.baseURI);
  const loaded = new Set();
  const loads = new Map();
  const life = new AbortController();
  const {signal} = life;
  const control = document.createElement("button");
  control.type = "button";
  control.className = "text-action umbrely-motion";
  let paused = initiallyPaused;
  let slot, visible = false, timer = null, desired = null, generation = 0, playing = false, suspended = false;

  function loadAsset(key, complete, failed) {
    if (loaded.has(key)) { complete(); return; }
    const image = new Image();
    function unregister() {
      if (!loads.has(key)) return false;
      loads.delete(key);
      image.onload = image.onerror = null;
      metrics.pendingImages--;
      return true;
    }
    loads.set(key, () => {
      unregister();
      image.removeAttribute("src");
    });
    metrics.pendingImages++;
    image.onload = () => {
      if (!unregister()) return;
      const asset = config.assets[key];
      if (image.naturalWidth !== asset.width || image.naturalHeight !== asset.height) {
        failed();
        return;
      }
      loaded.add(key);
      complete();
    };
    image.onerror = () => { if (unregister()) failed(); };
    image.src = new URL(config.assets[key].path, base).href;
  }

  function paint(key, tile = 0) {
    const asset = config.assets[key];
    const columns = asset.width / config.frameSize.width;
    const rows = asset.height / config.frameSize.height;
    const x = columns === 1 ? 0 : tile % columns / (columns - 1) * 100;
    const y = rows === 1 ? 0 : Math.floor(tile / columns) / (rows - 1) * 100;
    sprite.style.backgroundImage = 'url("' + new URL(asset.path, base).href + '")';
    sprite.style.backgroundSize = (columns * 100) + "% " + (rows * 100) + "%";
    sprite.style.backgroundPosition = x + "% " + y + "%";
    sprite.dataset.tile = tile;
  }

  function neutral() {
    sprite.dataset.umbrelyState = "ready";
    const asset = config.controls.reducedMotion.image;
    if (loaded.has(asset)) paint(asset);
  }

  function halt() {
    generation++;
    playing = false;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
      metrics.timers--;
    }
    for (const [key, cancel] of loads) if (key !== config.initialAsset) cancel();
    neutral();
  }

  function interrupt(returnToIdle = true) {
    desired = null;
    suspended = !returnToIdle;
    halt();
    resume();
  }

  function eligible() {
    return !paused && visible && !document.hidden && !reduced.matches && !signal.aborted;
  }

  function resume() {
    if (suspended || playing || !eligible() || !slot?.isConnected || !loaded.has(config.initialAsset)) return;
    let state = desired ?? "idle";
    const version = generation;
    const clip = config.states[state === "idle" ? "welcome" : state];
    playing = true;
    loadAsset(clip.atlas, () => {
      if (version !== generation || !eligible()) return;
      const start = performance.now();
      sprite.dataset.umbrelyState = state;
      function frame() {
        if (version !== generation || !eligible()) return;
        const elapsed = performance.now() - start;
        if (elapsed >= clip.totalMs && state === "welcome") {
          desired = null;
          state = "idle";
          sprite.dataset.umbrelyState = state;
        } else if (elapsed >= clip.totalMs && state !== "idle" && clip.playback !== "while-processing") {
          interrupt();
          return;
        }
        const offset = elapsed % clip.totalMs;
        let boundary = 0;
        for (let index = 0; index < clip.frames.length; index++) {
          const item = clip.frames[index];
          boundary += item.ms;
          if (boundary > offset) {
            paint(clip.atlas, item.tile);
            metrics.frames++;
            // Adjacent copies show the same pixels. Keep their full dwell time.
            for (let next = index + 1; clip.frames[next]?.tile === item.tile; next++) {
              boundary += clip.frames[next].ms;
            }
            break;
          }
        }
        if (boundary <= offset) return;
        metrics.timers++;
        timer = setTimeout(() => {
          timer = null;
          metrics.timers--;
          frame();
        }, Math.max(1, Math.ceil(boundary - offset)));
      }
      frame();
    }, () => {
      if (version === generation) interrupt(clip.atlas !== config.states.welcome.atlas);
    });
  }

  function visibilityChanged() {
    if (eligible()) resume();
    else {
      if (desired !== "processing") desired = null;
      halt();
    }
  }

  function syncControl() {
    control.textContent = paused ? "Resume Umbrely animation" : "Pause Umbrely animation";
    control.hidden = reduced.matches || Boolean(slot?.hidden);
  }

  control.addEventListener("click", () => {
    paused = !paused;
    onPause(paused);
    syncControl();
    visibilityChanged();
  }, {signal});
  syncControl();

  const observer = new IntersectionObserver(entries => {
    const entry = entries.findLast(item => item.target === slot);
    if (!entry) return;
    visible = entry.isIntersecting;
    visibilityChanged();
  });
  document.addEventListener("visibilitychange", visibilityChanged, {signal});
  reduced.addEventListener("change", () => {
    syncControl();
    visibilityChanged();
  }, {signal});
  metrics.players++;
  metrics.observers++;
  metrics.listeners += 3;
  neutral();

  return {
    attach(next, label) {
      if (next === slot) return;
      if (slot) observer.unobserve(slot);
      slot = next;
      slot.append(sprite);
      const toolbar = document.createElement("div");
      toolbar.className = "umbrely-toolbar";
      label.before(toolbar);
      toolbar.append(label, control);
      syncControl();
      observer.observe(slot);
      if (!loaded.has(config.initialAsset) && !loads.has(config.initialAsset)) loadAsset(config.initialAsset, () => {
        neutral();
        resume();
      }, () => { slot.hidden = true; syncControl(); interrupt(); });
    },
    react(state) {
      suspended = false;
      halt();
      if (state === "ready" || (state !== "processing" && (paused || document.hidden || reduced.matches))) {
        desired = null;
        resume();
        return;
      }
      desired = state;
      resume();
    },
    interrupt,
    settle() {
      if (suspended) {
        suspended = false;
        resume();
      }
    },
    stop() {
      if (signal.aborted) return;
      life.abort();
      observer.disconnect();
      interrupt(false);
      for (const cancel of loads.values()) cancel();
      sprite.remove();
      control.remove();
      slot = null;
      metrics.players--;
      metrics.observers--;
      metrics.listeners -= 3;
    },
  };
}

function updateUmbrely(root, state, data) {
  const slot = root.querySelector("[data-umbrely-slot]");
  const label = root.querySelector('.assistant-main .composer label[for="question"]');
  if (!slot || !label || !data.mascot) {
    state.umbrely?.stop();
    state.umbrely = null;
    return;
  }
  state.umbrely ??= createUmbrelyPlayer(data.mascot.config, Boolean(state.umbrelyPaused),
    paused => { state.umbrelyPaused = paused; });
  state.umbrely.attach(slot, label);
  const operation = data.mascot.operation;
  if (operation) {
    state.umbrelyWelcome = true;
    const event = operation.id + ":" + operation.phase;
    if (event !== state.umbrelyEvent) {
      state.umbrelyEvent = event;
      state.umbrely.react(operation.phase);
    }
  } else if (!state.umbrelyWelcome) {
    state.umbrelyWelcome = true;
    state.umbrely.react("welcome");
  } else if (!state.pending) {
    state.umbrely.settle();
  }
}
