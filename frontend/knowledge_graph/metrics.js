export const metrics = globalThis[Symbol.for("umbral.graph.probe")] ??= {
  mounts:0, unmounts:0, contexts:0, observers:0, scopes:0, pending:0, draws:0, losses:0, requests:0,
};
