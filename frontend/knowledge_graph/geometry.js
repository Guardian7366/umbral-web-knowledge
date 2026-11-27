import {ExtrudeGeometry, Float32BufferAttribute, MeshBasicMaterial, MeshPhongMaterial, Path, Shape} from "three";

export const families = ["Department", "Knowledge group", "Document", "Concept", "Project example"];

function contour(path, points) {
  path.moveTo(...points[0]);
  for (const point of points.slice(1)) path.lineTo(...point);
  path.closePath();
  return path;
}

function solid(points, {depth, bevel = .028, hole, offset = [0, 0, 0]}) {
  const shape = contour(new Shape(), points);
  if (hole) shape.holes.push(contour(new Path(), hole));
  const geometry = new ExtrudeGeometry(shape, {
    depth, steps:1, bevelEnabled:bevel > 0, bevelThickness:bevel,
    bevelSize:bevel, bevelSegments:1, curveSegments:1,
  });
  geometry.translate(...offset);
  return geometry;
}

const silhouettes = {
  department:[[-.73,-.65],[.73,-.65],[.73,.66],[.36,.66],[.36,-.20],[-.36,-.20],[-.36,.66],[-.73,.66]],
  group:[[-.79,-.57],[.79,-.57],[.79,.25],[.06,.25],[-.13,.60],[-.62,.60],[-.72,.25],[-.79,.25]],
  sheet:[[-.62,-.72],[.51,-.72],[.64,-.54],[.43,-.54],[.64,-.36],[.64,.55],[.49,.70],[-.62,.70]],
  triangle:[[-.83,-.60],[.83,-.60],[0,.87]],
  aperture:[[-.40,-.37],[0,.37],[.40,-.37]],
  project:[[-.76,-.59],[.76,-.59],[.76,.28],[.48,.58],[-.48,.58],[-.76,.28]],
};

function metalFinish(geometry) {
  const {position,normal} = geometry.attributes;
  const colors = [];
  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i), y = position.getY(i), z = normal.getZ(i);
    const face = .87 + .13 * y - .19 * x;
    const polish = Math.max(0, z) ** 2;
    if (Math.abs(z) > .98) colors.push(face, face * 1.015, face * 1.035);
    else colors.push(.83 + 2.9 * polish, .91 + 1.45 * polish, 1 + .48 * polish);
  }
  geometry.setAttribute("color", new Float32BufferAttribute(colors, 3));
}

export function buildFamilies(geometries, materials) {
  const phong = (color, specular, shininess) => {
    const material = new MeshPhongMaterial({color, specular, shininess, vertexColors:true});
    materials.add(material);
    return material;
  };
  const steel = phong(0x7298bd, 0xa8c5e4, 38);
  const pale = phong(0xc8deee, 0x9ab8d2, 54);
  const paper = phong(0xe5f0fa, 0x5c738b, 22);
  const project = phong(0x9fc5d9, 0x8aacc2, 45);
  const structural = phong(0x34588f, 0x82a9d4, 69);
  const edge = new MeshBasicMaterial({color:0x68e8f2});
  materials.add(edge);
  const part = (points, settings, material) => {
    const geometry = solid(points, settings);
    if (Array.isArray(material)) metalFinish(geometry);
    geometries.add(geometry);
    return {geometry, material};
  };

  return new Map([
    ["Department", [
      part(silhouettes.department, {depth:.38, offset:[0,0,-.21]}, [steel, structural]),
    ]],
    ["Knowledge group", [
      part(silhouettes.group, {depth:.29, offset:[0,0,-.15]}, [pale, structural]),
    ]],
    ["Document", [
      part(silhouettes.sheet, {depth:.13, offset:[.095,.078,-.215]}, [structural, structural]),
      part(silhouettes.sheet, {depth:.138, offset:[0,0,-.02]}, [paper, structural]),
      part([[-.56,.548],[-.15,.548],[-.045,.631],[-.106,.631],[-.18,.581],[-.56,.581]],
        {depth:.007, bevel:0, offset:[0,0,.148]}, edge),
    ]],
    ["Concept", [
      part(silhouettes.triangle, {depth:.41, hole:silhouettes.aperture, offset:[0,0,-.23]}, [pale, structural]),
      part([[-.76,-.565],[-.55,-.565],[-.48,-.443],[-.517,-.443],[-.566,-.534],[-.742,-.534]],
        {depth:.01, bevel:0, offset:[0,0,.210]}, edge),
    ]],
    ["Project example", [
      part(silhouettes.project, {depth:.44, bevel:.045, offset:[0,0,-.24]}, [project, structural]),
    ]],
  ]);
}
