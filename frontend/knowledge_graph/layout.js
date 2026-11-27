// World positions are presentation data. No distance defines semantic proximity.
const positions = {
  "Design and UX":[-6.6,.14,6.85],
  "Prototype":[-.25,.19,7.5],
  "Reusable Components":[5.85,.41,6.45],
  "Interface Development":[8.8,.45,3.85],
  "design_references":[-8.25,.31,3.85],
  "Creative Direction":[-8.85,.44,-8.4],
  "creative_methods":[-5.35,.38,-8.18],
  "Project Management":[3.88,.47,-8.38],
  "project_learnings":[7.35,.48,-8.28],
  "UW01":[-9.4,.13,-5.22],
  "Visual Hierarchy":[-6.7,.22,-5.50],
  "UW02":[-3.3,.16,-5.60],
  "Responsiveness":[-.68,.26,-5.52],
  "UW03":[2.76,.21,-5.84],
  "Module Composition":[5.55,.26,-5.72],
  "UW07":[-8.9,.13,-1.58],
  "Aula Clara Project":[-6.22,.27,-1.70],
  "UW08":[-2.72,.18,-2.08],
  "Estudio Norte Project":[.05,.25,-2.17],
  "UW09":[3.55,.22,-2.20],
  "Mesa Abierta Project":[6.46,.35,-2.36],
  "UW04":[-4.0,.15,2.0],
  "Ideation":[-.98,.23,1.77],
  "UW05":[1.45,.19,1.28],
  "Visual Proposal Evaluation":[4.12,.28,1.16],
  "UW06":[6.72,.16,.65],
  "Concept Selection":[9.25,.32,.37],
};

export function spatialRecords(graph) {
  return graph.nodes.map(node => {
    if (!Object.hasOwn(positions, node.originalKey)) {
      throw new Error(`Missing position for ${node.originalKey}`);
    }
    return {...node, position:positions[node.originalKey]};
  });
}
