#!/usr/bin/env python3
import time
import math
from decimal import Decimal
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Tuple
from random import random,randint,gauss
from collections import Counter
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import argparse
import csv


from py3dbl import (
    Bin, BinModel, Packer, Item, Volume, Vector3,
    constraints, item_generator, render
)
from py3dbl.render import get_priority_color
from py3dbl.Packer import calculate_moves_v5

# ============================================================================
# CONFIGURAZIONE
# ============================================================================
FURGONE = BinModel(name="Furgone Ducato L3H2", size=(1.67, 2, 3.10), max_weight=1400)
ITEM_CONFIG = {"width": (0.30, 0.55), "height": (0.30, 0.50), "depth": (0.30, 0.70), "weight": (5, 25), "priority_range": (1, 10)}
NUM_ITEMS = 60 #(-n)
CORRIDOR_WIDTH_PCT = 0.2 #(-w)
RESULTS_DIR = Path("results_simulation_final")
RESULTS_DIR.mkdir(exist_ok=True)


# ============================================================================
# RENDERING SOLIDO 
# ============================================================================

def create_box_traces(it, moves_count):
    x, y, z = float(it.position.x), float(it.position.y), float(it.position.z)
    w, h, d = float(it.width), float(it.height), float(it.depth)
    
    # Mapping Plotly: X=Larghezza, Y=Profondità, Z=Altezza
    vx = [x, x+w, x+w, x, x, x+w, x+w, x]
    vy = [z, z, z+d, z+d, z, z, z+d, z+d] # Y as Depth
    vz = [y, y, y, y, y+h, y+h, y+h, y+h] # Z as Height

    mesh = go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=[0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3], j=[1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4], k=[2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7],
        opacity=0.7, color=get_priority_color(it.priority, 1, 10),
        flatshading=True, name=f"Pacco {it.name}",
        text=f"ID:{it.name}<br>Priorità:{it.priority}<br>Mosse:{moves_count}", hoverinfo="text"
    )

    lx = [x, x+w, x+w, x, x, None, x, x+w, x+w, x, x, None, x, x, None, x+w, x+w, None, x+w, x+w, None, x, x]
    ly = [z, z, z+d, z+d, z, None, z, z, z+d, z+d, z, None, z, z, None, z, z, None, z+d, z+d, None, z+d, z+d]
    lz = [y, y, y, y, y, None, y+h, y+h, y+h, y+h, y+h, None, y, y+h, None, y+h, y, None, y, y+h, None, y+h, y]

    wire = go.Scatter3d(x=lx, y=ly, z=lz, mode='lines', line=dict(color='black', width=2), hoverinfo='none', showlegend=False)
    return mesh, wire

