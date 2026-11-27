import pathlib
import os
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.path import Path

# ============================================================
# 1. GRAPH STRUCTURE
# ============================================================

G = nx.DiGraph()

# Node definitions:
# (x, y, width, height, fill_color, border_color, text_color)

nodes = {
    # Organization
    "Interface Development": (134, 77, 185, 58, "#E6C900", "#B89F00", "black"),
    "Design and UX": (134, 201, 185, 58, "green", "#006600", "white"),
    "Creative Direction": (134, 526, 185, 58, "#ED1000", "#C00000", "white"),
    "Project Management": (134, 640, 185, 58, "#159FDC", "#0079B5", "white"),

    # Design references
    "design_references": (478, 201, 185, 57, "#FFE5C6", "#E89000", "black"),
    "UW01": (478, 268, 185, 38, "white", "black", "black"),
    "UW02": (478, 335, 185, 38, "white", "black", "black"),
    "UW03": (478, 402, 185, 38, "white", "black", "black"),

    # Creative methods
    "creative_methods": (478, 526, 185, 57, "#E4D6E9", "#A47AB5", "black"),
    "UW04": (478, 593, 185, 38, "white", "black", "black"),
    "UW05": (478, 660, 185, 38, "white", "black", "black"),
    "UW06": (478, 727, 185, 38, "white", "black", "black"),

    # Project learnings
    "project_learnings": (478, 836, 185, 57, "#D9E7FC", "#6A94D6", "black"),
    "UW07": (478, 903, 185, 48, "white", "black", "black"),
    "UW08": (478, 970, 185, 48, "white", "black", "black"),
    "UW09": (478, 1037, 185, 48, "white", "black", "black"),

    # Design domain concepts
    "Prototype": (966, 188, 185, 58, "white", "black", "black"),
    "Reusable Components": (1229, 188, 185, 58, "white", "black", "black"),
    "Visual Hierarchy": (966, 268, 185, 58, "white", "black", "black"),
    "Responsiveness": (966, 335, 185, 58, "white", "black", "black"),
    "Module Composition": (966, 402, 185, 58, "white", "black", "black"),

    "Ideation": (966, 593, 185, 50, "white", "black", "black"),
    "Visual Proposal Evaluation": (966, 660, 185, 58, "white", "black", "black"),
    "Concept Selection": (966, 727, 185, 58, "white", "black", "black"),

    # Project examples
    "Aula Clara Project": (903, 903, 185, 58, "white", "black", "black"),
    "Estudio Norte Project": (903, 970, 185, 58, "white", "black", "black"),
    "Mesa Abierta Project": (903, 1037, 185, 58, "white", "black", "black"),
}

for name in nodes:
    G.add_node(name)


# ============================================================
# 2. RELATIONSHIPS
# ============================================================

# Each edge:
# (source, target, relationship, color, route_points, label_position)

edges = [
    # Organization -> knowledge groups
    ("Design and UX", "design_references", "stores", "green",
     [(215, 201), (397, 201)], (305, 193)),

    ("Creative Direction", "creative_methods", "stores", "#D00000",
     [(215, 526), (397, 526)], (301, 518)),

    ("Project Management", "project_learnings", "stores", "#007ACC",
     [(215, 640), (305, 640), (305, 836), (397, 836)],
     (307, 732)),

    # Organization -> design domain concepts
    ("Design and UX", "Prototype", "creates", "darkgreen",
     [(215, 201), (286, 201), (286, 114), (966, 114), (966, 159)],
     (578, 114)),

    ("Interface Development", "Reusable Components", "implements", "#B59A00",
     [(215, 77), (1229, 77), (1229, 159)],
     (639, 77)),

    # Design references -> concepts
    ("UW01", "Visual Hierarchy", "describes", "black",
     [(559, 268), (884, 268)], (724, 260)),

    ("UW02", "Responsiveness", "describes", "black",
     [(559, 335), (884, 335)], (724, 327)),

    ("UW03", "Module Composition", "describes", "black",
     [(559, 402), (884, 402)], (724, 394)),

    # Prototype -> reusable components
    ("Prototype", "Reusable Components", "generates", "black",
     [(1047, 188), (1148, 188)], (1098, 180)),

    # Creative methods -> concepts
    ("UW04", "Ideation", "documents_methods_for", "black",
     [(559, 593), (884, 593)], (724, 585)),

    ("UW05", "Visual Proposal Evaluation", "documents_methods_for", "black",
     [(559, 660), (884, 660)], (724, 652)),

    ("UW06", "Concept Selection", "documents_methods_for", "black",
     [(559, 727), (884, 727)], (724, 719)),

    # Project learnings -> project examples
    ("UW07", "Aula Clara Project", "documents_closure_of", "black",
     [(559, 903), (822, 903)], (694, 895)),

    ("UW08", "Estudio Norte Project", "documents_closure_of", "black",
     [(559, 970), (822, 970)], (694, 962)),

    ("UW09", "Mesa Abierta Project", "documents_closure_of", "black",
     [(559, 1037), (822, 1037)], (694, 1029)),
]

