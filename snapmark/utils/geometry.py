"""
snapmark/utils/geometry.py

Primitive geometriche condivise tra i moduli di snapmark.

Contiene:
- Rotazione di punti, segmenti, entità DXF
- VirtualSegment: astrazione per trattare segmenti di LWPOLYLINE
  come LINE reali (stessa interfaccia .dxf.start / .dxf.end)
- Funzioni per estrarre e ruotare segmenti da LWPOLYLINE
- Funzioni per trovare l'entità più lunga nel modelspace
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from ezdxf.math import bulge_to_arc


##############################################################################
# Rotazione di punti e segmenti
##############################################################################

def rotate_point(point, pivot, angle):
    """
    Ruota un punto attorno a un pivot di un angolo in radianti.

    Args:
        point: Tupla (x, y) o oggetto con attributi .x e .y
        pivot: Tupla (x, y) del punto attorno a cui ruotare
        angle: Angolo in radianti

    Returns:
        Tupla (x, y) del punto ruotato
    """
    # accetta sia tuple che oggetti ezdxf con .x .y
    px = point[0] if hasattr(point, '__getitem__') else point.x
    py = point[1] if hasattr(point, '__getitem__') else point.y

    rx = pivot[0] + (px - pivot[0]) * math.cos(angle) - (py - pivot[1]) * math.sin(angle)
    ry = pivot[1] + (px - pivot[0]) * math.sin(angle) + (py - pivot[1]) * math.cos(angle)
    return rx, ry


def rotate_segs(segs, pivot, angle):
    """
    Ruota una lista di segmenti (x1, y1, x2, y2) attorno a un pivot.

    Usato per portare i segmenti del disegno in coordinate locali
    rispetto all'entità di riferimento prima di cercare spazio
    per la sequenza.

    Args:
        segs: Lista di tuple (x1, y1, x2, y2)
        pivot: Tupla (x, y) del punto di rotazione
        angle: Angolo in radianti

    Returns:
        Lista di tuple (x1, y1, x2, y2) ruotate
    """
    rotated = []
    for (x1, y1, x2, y2) in segs:
        rx1, ry1 = rotate_point((x1, y1), pivot, angle)
        rx2, ry2 = rotate_point((x2, y2), pivot, angle)
        rotated.append((rx1, ry1, rx2, ry2))
    return rotated


def seg_length(p1, p2):
    """
    Lunghezza euclidea tra due punti.

    Args:
        p1, p2: Tuple (x, y) o oggetti con __getitem__

    Returns:
        float: distanza tra i due punti
    """
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def seg_angle(p1, p2):
    """
    Angolo in radianti del segmento p1->p2 rispetto all'asse X.
    Normalizza sempre verso destra (deltaX >= 0) per coerenza
    con comp_inclination in aligner.py.

    Args:
        p1, p2: Tuple (x, y)

    Returns:
        float: angolo in radianti
    """
    if p2[0] >= p1[0]:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    else:
        dx, dy = p1[0] - p2[0], p1[1] - p2[1]
    return math.atan2(dy, dx)


##############################################################################
# VirtualSegment
##############################################################################

@dataclass
class _Point:
    x: float
    y: float


@dataclass
class _Dxf:
    start: _Point
    end: _Point


@dataclass
class VirtualSegment:
    """
    Segmento virtuale estratto da una LWPOLYLINE, solo per calcoli geometrici.

    Imita l'interfaccia .dxf.start / .dxf.end delle LINE reali in modo che
    find_longer_entity, comp_inclination e get_pivot_point in aligner.py
    non richiedano nessuna modifica.

    Il bulge viene ignorato: per trovare il lato più lungo la corda è sufficiente.

    Attributes:
        dxf: Oggetto con .start e .end, ognuno con .x e .y
        source_entity: Riferimento alla LWPOLYLINE originale,
                       necessario per ruotarla dopo aver trovato il lato di riferimento.
    """
    dxf: _Dxf
    source_entity: object = field(default=None, repr=False)

    def __init__(self, x1: float, y1: float, x2: float, y2: float, source_entity=None):
        self.dxf = _Dxf(start=_Point(x1, y1), end=_Point(x2, y2))
        self.source_entity = source_entity


##############################################################################
# Estrazione segmenti virtuali da LWPOLYLINE
##############################################################################

def lwpolylines_to_virtual_segments(lwpolylines):
    """
    Estrae tutti i segmenti virtuali da una lista di LWPOLYLINE.

    Ogni segmento porta un riferimento alla LWPOLYLINE originale
    tramite source_entity, in modo che dopo aver individuato il
    segmento più lungo si possa risalire all'entità da ruotare.

    Args:
        lwpolylines: Lista di entità LWPOLYLINE ezdxf

    Returns:
        Lista di VirtualSegment
    """
    segments = []
    for lwpoly in lwpolylines:
        points = list(lwpoly.get_points(format='xy'))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            segments.append(VirtualSegment(x1, y1, x2, y2, source_entity=lwpoly))

        # se è chiusa, aggiungi il segmento che richiude il perimetro
        if lwpoly.closed and len(points) >= 2:
            x1, y1 = points[-1]
            x2, y2 = points[0]
            segments.append(VirtualSegment(x1, y1, x2, y2, source_entity=lwpoly))

    return segments


##############################################################################
# Ricerca dell'entità di riferimento nel modelspace
##############################################################################


def find_longer_entity(entities):
    """
    Finds the longest entity among the given entities and checks if it is below a certain minimum point.
    
    Args:
        entities: A list of entities to evaluate.
    
    Returns:
        A tuple containing the longest entity and a boolean indicating if it is below the minimum point.
    """
    
    longest_side = None
    longest_side_length = 0
    longest_side_is_below = True
    minimum_point = float('inf')
    
    # Iterate through all the lines in the model
    for entity in entities:
        minimum_point = min(entity.dxf.start.y, entity.dxf.end.y, minimum_point)      
        # Calculate the length of the line using the Pythagorean theorem
        length = ((entity.dxf.start.x - entity.dxf.end.x) ** 2 + (entity.dxf.start.y - entity.dxf.end.y) ** 2) ** 0.5
        # If the length of the line is greater than the maximum length found so far, update it
        if length > longest_side_length:
            longest_side_length = length
            longest_side = entity
    
    # Check if the longest side is a perimeter line
    if min(longest_side.dxf.start.y, longest_side.dxf.end.y) > minimum_point:
        longest_side_is_below = False
    
    return longest_side, longest_side_is_below


def find_reference_entity(lines, lwpolylines, horizontal_threshold_deg=5.0):
    """
    Trova il segmento di riferimento per il posizionamento della sequenza.

    Strategia:
        1. Estrae tutti i segmenti (LINE reali + segmenti virtuali da LWPOLYLINE)
        2. Filtra quelli sufficientemente orizzontali (angolo < threshold)
        3. Tra quelli orizzontali, prende il più basso (min y)
        4. Fallback: nessun orizzontale → segmento con il vertice y più basso
           tra tutti; a parità di y, il più orizzontale dei due.

    Args:
        lines: Lista di entità LINE ezdxf
        lwpolylines: Lista di entità LWPOLYLINE ezdxf
        horizontal_threshold_deg: Soglia in gradi sotto cui un segmento
                                  è considerato orizzontale (default 5°)

    Returns:
        VirtualSegment del segmento scelto, oppure None se il modelspace è vuoto
    """
    threshold_rad = math.radians(horizontal_threshold_deg)

    all_segments = []
    for line in lines:
        p1 = (line.dxf.start.x, line.dxf.start.y)
        p2 = (line.dxf.end.x, line.dxf.end.y)
        all_segments.append(VirtualSegment(p1[0], p1[1], p2[0], p2[1]))
    all_segments.extend(lwpolylines_to_virtual_segments(lwpolylines))

    if not all_segments:
        return None

    def _angle(seg):
        return abs(seg_angle(
            (seg.dxf.start.x, seg.dxf.start.y),
            (seg.dxf.end.x, seg.dxf.end.y)
        ))

    def _min_y(seg):
        return min(seg.dxf.start.y, seg.dxf.end.y)

    horizontal = [seg for seg in all_segments if _angle(seg) < threshold_rad]

    if horizontal:
        return min(horizontal, key=_min_y)
    else:
        # fallback: ordina per y più bassa, a parità di y il più orizzontale
        return min(all_segments, key=lambda s: (_min_y(s), _angle(s)))
    

def comp_centroid(vertex):
    """Calculates the centroid of a given set of vertices."""
    num_vertex = len(vertex)
    sum_x = np.sum(vertex[:, 0])
    sum_y = np.sum(vertex[:, 1])
    centroid_x = sum_x / num_vertex
    centroid_y = sum_y / num_vertex
    return (centroid_x, centroid_y)


def lwpolyline_to_segs(entity, min_arc_segs=15):
    """
    Converts a LWPOLYLINE into a list of segments (x1, y1, x2, y2).
    Correctly handles bulge values by discretizing arcs.

    Args:
        entity: ezdxf LWPOLYLINE entity.
        min_arc_segs: Minimum number of segments used to discretize an arc.

    Returns:
        List of tuples (x1, y1, x2, y2).
    """
    segs = []
    verts = list(entity.get_points(format='xyseb'))
    
    if len(verts) < 2:
        return segs
    
    pairs = list(zip(verts, verts[1:]))
    if entity.closed:
        pairs.append((verts[-1], verts[0]))
    
    for v1, v2 in pairs:
        x1, y1, _, _, bulge = v1
        x2, y2 = v2[0], v2[1]
        
        if abs(bulge) < 1e-6:
            segs.append((x1, y1, x2, y2))
        else:
            center, start_angle, end_angle, radius = bulge_to_arc(
                (x1, y1), (x2, y2), bulge
            )
            if start_angle > end_angle:
                end_angle += 2 * math.pi
            
            num_segs = max(min_arc_segs, int(min_arc_segs + (radius // 2) *
                          (end_angle - start_angle) / (2 * math.pi)))
            
            angles = np.linspace(start_angle, end_angle, num_segs + 1)
            cx, cy = center.x, center.y
            pts = [(cx + radius * math.cos(a),
                    cy + radius * math.sin(a)) for a in angles]
            
            for p1, p2 in zip(pts, pts[1:]):
                segs.append((p1[0], p1[1], p2[0], p2[1]))
    
    return segs