def run_comparison():
    print("\nAVVIO SIMULAZIONE")
    items = item_generator(**ITEM_CONFIG, batch_size=NUM_ITEMS)
    results_data = []
    
    for use_corridor in [False, True]:
        name = "CON CORRIDOIO" if use_corridor else "SENZA CORRIDOIO"
        p = Packer(); p.set_default_bin(FURGONE)
        p.add_batch([Item(it.name, Volume(Vector3(*it.dimensions)), it.weight, it.priority) for it in items])
        c_list = [
            constraints['weight_within_limit'], 
            constraints['fits_inside_bin'], 
            constraints['no_overlap'], 
            constraints['is_supported']
            ]
        if use_corridor: 
            c_corr = constraints['central_corridor_accessibility']
            c_corr.set_parameter('corridor_width_percent', CORRIDOR_WIDTH_PCT)
            c_list.append(c_corr)
        else: 
            c_list.append(constraints['maintain_center_of_gravity'])
        
        p.pack(constraints=c_list, strategy='multi_anchor')
        
        bin0 = p.current_configuration[0]
        moves_map = calculate_moves_v5(bin0, use_corridor, CORRIDOR_WIDTH_PCT)
        
        fig = go.Figure()

        # --- TRACCE FANTASMA (Per bloccare le proporzioni e lo schiacciamento) ---
        # Aggiungiamo due punti invisibili agli angoli estremi del furgone
        fig.add_trace(go.Scatter3d(
            x=[0, float(bin0.width)], y=[0, float(bin0.depth)], z=[0, float(bin0.height)],
            mode='markers', marker=dict(size=0, opacity=0), showlegend=False, hoverinfo='none'
        ))

        # Creiamo le tracce per i pacchi
        for it in bin0.items:
            m = moves_map.get(it.name, 0)
            mesh, wire = create_box_traces(it, m)
            fig.add_trace(mesh)
            fig.add_trace(wire)

        priorities_present = sorted(list(set(int(it.priority) for it in bin0.items)), reverse=True)
        steps = ["Partenza"] + [f"Scarico P{pr}" for pr in priorities_present] + ["Arrivo"]
        
        frames = []
        for step in steps:
            # Creiamo una LISTA di tracce per questo frame
            frame_traces = []

            # 1. Traccia 0: I punti fantasma (sempre visibili per bloccare le proporzioni)
            frame_traces.append(go.Scatter3d(visible=True))

            # 2. Ciclo sui pacchi per decidere visibilità e stile
            # Gli item iniziano dall'indice 1 della fig.data originale
            for idx, it in enumerate(bin0.items):
                m = moves_map.get(it.name, 0)
                
                # Logica Disparizione
                is_visible = True
                if step == "Arrivo": 
                    is_visible = False
                elif step != "Partenza":
                    curr_p_limit = int(step.split('P')[1])
                    if it.priority > curr_p_limit: 
                        is_visible = False
                
                # Logica Highlight (Bordo rosso se è il pacco attuale ed è bloccato)
                is_current_target = (step.startswith("Scarico") and it.priority == int(step.split('P')[1]))
                line_color = "red" if (is_current_target and m > 0) else "black"
                line_width = 10 if (is_current_target and m > 0) else 2
                
                # Aggiungiamo la MESH (faccia solida)
                frame_traces.append(go.Mesh3d(visible=is_visible))
                
                # Aggiungiamo il WIREFRAME (bordi neri/rossi)
                frame_traces.append(go.Scatter3d(
                    visible=is_visible, 
                    line=dict(color=line_color, width=line_width)
                ))

            # Creiamo il frame passando l'intera lista di tracce
            frames.append(go.Frame(data=frame_traces, name=step))

        # --- CONFIGURAZIONE LAYOUT ANTI-SCHIACCIAMENTO ---
        bw, bh, bd = float(bin0.width), float(bin0.height), float(bin0.depth)
        
        fig.update_layout(
            sliders=[dict(
                active=0, 
                currentvalue={"prefix": "Fase attuale: ", "font": {"size": 20}},
                steps=[dict(method="animate", label=s, args=[[s], {"frame": {"duration": 300, "redraw": True}, "mode": "immediate"}]) for s in steps]
            )],
            scene=dict(
                xaxis=dict(title="Larghezza (X)", range=[0, bw]),
                yaxis=dict(title="Profondità (Z)", range=[0, bd]),
                zaxis=dict(title="Altezza (Y)", range=[0, bh]),
                aspectmode='manual',
                aspectratio=dict(x=bw/bd, y=1, z=bh/bd) 
            ),
            updatemenus=[dict(
                type="buttons", 
                buttons=[dict(label="Play", method="animate", args=[None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True}])]
            )]
        )

        # 2. LOGICA DI SCENA (CoG, Target, Viste) - Eseguita una volta per scenario
        if bin0.items:
            cog = bin0.calculate_center_of_gravity()
            # Marker Centro di Gravità (Mapping Assi: x, z, y per avere altezza verticale)
            fig.add_trace(go.Scatter3d(
                x=[float(cog.x)], y=[float(cog.z)], z=[float(cog.y)],
                mode='markers', marker=dict(size=10, color='red', symbol='diamond'),
                name="Centro di Gravità"
            ))
            # Marker Target Bilanciamento (Centro pavimento)
            fig.add_trace(go.Scatter3d(
                x=[bw/2], y=[bd/2], z=[0],
                mode='markers', marker=dict(size=8, color='orange', symbol='x'),
                name='Target Bilanciamento'
            ))


        # Raccolta dati per tabella terminale
        total_items = len(bin0.items)
        vol_util = (sum(i.volume.volume() for i in bin0.items) / bin0._model.volume) * 100
        free_items = list(moves_map.values()).count(0)
        mod = calculate_cog_deviation(bin0)
        results_data.append({
            "name": name, 
            "vol": vol_util, 
            "free": free_items, 
            "total": total_items, 
            "moves": sum(moves_map.values()),
            "CoG": mod
        })
        fig.frames = frames
        name_tag = "corridor" if use_corridor else "no_corridor"
        fig.write_html(str(RESULTS_DIR / f"simulation_{name_tag}_n{NUM_ITEMS}_w{CORRIDOR_WIDTH_PCT}.html"))
        print(f"Generato: simulation_{name_tag}.html")


    # STAMPA STATISTICHE COMPARATIVE FINALI
    print(f"\n{'PARAMETRO':<35} | {'SENZA CORRIDOIO':<18} | {'CON CORRIDOIO':<18}")
    print("-" * 80)
    print(f"{'Pacchi posizionati':<35} | {results_data[0]['total']:<18.1f} | {results_data[1]['total']:<18.1f}")
    print(f"{'Utilizzo Spazio Camion (%)':<35} | {results_data[0]['vol']:<18.1f} | {results_data[1]['vol']:<18.1f}")
    print(f"{'Pacchi Liberi (0 mosse)':<35} | {results_data[0]['free']:<18} | {results_data[1]['free']:<18}")
    print(f"{'Somma Pacchi da Spostare (Totali)':<35} | {results_data[0]['moves']:<18} | {results_data[1]['moves']:<18}")
    
    eff0 = (results_data[0]['free'] / results_data[0]['total'] * 100)
    eff1 = (results_data[1]['free'] / results_data[1]['total'] * 100)
    print(f"{'Indice Efficienza Operativa (%)':<35} | {eff0:<18.1f} | {eff1:<18.1f}")
    print(f"{'Distanza CoG (mm)':<35} | {results_data[0]['CoG']:<18} | {results_data[1]['CoG']:<18}")
    print("-" * 80)
    print(f"File generati in: {RESULTS_DIR.absolute()}")
    # salvataggio dei dati su exel
    save_to_excel_csv(results_data, NUM_ITEMS, CORRIDOR_WIDTH_PCT)
    # creazione grafici
    generate_plots(NUM_ITEMS)