for source, target, label, color, route, label_pos in edges:
    G.add_edge(source, target, label=label, color=color,
               route=route, label_pos=label_pos)


# ============================================================
# 3. FIGURE AND CONTAINERS
# ============================================================

fig, ax = plt.subplots(figsize=(16, 13))

ax.set_xlim(0, 1350)
ax.set_ylim(1120, 0)
ax.set_aspect("equal")
ax.axis("off")

# Container helper
def draw_container(x, y, width, height, linewidth=0.9):
    rect = Rectangle(
        (x, y), width, height,
        facecolor="none",
        edgecolor="#222222",
        linewidth=linewidth,
        zorder=0
    )
    ax.add_patch(rect)


# Organization container
draw_container(20, 20, 229, 697)

# Knowledge groups
draw_container(363, 153, 230, 297)
draw_container(363, 488, 230, 277)
draw_container(363, 793, 230, 306)

# Design domain concepts
draw_container(851, 134, 478, 640)

# Container titles
ax.text(
    134, 370, "Organization",
    ha="center", va="center",
    fontsize=17, fontweight="bold"
)

ax.text(
    1307, 735, "Design Domain\nConcepts",
    ha="right", va="center",
    fontsize=12, fontweight="bold"
)


# ============================================================
# 4. DRAW ORTHOGONAL EDGES
# ============================================================

def draw_orthogonal_edge(route, color="black", linewidth=1.5):
    """
    Draw an edge through manually specified horizontal/vertical
    route points, with an arrowhead at its destination.
    """
    vertices = route
    codes = [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1)

    path = Path(vertices, codes)

    arrow = FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=13,
        color=color,
        linewidth=linewidth,
        shrinkA=0,
        shrinkB=0,
        zorder=2
    )
    ax.add_patch(arrow)


# Draw edges before nodes
for source, target, data in G.edges(data=True):

    draw_orthogonal_edge(
        data["route"],
        color=data["color"],
        linewidth=1.6
    )

    # Relationship labels
    lx, ly = data["label_pos"]

    ax.text(
        lx, ly,
        data["label"],
        ha="center",
        va="center",
        fontsize=7.5,
        color="black",
        bbox=dict(
            facecolor="#D9D7FF",
            edgecolor="none",
            pad=0.5
        ),
        zorder=4
    )


# ============================================================
# 5. DRAW NODES
# ============================================================

def draw_node(name, data):
    x, y, width, height, fill, border, text_color = data

    # Node center coordinates are converted to bottom-left
    # coordinates for FancyBboxPatch.
    rect = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.01,rounding_size=10",
        facecolor=fill,
        edgecolor=border,
        linewidth=0.9,
        zorder=5
    )

    ax.add_patch(rect)

    ax.text(
        x, y,
        name,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold" if name in [
            "Interface Development",
            "Design and UX",
            "Creative Direction",
            "Project Management"
        ] else "normal",
        color=text_color,
        zorder=6
    )


for name, data in nodes.items():
    draw_node(name, data)


# ============================================================
# 6. INTERNAL GROUP CONNECTIONS
# ============================================================

# These lines connect each knowledge category to its units.
# They are drawn behind the nodes.

internal_connections = [
    (478, 229, 478, 249, "#E89000"),
    (478, 287, 478, 316, "#E89000"),
    (478, 354, 478, 383, "#E89000"),

    (478, 554, 478, 574, "#A47AB5"),
    (478, 612, 478, 641, "#A47AB5"),
    (478, 679, 478, 708, "#A47AB5"),

    (478, 864, 478, 879, "#6A94D6"),
    (478, 927, 478, 946, "#6A94D6"),
    (478, 994, 478, 1013, "#6A94D6"),
]

for x1, y1, x2, y2, color in internal_connections:
    ax.plot(
        [x1, x2], [y1, y2],
        color=color,
        linewidth=1,
        zorder=1
    )


# ============================================================
# 7. EXPORT
# ============================================================

repo = pathlib.Path(__file__).resolve().parent.parent
directory = os.path.join(repo, "evidences", "graph")
os.makedirs(directory, exist_ok=True)
file = os.path.join(directory, "GraphNetworkx.png")
plt.savefig(
    file,
    dpi=200,
    bbox_inches="tight",
    facecolor="white"
)

plt.show()
