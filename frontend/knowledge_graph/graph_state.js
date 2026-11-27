export const families = ["Department","Knowledge group","Document","Concept","Project example"];

export function normalize(value) {
  return value.normalize("NFD").replace(/\p{M}/gu,"").toLocaleLowerCase("en")
    .trim().replace(/\s+/g," ");
}

export function createGraphState(graph) {
  const nodes = new Map(graph.nodes.map(node => [node.id,node]));
  const catalog = new Map(graph.nodes.map(node => [
    node.id, [node.documentId,node.originalKey,node.label,node.metadata.catalogTitle]
      .filter(Boolean).map(normalize),
  ]));
  const state = {
    selected:null, edge:null, query:"", types:new Set(families), previous:null, suspended:null,
  };
  function visible(node) { return state.types.has(node.family); }
  function subgraph() {
    const members = graph.nodes.filter(visible);
    const ids = new Set(members.map(node => node.id));
    return {members, ids, edges:graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target))};
  }
  function matches(node) {
    const query = normalize(state.query);
    return catalog.get(node.id).some(field => field.includes(query));
  }
  function select(id, follow = false) {
    if (!nodes.has(id) || !visible(nodes.get(id))) return false;
    if (follow && state.selected && state.selected !== id) {
      state.previous = {id:state.selected,edge:state.edge,query:state.query,suspended:state.suspended};
      if (!matches(nodes.get(id))) {
        state.suspended = state.query;
        state.query = "";
      }
    }
    state.selected = id;
    state.edge = null;
    return true;
  }
  function deselect() { state.selected = state.edge = state.previous = null; }
  function relations(id, edges) {
    return {
      incoming:edges.filter(edge => edge.target === id),
      outgoing:edges.filter(edge => edge.source === id),
    };
  }
  return {state,nodes,matches,visible,subgraph,select,deselect,relations};
}
