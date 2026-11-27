import {
  BufferGeometry, CircleGeometry, Color, ConeGeometry, DirectionalLight,
  Float32BufferAttribute, Group, HemisphereLight, InstancedMesh, LineBasicMaterial, LineSegments,
  Mesh, MeshBasicMaterial, Object3D, PerspectiveCamera, Raycaster, Scene,
  Vector2, Vector3, WebGLRenderer, MOUSE, TOUCH,
} from "three";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
import {LineMaterial} from "three/addons/lines/LineMaterial.js";
import {LineSegments2} from "three/addons/lines/LineSegments2.js";
import {LineSegmentsGeometry} from "three/addons/lines/LineSegmentsGeometry.js";
import {buildFamilies, families} from "./geometry.js";
import {spatialRecords} from "./layout.js";

import {metrics} from "./metrics.js";
const motion = matchMedia("(prefers-reduced-motion: reduce)");
const steelLink = new Color(0x82a6c5);
const optical = new Color(0x68e8f2);
const solidTint = new Color(0xffffff);
const subduedTint = new Color(0xa6b9ce);
const backgroundTint = new Color(0x354e70);
const backgroundLink = new Color(0x294971);

export function mountScene(host, graph, interaction) {
  const {selection, select, inspect, onLoss, legendMode, shown, matches, activeEdge, restoredPose} = interaction;
  const renderer = new WebGLRenderer({antialias:true, alpha:true});
  const canvas = renderer.domElement;
  const scene = new Scene();
  const life = new AbortController();
  const {signal} = life;
  const geometryResources = new Set();
  const materialResources = new Set();
  const instances = new Set();
  let controls, observer, cancelFrame, releaseControls, stopped = false;
  metrics.contexts++;
  metrics.scopes++;

  function stop() {
    if (stopped) return;
    stopped = true;
    cancelFrame?.();
    if (observer) {
      observer.disconnect();
      metrics.observers--;
    }
    life.abort();
    metrics.scopes--;
    releaseControls?.();
    controls?.dispose();
    const count = () => ({
      geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,
      programs:renderer.info.programs.length,
    });
    const before = count();
    for (const mesh of instances) mesh.dispose();
    for (const geometry of geometryResources) geometry.dispose();
    for (const material of materialResources) material.dispose();
    scene.clear();
    renderer.setSize(1,1,false);
    renderer.dispose();
    const context = renderer.getContext();
    if (!context.isContextLost()) renderer.forceContextLoss();
    metrics.lastRelease = {before,after:count(),contextLost:context.isContextLost()};
    metrics.contexts--;
    host.replaceChildren();
  }

  try {
    canvas.setAttribute("aria-hidden","true");
    host.append(canvas);
    const camera = new PerspectiveCamera(38,1,.07,220);
    controls = new OrbitControls(camera,canvas);
    controls.enableDamping = false;
    controls.minDistance = 2.9;
    controls.maxDistance = 128;
    controls.minPolarAngle = .35;
    controls.maxPolarAngle = 1.46;
    controls.maxTargetRadius = 26;
    const graphGroup = new Group(), legendGroup = new Group();
    scene.add(graphGroup,legendGroup);
    const models = buildFamilies(geometryResources, materialResources);
    const records = spatialRecords(graph);
    const byId = new Map(records.map(record=>[record.id,record]));
    const legend = families.map((family,i)=>({
      id:family, label:family, family, position:[(i-2)*2.52,.14,(i%2)*-.19],
    }));
    const pose = new Object3D();
    const up = new Vector3(0,1,0);
    const defaultDirection = new Vector3(.11,.625,.773).normalize();

    const legendDirection = new Vector3(.13,.29,.948).normalize();
    const labels = [];

    function geometry(resource) {
      geometryResources.add(resource);
      return resource;
    }
    function material(resource) {
      materialResources.add(resource);
      return resource;
    }
    function batch(geo, mat, count, parent) {
      const result = new InstancedMesh(geo,mat,count);
      instances.add(result);
      parent.add(result);
      return result;
    }
    function label(text, position, group, options = {}) {
      const tag = document.createElement(group === legendGroup ? "span" : "button");
      tag.className = "lab-tag" + (options.edge ? " edge" : "");
      const caption = document.createElement("span");
      caption.textContent = text;
      tag.append(caption);
      if (tag instanceof HTMLButtonElement) {
        tag.type = "button";
        tag.addEventListener("click", () => options.edge ? inspect(options.edge.id) : select(options.id, tag), {signal});
      }
      tag.hidden = true;
      host.append(tag);
      labels.push({tag, position, group, textLength:text.length, ...options});
    }

    const floorLines = [];
    for (const z of [-10,-6,-2,2,6,10]) floorLines.push(-12,-.87,z,12,-.87,z);
    for (const x of [-12,-8,-4,0,4,8,12]) floorLines.push(x,-.87,-10,x,-.87,10);
    const floorGeometry = geometry(new BufferGeometry().setAttribute("position", new Float32BufferAttribute(floorLines,3)));
    const floorMaterial = material(new LineBasicMaterial({color:0x6a9dc6,transparent:true,opacity:.22}));
    scene.add(new LineSegments(floorGeometry,floorMaterial));

    const shade = geometry(new CircleGeometry(1,12).rotateX(-Math.PI/2));
    const shadeColors = [0.013,.032,.085,.45];
    for(let i=1;i<shade.attributes.position.count;i++) shadeColors.push(.013,.032,.085,0);
    shade.setAttribute("color",new Float32BufferAttribute(shadeColors,4));
    const shadeMaterial = material(new MeshBasicMaterial({
      vertexColors:true,transparent:true,depthWrite:false,
    }));

    function instantiate(nodes, parent, legendOnly) {
      const batches = [];
      const shadows = batch(shade,shadeMaterial,nodes.length,parent);
      shadows.members = nodes;
      for (const node of nodes) label(node.label,new Vector3(...node.position).add(new Vector3(0,-.91,.36)),parent,{id:node.id});
      for (const [family,parts] of models) {
        const members = nodes.filter(node=>node.family===family);
        if (!members.length) continue;
        for (const part of parts) {
          const object = batch(part.geometry,part.material,members.length,parent);
          object.members = members;
          object.userData.nodes = members;
          batches.push(object);
        }
      }
      return {batches,shadows,legendOnly};
    }
    const graphModels = instantiate(records, graphGroup, false);
    const legendModels = instantiate(legend, legendGroup, true);
    function positionModels({batches,shadows,legendOnly}, visible) {
      const allowed = node => legendOnly || visible.has(node.id);
      const members = shadows.members.filter(allowed);
      members.forEach((node,i)=>{
        pose.position.set(node.position[0]+.18,-.847,node.position[2]-.16);
        pose.rotation.set(0,0,0);
        pose.scale.set(1.22,1,.69);
        pose.updateMatrix();
        shadows.setMatrixAt(i,pose.matrix);
      });
      updateBounds(shadows,members.length);
      for (const object of batches) {
        const visibleMembers = object.members.filter(allowed);
        object.userData.nodes = visibleMembers;
        visibleMembers.forEach((node,i)=>{
          pose.position.set(...node.position);
          pose.rotation.set(0,legendOnly ? -.30 : -.26,0);
          pose.scale.setScalar(1);
          pose.updateMatrix();
          object.setMatrixAt(i,pose.matrix);
          object.setColorAt(i,solidTint);
        });
        updateBounds(object,visibleMembers.length);
        object.instanceColor && (object.instanceColor.needsUpdate = true);
      }
    }
    function updateBounds(object,count) {
      object.count = count;
      object.visible = count > 0;
      object.instanceMatrix.needsUpdate = true;
      object.computeBoundingSphere();
    }

    const arrowTransforms = [];
    const linePoints = [];
    const lineColors = [];
    const arrowMaterial = material(new MeshBasicMaterial({color:0xffffff}));
    const heads = batch(geometry(new ConeGeometry(.103,.234,5)),arrowMaterial,graph.edges.length,graphGroup);
    for (const [i, edge] of graph.edges.entries()) {
      const start = new Vector3(...byId.get(edge.source).position);
      const end = new Vector3(...byId.get(edge.target).position);
      start.y -= .29;
      end.y -= .29;
      const direction = end.clone().sub(start).normalize();
      start.addScaledVector(direction,.86);
      end.addScaledVector(direction,-.91);
      pose.position.copy(end).addScaledVector(direction,-.117);
      pose.quaternion.setFromUnitVectors(up,direction);
      pose.scale.setScalar(1);
      pose.updateMatrix();
      arrowTransforms.push(pose.matrix.clone());
      heads.setColorAt(i,steelLink);
      linePoints.push(...start.toArray(),...pose.position.toArray());
      lineColors.push(...steelLink.toArray(),...steelLink.toArray());
      label(edge.verb.replaceAll("_"," "),start.clone().lerp(end,.45).add(new Vector3(0,.26,.05)),graphGroup,{edge});
    }
    const lineGeo = geometry(new LineSegmentsGeometry().setPositions(linePoints).setColors(lineColors));
    const lineMaterial = material(new LineMaterial({linewidth:1.75,vertexColors:true,color:0xffffff}));
    const lines = new LineSegments2(lineGeo,lineMaterial);
    lines.frustumCulled = false;
    graphGroup.add(lines);
    let visibleEdges = [];
    function positionEdges(visible) {
      visibleEdges = graph.edges.map((edge,index)=>({edge,index})).filter(({edge})=>visible.has(edge.source) && visible.has(edge.target));
      const starts = lineGeo.attributes.instanceStart, ends = lineGeo.attributes.instanceEnd;
      visibleEdges.forEach(({index},i)=>{
        heads.setMatrixAt(i,arrowTransforms[index]);
        starts.setXYZ(i,...linePoints.slice(index*6,index*6+3));
        ends.setXYZ(i,...linePoints.slice(index*6+3,index*6+6));
      });
      starts.data.needsUpdate = true;
      lineGeo.instanceCount = visibleEdges.length;
      lines.visible = visibleEdges.length > 0;
      updateBounds(heads,visibleEdges.length);
    }

    const notchPoints = [-.80,-.835,.54,-.59,-.835,.74,-.29,-.835,.74];
    const notchGeo = geometry(new BufferGeometry().setAttribute("position",new Float32BufferAttribute(notchPoints,3)));
    const notch = new Mesh(notchGeo,material(new MeshBasicMaterial({color:0x68e8f2,side:2})));
    notch.visible = false;
    graphGroup.add(notch);
    const light = new DirectionalLight(0xf1f9ff,2.65);
    light.position.set(-7,5.5,5);
    const rim = new DirectionalLight(0x83b7ff,.96);
    rim.position.set(5,1.25,-6);
    scene.add(light,rim,new HemisphereLight(0xc9e2ff,0x4a6597,.95));

    const point = new Vector3(), graphPoint = new Vector3();
    const prototypePick = new Vector3(...records.find(node=>node.originalKey==="Prototype").position)
      .add(new Vector3(0,-.54,.25));
    const ray = new Raycaster();
    ray.params.Line2 = {threshold:5};
    const pointers = new Map();
    let frame = null, press, draws = 0, ratio = 1, hydrated = false;
    let width = 0, height = 0, resourceKey;
    let filter = null, dirty = true, animateLinksAt = null, cameraMotion = null, paint = null;
    let dragMode = "orbit";

    function boundsPose(visible, direction) {
      if (!visible.length) return snapshot();
      const center = new Vector3();
      for (const {position} of visible) center.add(new Vector3(...position));
      center.divideScalar(visible.length);
      const right = up.clone().cross(direction).normalize();
      const vertical = direction.clone().cross(right);
      const tan = Math.tan(camera.fov*Math.PI/360);
      let distance = controls.minDistance;
      for (const {position} of visible) {
        for (const x of [-.95,.95]) for (const y of [-1.05,.98]) for (const z of [-.5,.5]) {
          const corner = new Vector3(...position).sub(center).add(new Vector3(x,y,z));
          distance = Math.max(distance,corner.dot(direction) + Math.max(
            Math.abs(corner.dot(right))/(tan*ratio*.89),Math.abs(corner.dot(vertical))/(tan*.89)));
        }
      }
      return {target:center.toArray(),position:center.clone().addScaledVector(direction,distance).toArray()};
    }

    function visibleRecords() { return records.filter(node=>shown().has(node.id)); }
    function snapshot() { return {position:camera.position.toArray(),target:controls.target.toArray()}; }
    function applyPose(next) {
      controls.target.fromArray(next.target);
      camera.position.fromArray(next.position);
      controls.update();
    }
    function curve(progress, x1, y1, x2, y2) {
      const bezier = (t,a,b) => 3*(1-t)**2*t*a + 3*(1-t)*t*t*b + t**3;
      let low = 0, high = 1;
      for (let i=0;i<12;i++) {
        const mid = (low+high)/2;
        if (bezier(mid,x1,x2) < progress) low=mid;
        else high=mid;
      }
      return bezier((low+high)/2,y1,y2);
    }
    function moveCamera(next,duration) {
      cancelMotion();
      if (motion.matches) applyPose(next);
      else {
        const offsets = [snapshot(),next].map(item=>new Vector3().fromArray(item.position).sub(new Vector3().fromArray(item.target)));
        const axes = offsets.map(item=>item.clone().normalize());
        const turn = new (camera.quaternion.constructor)().setFromUnitVectors(...axes);
        cameraMotion = {from:controls.target.clone(),to:new Vector3().fromArray(next.target),
          axis:axes[0],distances:offsets.map(item=>item.length()),turn,rotation:turn.clone(),
          duration,start:performance.now(), next};
        host.dataset.moving = "true";
      }
      invalidate();
    }
    function cancelMotion() { cameraMotion = null; delete host.dataset.moving; }
    function advanceCamera(now) {
      const step = cameraMotion;
      if (!step) return;
      const progress = Math.min(1,(now-step.start)/step.duration);
      if (progress>=1 || motion.matches) {
        applyPose(step.next);
        cancelMotion();
        return;
      }
      const eased = curve(Math.max(0,progress),.4,0,.2,1);
      controls.target.lerpVectors(step.from,step.to,eased);
      step.rotation.identity().slerp(step.turn,eased);
      camera.position.copy(step.axis).applyQuaternion(step.rotation)
        .multiplyScalar(step.distances[0]+(step.distances[1]-step.distances[0])*eased)
        .add(controls.target);
      controls.update();
    }

    function repaint(now) {
      const selected = selection();
      const relation = activeEdge();
      const identities = matches();
      const active = new Set(selected ? [selected] : []);
      for (const {edge} of visibleEdges) {
        if (edge.id===relation || edge.source===selected || edge.target===selected) {
          active.add(edge.source);
          active.add(edge.target);
        }
      }
      if (dirty) {
        for (const object of graphModels.batches) {
          object.userData.nodes.forEach((node,i)=>{
            const tint = active.has(node.id) || identities?.has(node.id) ? solidTint :
              identities ? backgroundTint : selected ? subduedTint : solidTint;
            object.setColorAt(i,tint);
          });
          if (object.instanceColor) object.instanceColor.needsUpdate = true;
        }
        notch.visible = filter.has(selected);
        if (notch.visible) {
          const [x,,z] = byId.get(selected).position;
          notch.position.set(x,0,z);
        }
        paint = {selected,relation,active,identities};
        dirty = false;
      }
      if (animateLinksAt===null) return;
      const progress = motion.matches ? 1 : Math.min(1,Math.max(0,(now-animateLinksAt)/140));
      const mix = progress>=1 ? 1 : curve(progress,.2,.8,.2,1);
      visibleEdges.forEach(({edge},i)=>{
        const incident = edge.source===selected || edge.target===selected;
        const tint = incident || relation===edge.id ? steelLink.clone().lerp(optical,mix)
          : relation ? backgroundLink : steelLink;
        heads.setColorAt(i,tint);
        lineGeo.attributes.instanceColorStart.setXYZ(i,tint.r,tint.g,tint.b);
        lineGeo.attributes.instanceColorEnd.setXYZ(i,tint.r,tint.g,tint.b);
      });
      if (heads.instanceColor) heads.instanceColor.needsUpdate = true;
      lineGeo.attributes.instanceColorStart.data.needsUpdate = true;
      if (progress>=1) animateLinksAt = null;
    }
    function setGraph(animate = false) {
      const visible = shown();
      if (filter!==visible) {
        filter = visible;
        positionModels(graphModels,filter);
        positionEdges(filter);
      }
      dirty = true;
      animateLinksAt = animate ? performance.now() : -1000;
      invalidate();
    }

    function paintLabels() {
      const {selected, relation, active, identities} = paint;
      const candidates = [];
      for (const item of labels) {
        if (!item.group.visible || item.id && item.group===graphGroup && !filter.has(item.id)) continue;
        const edge = item.edge;
        const related = edge && filter.has(edge.source) && filter.has(edge.target)
          && (edge.id===relation || edge.source===selected || edge.target===selected);
        if (edge && !related) continue;
        point.copy(item.position).project(camera);
        if (Math.abs(point.x)>.98 || Math.abs(point.y)>.98 || Math.abs(point.z)>1) continue;
        const x = (point.x+1)*width/2, y = (1-point.y)*height/2 + (item.edge ? 0 : 14);
        const textWidth = Math.min(width*.61,item.textLength*(width<600 ? 6.6 : 7.4)+26);
        const priority = item.id===selected ? 5 : edge?.id===relation ? 4
          : related || active.has(item.id) ? 3 : identities?.has(item.id) ? 2 : 1;
        candidates.push({item,x,y,textWidth,priority,depth:point.z});
      }
      candidates.sort((a,b)=>b.priority-a.priority || a.depth-b.depth);
      const boxes = [], visible = new Set();
      for (const {item,x,y,textWidth,priority} of candidates) {
        if (boxes.length>=(width<620 ? 6 : 12)) break;
        const cx = Math.max(textWidth/2+5,Math.min(width-textWidth/2-5,x));
        for (const offset of [0,24,-24]) {
          const cy = y+offset;
          const rect = [cx-textWidth/2-3,cy-21,cx+textWidth/2+3,cy+21];
          if (cy<20 || cy>height-20 || boxes.some(b=>rect[0]<b[2]&&rect[2]>b[0]&&rect[1]<b[3]&&rect[3]>b[1])) continue;
          boxes.push(rect);
          visible.add(item.tag);
          item.tag.classList.toggle("active",priority===5);
          item.tag.classList.toggle("match",Boolean(identities?.has(item.id)));
          const transform = `translate(${Math.round(cx)}px,${Math.round(cy)}px) translate(-50%,-50%)`;
          if (item.tag.style.transform!==transform) item.tag.style.transform=transform;
          break;
        }
      }
      for (const {tag} of labels) {
        const hidden = !visible.has(tag);
        if (tag.hidden !== hidden) tag.hidden = hidden;
      }
    }
    function draw(now) {
      frame = null;
      metrics.pending--;
      if (stopped || document.hidden) return;
      advanceCamera(now);
      if (dirty || animateLinksAt!==null) repaint(now);
      graphGroup.visible = !legendMode();
      legendGroup.visible = legendMode();
      renderer.render(scene,camera);
      host.dataset.draws = ++draws;
      const {triangles,calls} = renderer.info.render;
      if (Number(host.dataset.triangles)!==triangles) host.dataset.triangles = triangles;
      if (Number(host.dataset.calls)!==calls) host.dataset.calls = calls;
      host.dataset.distance = camera.position.distanceTo(controls.target).toFixed(4);
      host.dataset.pose = JSON.stringify(snapshot());
      const {geometries,textures} = renderer.info.memory;
      const programs = renderer.info.programs.length;
      const resources = [geometries,textures,programs,filter.size,visibleEdges.length].join(",");
      if (resources!==resourceKey) {
        resourceKey = resources;
        host.dataset.resources = JSON.stringify({geometries,textures,programs,
          materials:materialResources.size,instances:instances.size,nodes:filter.size,edges:visibleEdges.length});
      }
      metrics.draws++;
      paintLabels();
      graphPoint.copy(prototypePick).project(camera);
      host.dataset.pickX = (graphPoint.x+1)*width/2;
      host.dataset.pickY = (1-graphPoint.y)*height/2;
      if (cameraMotion || animateLinksAt!==null) invalidate();
    }
    function invalidate() {
      if (!stopped && !document.hidden && frame === null) {
        frame = requestAnimationFrame(draw);
        metrics.pending++;
      }
    }
    function cancel() {
      if (frame===null) return;
      cancelAnimationFrame(frame);
      frame=null;
      metrics.pending--;
    }
    function resize() {
      width = host.clientWidth;
      height = host.clientHeight;
      if (!width || !height) return;
      const cap = host.dataset.pixelMode === "low" ? 1 : width<=640 ? 1.25 : 1.5;
      const dpr = Math.min(devicePixelRatio,cap);
      if (renderer.getPixelRatio()!==dpr) renderer.setPixelRatio(dpr);
      host.dataset.dpr = dpr;
      renderer.setSize(width,height,false);
      lineMaterial.resolution.set(width,height);
      ratio=width/height;
      camera.aspect=ratio;
      camera.updateProjectionMatrix();
      if (!hydrated) {
        applyPose(legendMode() ? boundsPose(legend,legendDirection)
          : restoredPose ?? boundsPose(visibleRecords(),defaultDirection));
        hydrated=true;
      }
      invalidate();
    }

    cancelFrame = cancel;
    positionModels(legendModels,new Set());
    setGraph();
    observer = new ResizeObserver(resize);
    metrics.observers++;
    observer.observe(host);
    resize();
    controls.addEventListener("change",invalidate);
    releaseControls = () => controls.removeEventListener("change",invalidate);
    controls.addEventListener("start",cancelMotion);
    canvas.addEventListener("wheel",event=>event.stopImmediatePropagation(),{capture:true,passive:true,signal});
    canvas.addEventListener("pointerdown",event=>{
      if (event.button!==0) return;
      cancelMotion();
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      press = pointers.size===1 ? event.pointerId : null;
    },{signal});
    canvas.addEventListener("pointermove",event=>{
      const start = pointers.get(event.pointerId);
      if (start && Math.hypot(event.clientX-start.x,event.clientY-start.y)>6) press=null;
    },{signal});
    canvas.addEventListener("pointerup",event=>{
      pointers.delete(event.pointerId);
      if (event.pointerId!==press || legendMode()) return;
      press=null;
      const box=canvas.getBoundingClientRect();
      ray.setFromCamera(new Vector2(2*(event.clientX-box.left)/box.width-1,1-2*(event.clientY-box.top)/box.height),camera);
      const hit=ray.intersectObjects(graphModels.batches.filter(object=>object.visible),false)[0];
      if (hit) return select(hit.object.userData.nodes[hit.instanceId].id,canvas);
      const edgeHit = lines.visible && ray.intersectObject(lines,false).find(hit=>hit.faceIndex<visibleEdges.length);
      if (edgeHit) return inspect(visibleEdges[edgeHit.faceIndex].edge.id);
      select(null,canvas);
    },{signal});
    for (const end of ["pointercancel","lostpointercapture"]) canvas.addEventListener(end,event=>{
      pointers.delete(event.pointerId);
      if (press===event.pointerId) press=null;
    },{signal});
    canvas.addEventListener("webglcontextlost",event=>{
      event.preventDefault();
      metrics.losses++;
      onLoss();
    },{signal});
    document.addEventListener("visibilitychange",()=>{
      if (document.hidden) { cancel(); cancelMotion(); }
      else invalidate();
    },{signal});
    motion.addEventListener("change",invalidate,{signal});

    return {
      setGraph, resize, snapshot, cancelMotion,
      focus() {
        const selected = selection();
        if (!filter.has(selected)) return;
        const context = new Set([selected]);
        for (const {edge} of visibleEdges) {
          if (edge.source===selected) context.add(edge.target);
          if (edge.target===selected) context.add(edge.source);
        }
        // The desktop framing includes the two contextual neighbors in the approved Prototype view.
        if (ratio>=1.7 && byId.get(selected).originalKey==="Prototype") for (const {edge} of visibleEdges) {
          if (context.has(edge.target) && byId.get(edge.source).originalKey==="Interface Development") context.add(edge.source);
          if (context.has(edge.source) && byId.get(edge.target).originalKey==="design_references") context.add(edge.target);
        }
        const direction = camera.position.clone().sub(controls.target).normalize();
        moveCamera(boundsPose(records.filter(node=>context.has(node.id)),direction),300);
      },
      reset() {
        moveCamera(legendMode() ? boundsPose(legend,legendDirection) : boundsPose(visibleRecords(),defaultDirection),320);
      },
      changeView(restore) {
        cancelMotion();
        applyPose(legendMode() ? boundsPose(legend,legendDirection) : restore ?? boundsPose(visibleRecords(),defaultDirection));
        invalidate();
      },
      setControl(mode,touchSurface) {
        dragMode=mode;
        const pan=mode==="pan";
        controls.mouseButtons.LEFT = pan ? MOUSE.PAN : MOUSE.ROTATE;
        controls.touches.ONE = pan ? TOUCH.PAN : TOUCH.ROTATE;
        controls.enabled=touchSurface;
        canvas.style.touchAction=touchSurface ? "none" : "pan-y pinch-zoom";
      },
      step(direction) {
        cancelMotion();
        const offset=camera.position.clone().sub(controls.target);
        const angles={left:-1,right:1,up:-1,down:1};
        const horizontal=direction==="left" || direction==="right";
        if (dragMode==="pan") {
          const axis = new Vector3().setFromMatrixColumn(camera.matrixWorld,horizontal?0:1);
          const units=2*offset.length()*Math.tan(camera.fov*Math.PI/360)*.1*(horizontal?ratio:1);
          axis.multiplyScalar(units*angles[direction]*(horizontal?1:-1));
          camera.position.add(axis);
          controls.target.add(axis);
        } else {
          const axis = horizontal ? up : new Vector3().setFromMatrixColumn(camera.matrixWorld,0);
          offset.applyAxisAngle(axis,Math.PI/12*angles[direction]*(horizontal?-1:1));
          camera.position.copy(controls.target).add(offset);
        }
        controls.update();
        invalidate();
      },
      zoom(factor) {
        cancelMotion();
        const offset=camera.position.clone().sub(controls.target);
        offset.setLength(Math.min(controls.maxDistance,Math.max(controls.minDistance,offset.length()*factor)));
        camera.position.copy(controls.target).add(offset);
        controls.update();
        invalidate();
      },
      stop,
    };
  } catch (error) {
    stop();
    throw error;
  }
}
