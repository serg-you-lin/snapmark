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
from dataclasses import dataclass, field
from typing import Optional


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
    

def ref_angle_and_pivot(ref_segment):
    """
    Estrae angolo e pivot da un VirtualSegment di riferimento.

    Args:
        ref_segment: VirtualSegment (o qualsiasi oggetto con .dxf.start e .dxf.end)

    Returns:
        Tupla (angle, pivot) dove:
            angle: float in radianti
            pivot: tupla (x, y)
    """
    p1 = (ref_segment.dxf.start.x, ref_segment.dxf.start.y)
    p2 = (ref_segment.dxf.end.x, ref_segment.dxf.end.y)
    return seg_angle(p1, p2), p1


##############################################################################
# Rotazione della sequenza NS in coordinate reali
##############################################################################

def rotate_ns_sequence(sequence, pivot, angle):
    """
    Ruota tutti i punti di una sequenza NS attorno a un pivot.

    Chiamato dopo place_sequence per riportare la sequenza trovata
    in coordinate locali nelle coordinate reali del disegno.

    La rotazione avviene su due livelli:
    - position: il punto di ancoraggio del carattere nel disegno
    - scaled_segments: i punti dei segmenti del glifo, ruotati
      attorno all'origine (0,0) perché sono già relativi a position

    Args:
        sequence: Oggetto NS con .sequence lista di (scaled_segments, position)
        pivot: Tupla (x, y) attorno a cui ruotare
        angle: Angolo in radianti

    Returns:
        La stessa sequenza NS modificata in-place (per coerenza con place_sequence)
    """
    for scaled_segments, position in sequence.sequence:
        # ruota il punto di ancoraggio nel disegno
        rx, ry = rotate_point(position, pivot, angle)
        position[0], position[1] = rx, ry

        # ruota i punti del glifo attorno all'origine —
        # sono coordinate relative, il pivot è (0, 0)
        for point in scaled_segments:
            px, py = rotate_point((point[0], point[1]), (0.0, 0.0), angle)
            point[0], point[1] = px, py

    return sequence