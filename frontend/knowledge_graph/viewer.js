import {createGraphState,families} from "./graph_state.js";
import {metrics} from "./metrics.js";

const instances = new WeakMap();
const verb = edge => edge.verb.replaceAll("_"," ");

function node(tag, text, css = "") {
  const el = document.createElement(tag);
  if (text) el.textContent = text;
  if (css) el.className = css;
  return el;
}
function action(label, kind, value, css = "") {
  const el = node("button",label,css);
  el.type = "button";
  el.dataset.action = kind;
  if (value) el.dataset.value = value;
  return el;
}
function snapshotScroll(element) {
  const snapshots = [];
  for (let parent=element;parent;parent=parent.parentNode ?? parent.host) {
    if (typeof parent.scrollTop==="number") snapshots.push([parent,parent.scrollTop]);
  }
  snapshots.push([document.scrollingElement,document.scrollingElement.scrollTop]);
  return snapshots;
}
function focus(el) { el?.focus({preventScroll:true}); }

function attach(root, bridge) {
  const {graph,symbols,initialMode} = bridge.data;
  let trigger = bridge.setTriggerValue;
  const life = new AbortController();
  const {signal} = life;
  metrics.mounts++;
  const {state,nodes,matches,subgraph,select,deselect,relations} = createGraphState(graph);
  let view = initialMode, legend = false, scene, pose, current = subgraph(), highlights;
  let reader, selectionOrigin, drawer = false, failure, loading = false, mountAttempt = 0;
  let direction = "orbit", touchActive = false, needsReveal = true, inspectorClosing;
  const touch = matchMedia("(pointer: coarse)");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  root.innerHTML = [
    '<div class="lab-explorer">',
    '<header class="lab-header"><p class="lab-path">Knowledge Hub <span>/</span> <strong>Knowledge Graph</strong></p>',
    '<div class="lab-title-row"><h1 id="page-title" tabindex="-1">Knowledge Graph</h1>',
    '<div class="lab-tabs" role="group" aria-label="Graph view"><button type="button" data-action="3d">3D view</button><button type="button" data-action="text">Text view</button></div></div>',
    '<div class="lab-searchbar"><label class="lab-search"><span class="sr-only">Find a node</span>'+symbols.Search+
      '<input type="search" placeholder="Find a node" autocomplete="off" aria-describedby="search-description"></label>',
    '<span class="sr-only" id="search-description">Search names, keys, document IDs and titles in this graph.</span>',
    '<button type="button" data-action="filters" aria-controls="lab-filter-panel" aria-expanded="false">Node types</button>',
    '<button type="button" data-action="legend" aria-pressed="false">Legend</button>',
    '<p class="lab-counts"></p></div><div class="lab-filters" id="lab-filter-panel" hidden></div>',
    '<div class="lab-search-return"></div><div class="lab-search-results" hidden></div></header>',
    '<div class="lab-status sr-only" role="status"></div><div class="lab-error" role="status" hidden></div>',
    '<section class="lab-stage" aria-label="3D graph"><div class="lab-scene" role="group" aria-label="3D knowledge graph" aria-describedby="scene-description" tabindex="-1"></div><p id="scene-description" class="sr-only">Select a shape, use the camera controls or explore all nodes in Text view.</p>',
    '<p class="lab-stage-note" hidden></p><div class="lab-toolbar"><div class="lab-camera" role="group" aria-label="Camera controls"></div>',
    '<button type="button" data-action="camera-help" aria-expanded="false" aria-controls="lab-camera-help">Camera help</button></div>',
    '<div class="lab-camera-help" id="lab-camera-help" hidden></div></section>',
    '<section class="lab-legend" aria-label="Graph legend" hidden></section>',
    '<section class="lab-index" aria-label="Node index" hidden><h2 tabindex="-1">Node index</h2><div class="lab-items"></div></section>',
    '<section class="lab-details" aria-label="Node inspector" hidden></section></div>',
    '<section class="lab-reader" aria-label="Original document" hidden></section>',
  ].join("");
  const get = query => root.querySelector(query);
  const shell = get(".lab-explorer"), input=get("input"), host=get(".lab-scene"), stage=get(".lab-stage");
  const toolbar=get(".lab-toolbar"), filters=get(".lab-filters"), searchResults=get(".lab-search-results");
  const index=get(".lab-index"), items=get(".lab-items"), details=get(".lab-details"), original=get(".lab-reader");
  const count=get(".lab-counts"), status=get(".lab-status"), error=get(".lab-error"), stageNote=get(".lab-stage-note");
  const help=get(".lab-camera-help"), legendPanel=get(".lab-legend");
  const control = kind => get('[data-action="'+kind+'"]');
  const camera=get(".lab-camera");
  const speak = value => { status.textContent = value; };
  function openPanel(panel, button, show) { panel.hidden=!show; button.setAttribute("aria-expanded",String(show)); }
  function setPressed(el, value) { el.setAttribute("aria-pressed",String(value)); }

  const all=action("All types","all-types");
  filters.append(all);
  for (const family of families) {
    const label=node("label");
    const checkbox=node("input");
    checkbox.type="checkbox";
    checkbox.dataset.family=family;
    checkbox.checked=true;
    label.append(checkbox,document.createTextNode(family));
    filters.append(label);
  }
  const clear=action("Clear search","clear");
  const restore=action("Back to results","restore-query");
  restore.hidden=true;
  get(".lab-search-return").append(clear,restore);
  for (const [label,kind] of [
    ["Orbit","orbit"],["Pan","pan"],["−","zoom-out"],["+","zoom-in"],["Reset view","reset"],
  ]) camera.append(action(label,kind));
  control("zoom-out").setAttribute("aria-label","Zoom out");
  control("zoom-in").setAttribute("aria-label","Zoom in");
  const directional=node("div","","lab-directions");
  for (const [word,arrow] of [["left","←"],["right","→"],["up","↑"],["down","↓"]]) {
    const button=action(arrow,"step",word);
    button.setAttribute("aria-label",word);
    directional.append(button);
  }
  help.append(node("p","Drag in Orbit or Pan, or use the direction buttons. Zoom changes the graph, while your browser zoom remains available."),directional,action("Use DPR 1","dpr"));
  const legendClose=action("Close legend","legend-close");
  const legendTypes=node("ul");
  for (const family of families) legendTypes.append(node("li",family));
  legendPanel.append(legendTypes,node("p","Arrows point from source to target. Position shows layout only."),legendClose);

  function updateCamera() {
    const active=!touch.matches || touchActive;
    setPressed(control("orbit"),direction==="orbit" && active);
    setPressed(control("pan"),direction==="pan" && active);
    for (const button of directional.children) {
      button.setAttribute("aria-label",(direction==="pan"?"Pan ":"Orbit ")+button.dataset.value);
    }
    scene?.setControl(direction,active);
  }

  function labelFor(id) { return nodes.get(id).label; }
  function titleFor(record) { return record.metadata.catalogTitle ?? record.label; }
  function renderedSelection() {
    root.dataset.selected=state.selected ? nodes.get(state.selected).originalKey : "";
    root.dataset.edge=state.edge ?? "";
    root.toggleAttribute("data-has-selection",Boolean(state.selected));
    renderInspector();
  }
  function resultButton(record, origin) {
    const button = action(titleFor(record),"select",record.id,"lab-result");
    button.dataset.origin=origin;
    setPressed(button,state.selected===record.id);
    if (record.documentId) button.prepend(node("span",record.documentId,"lab-doc-id"));
    if (state.selected===record.id) button.append(node("span","Selected","lab-selected"));
    return button;
  }
  function refreshLists() {
    clear.hidden=!state.query;
    restore.hidden=state.suspended===null;
    if (state.query!==input.value) input.value=state.query;
    const queryActive=Boolean(state.query.trim());
    const found=current.members.filter(matches);
    highlights=queryActive ? new Set(found.map(item=>item.id)) : null;
    const partial=current.members.length!==graph.counts.nodes;
    count.textContent=partial
      ? current.members.length+" of "+graph.counts.nodes+" nodes · "+current.edges.length+" of "+graph.counts.edges+" relations"
      : graph.counts.nodes+" nodes / "+graph.counts.edges+" relations";
    root.dataset.nodes=current.members.length;
    root.dataset.edges=current.edges.length;
    root.dataset.matches=found.length;
    for (const input of filters.querySelectorAll("input")) input.checked=state.types.has(input.dataset.family);
    setPressed(all,state.types.size===families.length);
    searchResults.hidden=view!=="3d" || !queryActive || !drawer || legend;
    searchResults.replaceChildren();
    if (!searchResults.hidden) {
      searchResults.append(node("p",found.length ? found.length+" matching "+(found.length===1?"node":"nodes") : "No matching nodes."));
      for (const record of found) searchResults.append(resultButton(record,"search"));
    }
    index.hidden=view!=="text" || legend;
    items.replaceChildren();
    if (view==="text") {
      index.querySelector("h2").textContent=queryActive ? found.length+" matching "+(found.length===1?"node":"nodes") : "Node index";
      if (!found.length) items.append(node("p",queryActive ? "No matching nodes." : "No nodes visible."));
      for (const family of families) {
        const records=found.filter(item=>item.family===family).sort((a,b)=>a.label.localeCompare(b.label));
        if (!records.length) continue;
        const group=node("section","","lab-family");
        group.append(node("h3",family));
        for (const record of records) group.append(resultButton(record,"text"));
        items.append(group);
      }
      if (!current.edges.length && current.members.length) items.append(node("p","No visible relations."));
      if (!current.members.length) items.append(action("Show all types","all-types"));
    }
    stageNote.hidden=legend || current.members.length>0 && (!queryActive || found.length>0) && current.edges.length>0;
    stageNote.textContent=!current.members.length ? "No nodes visible." : queryActive && !found.length ? "No matching nodes." : "No visible relations.";
    if (!current.members.length) stageNote.append(" ", action("Show all types","all-types"));
  }

  function renderInspector() {
    const record=nodes.get(state.selected);
    if (!record || legend) {
      if (!details.hidden && !legend && !reduced.matches) {
        inspectorClosing?.cancel();
        details.inert=true;
        inspectorClosing=details.animate([
          {clipPath:"inset(0 0 0 0)",opacity:1},
          {clipPath:"inset(6px 0 0 0)",opacity:0},
        ],{duration:140,easing:"cubic-bezier(.4,0,1,1)"});
        inspectorClosing.onfinish=()=>{details.hidden=true; details.replaceChildren();};
      } else {
        details.hidden=true;
        details.replaceChildren();
      }
      return;
    }
    inspectorClosing?.cancel();
    const opening=details.hidden || details.inert;
    details.hidden=false;
    details.inert=false;
    const header=node("div","","lab-node-overview");
    header.append(node("p","Selected "+record.family.toLowerCase(),"lab-detail-key"));
    const title=node("h2",record.label);
    title.tabIndex=-1;
    header.append(title);
    if (record.documentId) {
      header.append(node("p",record.metadata.catalogTitle,"lab-doc-title"),
        node("p",record.metadata.catalogCategory.replaceAll("_"," "),"lab-detail-key"));
    }
    const info=node("details","","lab-node-meta");
    info.append(node("summary","Node details"),node("p","Original key: "+record.originalKey),
      node("p","Node ID: "+record.id));
    header.append(info);
    const actions=node("div","","lab-detail-actions");
    if (record.documentId) actions.append(action("Open original","original",record.documentId,"lab-primary"));
    if (view==="3d") actions.append(action("Focus node","focus"));
    actions.append(action("Deselect","deselect"));
    if (state.previous && current.ids.has(state.previous.id)) actions.append(action("Back to previous node","previous"));
    header.append(actions);
    const panels=node("div","","lab-relation-columns");
    const directions=relations(record.id,current.edges);
    const allEdges=relations(record.id,graph.edges);
    for (const kind of ["incoming","outgoing"]) {
      const column=node("section","","lab-detail-column");
      column.append(node("h3",kind[0].toUpperCase()+kind.slice(1)+" · "+directions[kind].length));
      if (!directions[kind].length) column.append(node("p","No "+kind+" relations."));
      for (const edge of directions[kind]) {
        const neighbor=kind==="incoming" ? edge.source : edge.target;
        const row=node("article","","lab-relation");
        const endpoint=action(labelFor(neighbor)+" →","follow",neighbor,"lab-endpoint");
        const relationship=action(verb(edge),"edge",edge.id,"lab-edge-row");
        relationship.setAttribute("aria-label",labelFor(edge.source)+" "+verb(edge)+" "+labelFor(edge.target));
        setPressed(relationship,state.edge===edge.id);
        row.append(endpoint,relationship);
        column.append(row);
      }
      const hidden=allEdges[kind].length-directions[kind].length;
      if (hidden) column.append(node("p",hidden+" hidden by node types."),action("Show all types","all-types"));
      panels.append(column);
    }
    const edge=graph.edges.find(item=>item.id===state.edge);
    if (edge) {
      const triple=node("div","","lab-triple");
      triple.tabIndex=-1;
      triple.append(node("h3","Directed relation"),
        action(labelFor(edge.source),"follow",edge.source),node("span"," → "+verb(edge)+" → "),
        action(labelFor(edge.target),"follow",edge.target),node("p","Original verb: "+edge.verb,"lab-detail-key"));
      panels.append(triple);
    }
    details.replaceChildren(header,panels);
    if (opening && !reduced.matches) details.animate([
      {clipPath:"inset(8px 0 0 0)",opacity:.70},{clipPath:"inset(0 0 0 0)",opacity:1},
    ],{duration:180,easing:"cubic-bezier(.2,.8,.2,1)"});
  }

  function changeSelection(id, origin, follow=false) {
    scene?.cancelMotion();
    if (!id) {
      if (!state.selected) return;
      deselect();
      renderedSelection();
      refreshLists();
      scene?.setGraph();
      speak("Selection cleared.");
      focus(selectionOrigin?.isConnected && !selectionOrigin.hidden ? selectionOrigin : input);
      selectionOrigin=null;
      return;
    }
    if (!select(id,follow)) return;
    if (!follow) selectionOrigin=origin instanceof HTMLCanvasElement ? host : origin;
    if (state.suspended!==null && follow) drawer=false;
    renderedSelection();
    refreshLists();
    scene?.setGraph(true);
    const counts=relations(id,current.edges);
    speak(labelFor(id)+", "+nodes.get(id).family+" selected. "+counts.incoming.length+" incoming and "+counts.outgoing.length+" outgoing."
      +(state.suspended!==null?" Search paused. Back to results restores it.":""));
    if (origin instanceof HTMLCanvasElement) focus(host);
    else if (follow || origin?.classList.contains("lab-result") || origin?.classList.contains("lab-tag")) focus(details.querySelector("h2"));
  }
  function chooseEdge(id) {
    const edge=current.edges.find(item=>item.id===id);
    if (!edge) return;
    if (state.selected!==edge.source && state.selected!==edge.target) select(edge.source,true);
    state.edge=id;
    renderedSelection();
    refreshLists();
    scene?.setGraph(true);
    const triple=details.querySelector(".lab-triple");
    focus(triple);
    speak(labelFor(edge.source)+" "+verb(edge)+" "+labelFor(edge.target)+".");
  }

  function changeFilters(family) {
    if (family) {
      if (state.types.has(family)) state.types.delete(family);
      else state.types.add(family);
    } else state.types=new Set(families);
    current=subgraph();
    const removed=state.selected && !current.ids.has(state.selected);
    if (removed) deselect();
    if (!current.edges.some(edge=>edge.id===state.edge)) state.edge=null;
    refreshLists();
    renderedSelection();
    scene?.setGraph();
    if (!reduced.matches && scene) host.animate([{opacity:.75},{opacity:1}],
      {duration:100,easing:"cubic-bezier(.2,.8,.2,1)"});
    speak(count.textContent+(removed?". Selection cleared by node types.":""));
  }

  function storePose() { if (scene && !legend) pose=scene.snapshot(); }
  function stopScene(keepPose=true) {
    if (keepPose) storePose();
    scene?.stop();
    scene=null;
    delete host.dataset.draws;
    delete host.dataset.pose;
    delete host.dataset.moving;
  }
  function surface() {
    root.dataset.mode=view;
    root.toggleAttribute("data-legend",legend);
    setPressed(control("3d"),view==="3d");
    setPressed(control("text"),view==="text");
    setPressed(control("legend"),legend);
    stage.hidden=view!=="3d";
    legendPanel.hidden=!legend;
    error.hidden=!failure;
    if (failure) error.replaceChildren(node("p",failure),action("Retry 3D","retry-3d"));
    refreshLists();
    renderedSelection();
  }
  function showText(message) {
    mountAttempt++;
    loading=false;
    stopScene();
    view="text";
    legend=false;
    failure=message;
    surface();
    speak(message ? "" : "Text view ready.");
    if (message) focus(control("retry-3d"));
  }
  async function show3D() {
    if (loading || scene || reader) return;
    view="3d";
    failure=null;
    loading=true;
    const attempt=++mountAttempt;
    surface();
    speak("Loading 3D view…");
    try {
      const href=new URL("./scene.js", import.meta.url);
      const module=await import(href.href);
      if (signal.aborted || attempt!==mountAttempt || reader) return;
      scene=module.mountScene(host,graph,{
        selection:()=>state.selected, select:changeSelection, inspect:chooseEdge, activeEdge:()=>state.edge,
        onLoss:()=>showText("3D view unavailable. The graphics context was lost."),
        legendMode:()=>legend, shown:()=>current.ids, matches:()=>highlights, restoredPose:pose,
      });
      updateCamera();
      if (needsReveal) {
        needsReveal=false;
        if (!reduced.matches) host.animate([
          {clipPath:"inset(6px 0 0 0)",filter:"brightness(.82)"},
          {clipPath:"inset(0 0 0 0)",filter:"brightness(1)"},
        ],{duration:260,easing:"cubic-bezier(.2,.8,.2,1)"});
      }
      speak("3D view ready.");
    } catch (err) {
      if (signal.aborted || attempt!==mountAttempt) return;
      console.warn("Graph renderer unavailable",err);
      showText("3D view unavailable. You can continue in Text view.");
    } finally {
      if (attempt===mountAttempt) loading=false;
    }
  }
  function toggleLegend(show) {
    if (show===legend) return;
    storePose();
    legend=show;
    surface();
    scene?.changeView(pose);
    if (!show) focus(control("legend"));
  }

  function requestOriginal() {
    reader.token=crypto.randomUUID();
    metrics.requests++;
    original.replaceChildren(node("p","Loading original…"),action("Back to graph","back",null,"lab-back"));
    trigger("original",{id:reader.id,token:reader.token});
  }
  function openOriginal(id, origin) {
    if (reader) return;
    reader={id,origin,scroll:snapshotScroll(root)};
    stopScene();
    shell.hidden=true;
    original.hidden=false;
    requestOriginal();
    focus(original.querySelector("button"));
  }
  function exitOriginal() {
    if (!reader) return;
    const {origin,scroll}=reader;
    reader=null;
    original.hidden=true;
    original.replaceChildren();
    shell.hidden=false;
    if (view==="3d") void show3D();
    for (const [parent,value] of scroll) parent.scrollTop=value;
    focus(origin.isConnected ? origin : control("original"));
  }

  input.addEventListener("input",()=>{
    state.query=input.value;
    state.suspended=null;
    drawer=true;
    refreshLists();
    scene?.setGraph();
    speak(state.query ? root.dataset.matches+" matching nodes." : "Search cleared.");
  },{signal});
  input.addEventListener("focus",()=>{drawer=true; refreshLists();},{signal});
  filters.addEventListener("change",event=>{
    if (event.target.dataset.family) changeFilters(event.target.dataset.family);
  },{signal});
  touch.addEventListener("change",updateCamera,{signal});
  root.addEventListener("keydown",event=>{
    if (event.key==="Enter" && event.target===input && state.query.trim()) {
      const first=current.members.find(matches);
      if (first) {
        drawer=false;
        changeSelection(first.id,input);
        focus(details.querySelector("h2"));
      }
      event.preventDefault();
    }
    if (event.key==="Escape") {
      if (reader) exitOriginal();
      else if (legend) toggleLegend(false);
      else if (!filters.hidden) {openPanel(filters,control("filters"),false);focus(control("filters"));}
      else if (!help.hidden) {openPanel(help,control("camera-help"),false);focus(control("camera-help"));}
      else if (!searchResults.hidden) {drawer=false;refreshLists();focus(input);drawer=false;refreshLists();}
      else if (touchActive) {touchActive=false;updateCamera();}
      else if (state.selected) changeSelection(null,event.target);
      else return;
      event.preventDefault();
    }
    if (["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key) &&
        (camera.contains(event.target) || directional.contains(event.target))) {
      scene?.step(event.key.slice(5).toLowerCase());
      event.preventDefault();
    }
  },{signal});

  root.addEventListener("click",event=>{
    const button=event.target.closest("[data-action],[data-graph-reader]");
    if (!button) {
      if (!searchResults.hidden && event.target!==input && !event.target.closest(".lab-search")) {
        drawer=false;refreshLists();
      }
      return;
    }
    const value=button.dataset.value;
    switch (button.dataset.action || button.dataset.graphReader) {
      case "filters": drawer=false; refreshLists(); openPanel(filters,button,filters.hidden); break;
      case "all-types": changeFilters(); break;
      case "clear": state.query=""; state.suspended=null; refreshLists(); scene?.setGraph(); focus(input); break;
      case "restore-query":
        state.query=state.suspended ?? ""; state.suspended=null; drawer=true;
        refreshLists(); scene?.setGraph(); focus(input); break;
      case "select": drawer=false; changeSelection(value,button); break;
      case "follow": changeSelection(value,button,true); break;
      case "edge": chooseEdge(value); break;
      case "previous": {
        const prior=state.previous;
        state.query=prior.query; state.suspended=prior.suspended; state.previous=null;
        changeSelection(prior.id,button);
        if (prior.edge) chooseEdge(prior.edge);
        else focus(details.querySelector("h2"));
        break;
      }
      case "deselect": changeSelection(null,button); break;
      case "legend": toggleLegend(!legend); break;
      case "legend-close": toggleLegend(false); break;
      case "text": if (view!=="text") showText(); break;
      case "3d": case "retry-3d": if (view!=="3d" || !scene) {legend=false; void show3D();} break;
      case "focus": scene?.focus(); break;
      case "reset": scene?.reset(); break;
      case "zoom-in": scene?.zoom(1/1.2); break;
      case "zoom-out": scene?.zoom(1.2); break;
      case "pan": case "orbit":
        touchActive=touch.matches && !(touchActive && direction===button.dataset.action);
        direction=button.dataset.action;
        updateCamera();
        speak(touch.matches && !touchActive ? "Page scrolling enabled over the scene." : direction+" camera mode.");
        break;
      case "step": scene?.step(value); break;
      case "camera-help": openPanel(help,button,help.hidden); break;
      case "dpr":
        host.dataset.pixelMode=host.dataset.pixelMode==="low" ? "auto" : "low";
        setPressed(button,host.dataset.pixelMode==="low"); scene?.resize(); break;
      case "original": openOriginal(value,button); break;
      case "back": exitOriginal(); break;
      case "retry": if (reader) requestOriginal(); break;
    }
  },{signal});

  surface();
  updateCamera();
  if (view==="3d") void show3D();
  return {
    blob:graph.source.blob,
    update(next) {
      trigger=next.setTriggerValue;
      const response=next.data.reader;
      if (!reader || response?.token!==reader.token || reader.rendered===response.token) return;
      reader.rendered=response.token;
      original.innerHTML=response.html;
      const heading=original.querySelector("h2");
      if (heading) focus(heading);
      else focus(original.querySelector("button"));
      for (const [parent] of reader.scroll) parent.scrollTop=0;
    },
    dispose() {
      if (signal.aborted) return;
      life.abort();
      inspectorClosing?.cancel();
      host.getAnimations().forEach(animation=>animation.cancel());
      stopScene(false);
      metrics.unmounts++;
      instances.delete(root);
      root.replaceChildren();
    },
  };
}

export default function render(bridge) {
  const root=bridge.parentElement.querySelector(".graph-lab");
  if (!root || !bridge.data?.graph) return;
  const prior=instances.get(root);
  if (prior?.blob===bridge.data.graph.source.blob) {
    prior.update(bridge);
    return prior.dispose;
  }
  prior?.dispose();
  const explorer=attach(root,bridge);
  instances.set(root,explorer);
  return explorer.dispose;
}
