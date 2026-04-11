import plotly.graph_objects as go 
import random, json, time 
import matplotlib.pyplot as plt

def plot_3d_py3dbp(packer, best_bin, type):
    used_bins = [b for b in packer.bins if b.items]
    if not used_bins:
        print("Nessun bin per cui fare plot")
        return 

    bin = used_bins[best_bin]
    bin_width, bin_height, bin_depth = bin.width, bin.height, bin.depth

    fig = go.Figure()

    for item in bin.items:
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth
        color = f'rgb({random.randint(50,255)},{random.randint(50,255)},{random.randint(50,255)})'

        fig.add_trace(go.Mesh3d(
            x=[x, x+w, x+w, x, x, x+w, x+w, x],
            z=[y, y, y+h, y+h, y, y, y+h, y+h],
            y=[z, z, z, z, z+d, z+d, z+d, z+d],
            color=color,
            opacity=0.8,
            name=item.name,
            alphahull=0,
            showscale=False
        ))

    fig.add_trace(go.Mesh3d(
        x=[0, bin_width, bin_width, 0, 0, bin_width, bin_width, 0],
        z=[0, 0, bin_height, bin_height, 0, 0, bin_height, bin_height],
        y=[0, 0, 0, 0, bin_depth, bin_depth, bin_depth, bin_depth],
        color='lightgrey',
        opacity=0.1,
        showscale=False,
        name='Bin'
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Width'),
            yaxis=dict(title='Height'),
            zaxis=dict(title='Depth'),
            aspectmode='data'
        ),
        title=f"3D Packing Visualization - Bin {bin.id} ({len(bin.items)} items)"
    )

    if type: 
        fig.write_html("./plots/bin_3d_py3dbp.html")
    else: 
        fig.write_html("./plots/bin_3d_py3dbp_realistic.html")
    

def plot_3d_ortools(items, solver, assign, o, orientations, best_bin_idx, bin_dims, x, y, z, w, h, d, support, floor, type):
    BIN_W, BIN_H, BIN_D = bin_dims
    fig = go.Figure()
    
    items_in_bin = []
    
    for i in range(len(items)):
        if solver.Value(assign[(i, best_bin_idx)]) == 1:
            items_in_bin.append(i)
            item_y = solver.Value(y[i])
            item_h = solver.Value(h[i])
            item_top = item_y + item_h
    
    print(f"Oggetti nel bin: {len(items_in_bin)}")


    for i in items_in_bin:
        try:
            chosen_orientation_index = solver.Value(o[i])
            di, dj, dk = orientations[chosen_orientation_index]
            wi = int(items[i][di])
            hi = int(items[i][dj])
            di_len = int(items[i][dk])

            xi, yi, zi = solver.Value(x[i]), solver.Value(y[i]), solver.Value(z[i])
            
            color = f'rgb({random.randint(50,255)},{random.randint(50,255)},{random.randint(50,255)})'

            fig.add_trace(go.Mesh3d(
                x=[xi, xi+wi, xi+wi, xi, xi, xi+wi, xi+wi, xi],
                y=[yi, yi, yi+hi, yi+hi, yi, yi, yi+hi, yi+hi],
                z=[zi, zi, zi, zi, zi+di_len, zi+di_len, zi+di_len, zi+di_len],
                alphahull = 0, 
                showscale = False,
                color=color,
                opacity=0.8,
                name=f"Item {i} (L{yi}, {wi}×{hi}×{di_len}"
            ))
            
        except Exception as e:
            print(f"Errore nel disegnare item {i}: {e}")
            continue

    fig.add_trace(go.Mesh3d(
        x=[0, BIN_W, BIN_W, 0, 0, BIN_W, BIN_W, 0],
        y=[0, 0, BIN_H, BIN_H, 0, 0, BIN_H, BIN_H],
        z=[0, 0, 0, 0, BIN_D, BIN_D, BIN_D, BIN_D],
        opacity=0.1,
        alphahull=0,
        color="gray",
        showscale = False, 
        name="Confini bin",
        showlegend=False
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Width (X)', range=[0, BIN_W]),
            yaxis=dict(title='Height (Y)', range=[0, BIN_H]),
            zaxis=dict(title='Depth (Z)', range=[0, BIN_D]),
            aspectmode='data'
        ),
        title=f"Bin {best_bin_idx}: {len(items_in_bin)} oggetti"
    )

    if type:
        fig.write_html("./plots/bin_3d_ortools.html")
    else: 
        fig.write_html("./plots/bin_3d_ortools_realistic.html")


def plot_graph(xlabel, ylabel, title, xarray, results_dict, filename, info):
    # se è un plotting al variare della capacità e non del peso è necessario convertire da mm3 a litri
    if info: 
        xarray = [cap / 1_000_000 for cap in xarray]

    plt.figure(figsize=(10, 6))
    for algo, results in results_dict.items(): 
        plt.plot(xarray, results, label=algo, linewidth=2)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title, fontsize=14)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    #salvataggio
    plt.savefig(filename, dpi=300)
    plt.close()
