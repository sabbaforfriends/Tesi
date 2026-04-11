import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from .Bin import Bin
from .Item import Item
from .Space import Volume, Vector3

# Configurazione Bordi per la Tesi
BORDER_WIDTH = 3  # Bordi spessi e netti
BORDER_COLOR = "black"
TRANSPARENCY = 0.6

def get_priority_color(priority: int, min_p=0, max_p=10) -> str:
    """Mappa la priorità su un gradient Verde-Giallo-Rosso"""
    p = max(min_p, min(max_p, priority))
    range_p = max_p - min_p
    ratio = (p - min_p) / range_p if range_p != 0 else 0
    
    if ratio < 0.5:
        # Da Verde a Giallo
        r = int(510 * ratio)
        g = 255
        b = 0
    else:
        # Da Giallo a Rosso
        r = 255
        g = int(510 * (1 - ratio))
        b = 0
    return f'rgb({r}, {g}, {b})'

def render_volume_interactive(volume: Volume, fig: go.Figure, color: str, name: str = "", 
                              show_border: bool = True, border_width: float = BORDER_WIDTH, 
                              border_color: str = BORDER_COLOR, transparency: float = TRANSPARENCY):   
    """Disegna il volume con i bordi delineati richiesti"""
    x, y, z = [float(v) for v in volume.position]
    w, h, d = [float(v) for v in volume.size]

    # Faccie dell'oggetto
    fig.add_trace(go.Mesh3d(
        x=[x, x, x+w, x+w, x, x, x+w, x+w],
        y=[y, y+h, y+h, y, y, y+h, y+h, y],
        z=[z, z, z, z, z+d, z+d, z+d, z+d],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        opacity=transparency,
        color=color,
        name=name,
        flatshading=True
    ))

    if show_border:
        # Linee nere per definire i bordi (wireframe)
        x_l = [x, x+w, x+w, x, x, None, x, x+w, x+w, x, x, None, x, x, None, x+w, x+w, None, x+w, x+w, None, x, x]
        y_l = [y, y, y+h, y+h, y, None, y, y, y+h, y+h, y, None, y, y+h, None, y+h, y, None, y, y+h, None, y+h, y]
        z_l = [z, z, z, z, z, None, z+d, z+d, z+d, z+d, z+d, None, z, z, None, z, z, None, z+d, z+d, None, z+d, z+d]
        
        fig.add_trace(go.Scatter3d(
            x=x_l, y=y_l, z=z_l, mode='lines',
            line=dict(color=border_color, width=border_width),
            showlegend=False, hoverinfo='none'
        ))

def render_bin_interactive(bin: Bin):
    """Funzione principale chiamata dai tuoi test"""
    fig = go.Figure()
    
    # Determina il range di priorità presenti per scalare i colori correttamente
    priorities = [item.priority for item in bin.items] if bin.items else [0]
    min_p, max_p = min(priorities), max(priorities)
    if min_p == max_p: max_p = min_p + 1 # Evita divisione per zero

    for item in bin.items:
        # Qui forziamo il colore basato sulla priorità invece che random
        p_color = get_priority_color(item.priority, min_p, max_p)
        
        render_volume_interactive(
            item.volume, 
            fig, 
            color=p_color, 
            name=f"ID:{item.name} P:{item.priority} W:{item.weight}kg"
        )

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Width (X)', range=[0, float(bin.width)]),
            yaxis=dict(title='Height (Y)', range=[0, float(bin.height)]),
            zaxis=dict(title='Depth (Z)', range=[0, float(bin.depth)]),
            aspectmode='data'
        ),
        title=f"Analisi Carico: {bin.name} (Verde=Priorità Bassa, Rosso=Alta)"
    )
    fig.show()

# --- Funzioni di compatibilità per evitare ImportError ---

def render_volume(volume: Volume, ax, color: str = "cyan", border_color: str = "black", alpha: float = 0.5):
    """Necessaria per l'import in __init__.py"""
    x, y, z = [float(v) for v in volume.position]
    w, h, d = [float(v) for v in volume.size]
    vertices = [[x,y,z], [x+w,y,z], [x+w,y+h,z], [x,y+h,z], [x,y,z+d], [x+w,y,z+d], [x+w,y+h,z+d], [x,y+h,z+d]]
    faces = [[vertices[0],vertices[1],vertices[5],vertices[4]], [vertices[7],vertices[6],vertices[2],vertices[3]], [vertices[0],vertices[4],vertices[7],vertices[3]], [vertices[1],vertices[5],vertices[6],vertices[2]], [vertices[4],vertices[5],vertices[6],vertices[7]], [vertices[0],vertices[1],vertices[2],vertices[3]]]
    ax.add_collection3d(Poly3DCollection(faces, facecolors=color, edgecolors=border_color, alpha=alpha))

def render_bin(bin: Bin, **kwargs):
    """Fallback su matplotlib se necessario"""
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for item in bin.items:
        render_volume(item.volume, ax)
    plt.show()