def calculate_cog_deviation(bin) -> float:
    """
    Calcola la deviazione del CoG dal centro ideale.
    Ritorna la distanza in millimetri.
    """
    if not bin.items:
        return 0.0
    
    cog = bin.calculate_center_of_gravity()
    
    # Centro ideale
    center_x = bin.width / Decimal(2)
    center_z = bin.depth / Decimal(2)  
    
    # Deviazione
    dev_x = abs(float(cog.x - center_x))
    dev_z = abs(float(cog.z - center_z))
    mod = int(math.hypot(dev_x, dev_z) * 1000)
    return mod


# salviamo i dati in due file excel (globale e locale)
def save_to_excel_csv(results_data, num_items, corridor_pct):
    """
    It saves result data in two .csv files: one for each number of items,
    one for all reults from each battery test.
    Every result is casted into integer in order to mantaining compatibility with Excel
    """
    eff0 = int((results_data[0]['free'] / results_data[0]['total'] * 100)) if results_data[0]['total'] > 0 else 0
    eff1 = int((results_data[1]['free'] / results_data[1]['total'] * 100)) if results_data[1]['total'] > 0 else 0
    
    file_specifico = RESULTS_DIR / f"report_items_{num_items}.csv"
    file_globale = RESULTS_DIR / "report_globale_tutti_i_test.csv"
    
    header_spec = [
        "Corridoio_PCT_x100", "Pacchi_Senza", "Pacchi_Con", 
        "Vol_Senza", "Vol_Con", "Liberi_Senza", "Liberi_Con", 
        "Mosse_Senza", "Mosse_Con", "Eff_Senza", "Eff_Con",
        "CoG_mm_Senza", "CoG_mm_Con"
    ]
    
    header_glob = ["Numero_Items"] + header_spec

    row_spec = [
        int(corridor_pct * 100), int(results_data[0]['total']), int(results_data[1]['total']),
        int(results_data[0]['vol']), int(results_data[1]['vol']),
        int(results_data[0]['free']), int(results_data[1]['free']),
        int(results_data[0]['moves']), int(results_data[1]['moves']),
        eff0, eff1, 
        int(results_data[0]['CoG']), int(results_data[1]['CoG'])
    ]
    row_glob = [num_items] + row_spec

    def write_csv(path, header, row):
        exists = path.exists()
        with open(path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            if not exists:
                writer.writerow(header)
            writer.writerow(row)

    write_csv(file_specifico, header_spec, row_spec)
    write_csv(file_globale, header_glob, row_glob)
        
    print(f"-> Dati salvati in {file_specifico.name} e nel report globale.")

def generate_plots(num_items):
    """
    Legge il file CSV e genera 3 grafici: Pacchi, Mosse e Centro di Gravità.
    """
    filename = RESULTS_DIR / f"report_items_{num_items}.csv"
    if not filename.exists():
        return
        
    corridoio = []
    p_senza, p_con = [], []
    m_senza, m_con = [], []
    cog_senza, cog_con = [], []
    
    # Lettura dati (tutti trattati come interi)
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader) 
        for row in reader:
            if not row: continue
            # Indici aggiornati in base alla nuova struttura CSV
            corridoio.append(int(row[0])) # Ora è 0, 5, 10...
            p_senza.append(int(row[1]))
            p_con.append(int(row[2]))
            m_senza.append(int(row[7]))
            m_con.append(int(row[8]))
            cog_senza.append(int(row[11])) # CoG mm Senza
            cog_con.append(int(row[12]))   # CoG mm Con
            
    # Ordinamento per asse X
    data = sorted(zip(corridoio, p_senza, p_con, m_senza, m_con, cog_senza, cog_con), key=lambda x: x[0])
    
    c_vals = [x[0] for x in data]
    ps, pc = [x[1] for x in data], [x[2] for x in data]
    ms, mc = [x[3] for x in data], [x[4] for x in data]
    cs, cc = [x[5] for x in data], [x[6] for x in data]

    # Subplots: 3 righe ora!
    fig = make_subplots(
        rows=3, cols=1, 
        subplot_titles=(
            "Saturazione Carico (Numero Pacchi)", 
            "Efficienza Operativa (Somma Mosse)", 
            "Stabilità (Spostamento Centro di Gravità in mm)"
        ),
        vertical_spacing=0.1
    )
    
    # --- 1. PACCHI ---
    fig.add_trace(go.Scatter(x=c_vals, y=ps, name='Pacchi (Senza)', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=c_vals, y=pc, name='Pacchi (Con)', line=dict(color='green')), row=1, col=1)
    
    # --- 2. MOSSE ---
    fig.add_trace(go.Scatter(x=c_vals, y=ms, name='Mosse (Senza)', line=dict(color='red', dash='dot')), row=2, col=1)
    fig.add_trace(go.Scatter(x=c_vals, y=mc, name='Mosse (Con)', line=dict(color='orange')), row=2, col=1)
    
    # --- 3. CENTRO DI GRAVITÀ (CoG) ---
    fig.add_trace(go.Scatter(x=c_vals, y=cs, name='CoG mm (Senza)', line=dict(color='purple', dash='dot')), row=3, col=1)
    fig.add_trace(go.Scatter(x=c_vals, y=cc, name='CoG mm (Con)', line=dict(color='darkviolet')), row=3, col=1)
    
    fig.update_layout(height=1000, title_text=f"Analisi Impatto Corridoio - {num_items} Items", hovermode="x unified")
    
    # Label assi X (ora in percentuale intera)
    for i in range(1, 4):
        fig.update_xaxes(title_text="Larghezza Corridoio %", row=i, col=1)
    
    fig.update_yaxes(title_text="N. Pacchi", row=1, col=1)
    fig.update_yaxes(title_text="Totale Mosse", row=2, col=1)
    fig.update_yaxes(title_text="Distanza CoG (mm)", row=3, col=1)
    
    plot_filename = RESULTS_DIR / f"grafici_items_{num_items}.html"
    fig.write_html(str(plot_filename))
    print(f"-> Grafici (inclusi CoG) aggiornati in: {plot_filename.name}")
    

if __name__ == "__main__":
    # Inizializziamo il parser degli argomenti
    parser = argparse.ArgumentParser(
        description="Simulazione di carico furgone con parametri personalizzabili."
    )
    
    # Definiamo i parametri che vuoi comandare da bash
    parser.add_argument(
        "-n", "--num-items", 
        type=int, 
        default=60, 
        help="Numero di pacchi con cui fare la simulazione (default: 60)"
    )
    parser.add_argument(
        "-w", "--corridor-width", 
        type=float, 
        default=0.2, 
        help="Larghezza del corridoio come percentuale tra 0.0 e 1.0 (default: 0.2)"
    )
    
    # Leggiamo i valori passati da riga di comando
    args = parser.parse_args()
    
    # Sovrascriviamo le variabili globali usate nelle funzioni
    NUM_ITEMS = args.num_items
    CORRIDOR_WIDTH_PCT = args.corridor_width
    
    # Stampiamo un piccolo riepilogo prima di partire
    print(f"-> Configurazione: Pacchi={NUM_ITEMS}, Corridoio={CORRIDOR_WIDTH_PCT:.2%}")
    
    # Avviamo la simulazione
    run_comparison()    
