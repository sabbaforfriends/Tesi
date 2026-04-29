
# Documentazione py3dbl - Libreria 3D Bin Packing con Bilanciamento

## Indice
1. [Panoramica](#panoramica)
2. [Installazione](#installazione)
3. [Architettura](#architettura)
4. [Moduli Principali](#moduli-principali)
5. [Esempi di Utilizzo](#esempi-di-utilizzo)
6. [Test di Confronto](#test-di-confronto-fra-corridoio-presente-e-non)


---

## Panoramica

**py3dbl** è una libreria Python per il 3D bin packing, estesa per includere il vincolo di bilanciamento tramite centro di gravità (CoG) e una nuova strategia di piazzamento Multi-Anchor. Sviluppata come parte di una tesi sulla logistica dell'ultimo miglio, la libreria permette di simulare e ottimizzare il caricamento di veicoli, garantendo efficienza e sicurezza.

### Cos'è il 3D Bin Packing?
Il problema consiste nel posizionare oggetti tridimensionali in uno o più contenitori, massimizzando l'utilizzo dello spazio e rispettando vincoli di:
- Peso massimo
- Dimensioni del contenitore
- Non sovrapposizione
- Supporto fisico
- Bilanciamento del carico (centro di gravità)

### Caratteristiche Principali
- Vincoli personalizzabili e modulari
- Precisione decimale configurabile
- Supporto per rotazioni (90°)
- Visualizzazione 3D interattiva (Plotly) e statica (Matplotlib)
- Generazione automatica di batch di items
- Strategia Multi-Anchor per piazzamento bilanciato
- Calcolo statistiche di caricamento
- Calcolo statistiche di scaricamento
- Vincolo di centro di gravità (CoG) per bilanciamento
- Vincolo di corridoio centrale
- Test di confronto tra corridoio presente e non

---


## Installazione

### Requisiti
- Python 3.x
- Librerie richieste (vedi `requirements.txt`)

### Setup
```bash
# 1. Clona il repository
git clone https://github.com/whowasfra/On-logistic-optimization-algorithms-Thesis-
# 2. Crea un ambiente virtuale
python3 -m venv venv
# 3. Attiva l'ambiente virtuale
source venv/bin/activate
# 4. Installa le dipendenze
pip install -r requirements.txt
```

---


## Architettura

La libreria è organizzata in moduli specializzati:

```
py3dbl/
├── __init__.py           # Esportazione delle classi principali
├── Packer.py             # Algoritmi di packing (greedy, multi-anchor)
├── Bin.py                # Modelli di contenitori
├── Item.py               # Modelli di oggetti
├── Space.py              # Gestione spazio 3D
├── Constraints.py        # Sistema di vincoli (incluso CoG)
├── item_generator.py     # Generazione automatica items
├── render.py             # Visualizzazione 3D
└── Decimal.py            # Precisione numerica
```

---


## Moduli Principali

### `Space.py` - Gestione dello Spazio 3D
Definisce primitive geometriche (Vector3, Volume) e funzioni di intersezione.

### `Item.py` - Oggetti da Imballare
Modella gli oggetti da caricare, con supporto per rotazioni e priorità.

### `Bin.py` - Contenitori
Definisce modelli e istanze di contenitori, con calcolo del centro di gravità.

### `Constraints.py` - Sistema di Vincoli
Vincoli modulari: peso, dimensioni, sovrapposizione, supporto, centro di gravità (CoG).

### `Packer.py` - Algoritmi di Packing
Contiene le strategie greedy (LBB) e Multi-Anchor, orchestrate dalla classe Packer; contiene inoltre il calcolo delle movimentazioni dei pacchi.

### `item_generator.py` - Generazione Items
Genera oggetti casuali o gaussiani per test e simulazioni.

### `render.py` - Visualizzazione 3D
Funzioni per visualizzare la configurazione in Plotly o Matplotlib.

### `Decimal.py` - Precisione Numerica
Gestione della precisione decimale.

---

- `size`: Vector3 | tuple - dimensioni del contenitore (accetta sia Vector3 che tuple)

## Esempi di Utilizzo

### Caricamento base con vincoli fisici
```python
from py3dbl import Packer, BinModel, item_generator, constraints

# Definisci il furgone
van = BinModel(name="DucatoL2H2", size=(1.87, 1.932, 3.120), max_weight=3000)

# Genera ordini casuali
orders = item_generator(
    width=(0.05, 1.5), height=(0.05, 1.5), depth=(0.05, 1.5),
    weight=(10, 1), batch_size=800, use_gaussian_distrib=False
)
if not isinstance(orders, list):
    orders = [orders]

# Packing
packer = Packer()
packer.set_default_bin(van)
packer.add_batch(orders)
packer.pack(constraints=[
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['no_overlap'],
    constraints['is_supported']
])

# Statistiche
stats = packer.calculate_statistics()
print(f"Volume caricato: {stats['loaded_volume']:.2f}")
print(f"Peso caricato: {stats['loaded_weight']:.2f}")
print(f"Utilizzo medio volume: {stats['average_volume']*100:.2f}%")

# Visualizzazione
from py3dbl import render_bin_interactive
render_bin_interactive(packer.current_configuration[0], transparency=0.7)
```

### Packing con vincolo di centro di gravità e Multi-Anchor
```python
from py3dbl import Packer, BinModel, item_generator, constraints

van = BinModel(name="Ducato", size=(1.67, 2.0, 3.10), max_weight=1400)
items = item_generator(
    width=(0.15, 0.60), height=(0.15, 0.60), depth=(0.15, 0.80),
    weight=(2, 40), batch_size=50
)
packer = Packer()
packer.set_default_bin(van)
packer.add_batch(items)
packer.pack(
    strategy="multi_anchor",
    constraints=[
        constraints['weight_within_limit'],
        constraints['fits_inside_bin'],
        constraints['no_overlap'],
        constraints['is_supported'],
        constraints['maintain_center_of_gravity'],
    ]
)
```

### Visualizzazione e analisi
```python
from py3dbl import render_bin_interactive
render_bin_interactive(packer.current_configuration[0])
```

---
#### `Bin`
Istanza di un contenitore con oggetti caricati.

**Parametri del costruttore:**
```python
Bin(id, model)
```
- `id`: identificativo univoco
- `model`: BinModel - modello di riferimento

**Attributi:**
- `items`: list[Item] - oggetti caricati
- `weight`: Decimal - peso corrente caricato

**Metodi:**
- `put_item(item, constraints=[])`: tenta di inserire un oggetto rispettando i vincoli
- `remove_item(item)`: rimuove un oggetto
- `calculate_center_of_gravity()`: calcola il centro di gravità del carico corrente (ritorna Vector3)

**Esempio:**
```python
bin = Bin(id=0, model=furgone)
success = bin.put_item(item, constraints=[...])
```

---

### 4. `Constraints.py` - Sistema di Vincoli

#### `Constraint`
Rappresenta un vincolo da applicare durante il packing.

**Parametri:**
- `func`: funzione che valuta il vincolo (bin, item) -> bool
- `weight`: int - peso per ordinamento (vincoli più costosi = peso maggiore)

**Vincoli predefiniti:**

##### `weight_within_limit` (peso: 5)
Verifica che il peso totale non superi il limite del bin.
```python
def weight_within_limit(bin: Bin, item: Item):
    return bin.weight + item.weight <= bin.max_weight
```

##### `fits_inside_bin` (peso: 10)
Verifica che l'oggetto sia completamente contenuto nel bin.
```python
def fits_inside_bin(bin: Bin, item: Item):
    return all([bin.dimension[axis] >= (item.position[axis] + item.dimensions[axis]) 
                for axis in range(3)])
```
**Nota:** Utilizza `>=` per consentire agli oggetti di toccare esattamente i bordi del contenitore.

##### `no_overlap` (peso: 15)
Verifica che non ci siano sovrapposizioni con altri oggetti.
```python
def no_overlap(bin: Bin, item: Item):
    return len(bin.items) == 0 or 
           not any([intersect(ib.volume, item.volume) for ib in bin.items])
```

##### `is_supported` (peso: 20)
Verifica il supporto fisico dell'oggetto. Controlla che la base dell'item sia sufficientemente appoggiata su altri oggetti o sul pavimento del bin, misurando l'area di contatto diretto (superficie superiore degli item sottostanti esattamente alla coordinata Y inferiore dell'item).

**Parametri aggiuntivi:**
- `minimum_support`: float - percentuale minima della base dell'item che deve essere supportata (default: 0.75, cioè il 75%)

**Logica:**
- Gli oggetti sul pavimento (Y = 0) sono sempre considerati supportati
- Per gli altri, si calcola l'area di contatto con gli item sottostanti la cui superficie superiore coincide esattamente con la posizione Y dell'item
- L'item è accettato se il rapporto area_contatto / area_base ≥ `minimum_support`

##### `maintain_center_of_gravity` (peso: 25)
Vincolo progressivo del centro di gravità. Verifica che il CoG del bin, dopo il piazzamento dell'item, rimanga entro una tolleranza configurabile dal centro geometrico del bin sul piano X-Z.

**Parametri aggiuntivi:**
- `tol_x_percent`: float - tolleranza sull'asse X come percentuale della larghezza del bin (default: 0.2 = 20%)
- `tol_z_percent`: float - tolleranza sull'asse Z come percentuale della profondità del bin (default: 0.2 = 20%)
- `progressive_tightening`: float - quanto la tolleranza si riduce a pieno carico (default: 0.7 = 70%). 0.0 = tolleranza fissa, 1.0 = tolleranza che si riduce a zero a pieno carico.

**Logica:**
1. **Tolleranza progressiva**: la tolleranza si riduce linearmente con il rapporto di carico:
   - A carico basso (load_ratio ≈ 0) → tolleranza massima (100% della tolleranza configurata)
   - A pieno carico (load_ratio = 1) → tolleranza = `tol_max * (1 - progressive_tightening)` (30% con default)
2. Il centro di riferimento Z è leggermente spostato verso il fondo del bin (`bin.depth * 0.4`) per favorire il carico posteriore, più stabile nei veicoli
3. **Corrective bias**: se il CoG corrente devia dal centro più di metà della tolleranza effettiva, i piazzamenti che peggiorerebbero la deviazione vengono rifiutati
4. L'item è rifiutato se la deviazione del CoG futuro supera le tolleranze

La tolleranza progressiva garantisce continuità nel comportamento: anche i primi item sono soggetti al vincolo (con tolleranza massima), permettendo di contribuire al bilanciamento fin dall'inizio. Questo è particolarmente importante quando i primi item sono molto pesanti.

| Load Ratio | Tolleranza effettiva (con `progressive_tightening=0.7`) |
|------------|----------------------------------------------------------|
| 0% | 100% della tolleranza massima |
| 25% | 82.5% della tolleranza massima |
| 50% | 65% della tolleranza massima |
| 75% | 47.5% della tolleranza massima |
| 100% | 30% della tolleranza massima |

```python
# Configurazione delle tolleranze
cog_constraint = constraints['maintain_center_of_gravity']
cog_constraint.set_parameter('tol_x_percent', 0.15)   # 15% tolleranza X
cog_constraint.set_parameter('tol_z_percent', 0.20)   # 20% tolleranza Z
cog_constraint.set_parameter('progressive_tightening', 0.7)  # 70% riduzione a pieno carico
```

**Esempio di utilizzo:**
```python
from py3dbl import constraints

my_constraints = [
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['no_overlap'],
    constraints['is_supported'],
    constraints['maintain_center_of_gravity']
]
```

> **Nota:** Il vincolo CoG è particolarmente efficace quando combinato con la strategia `multi_anchor` (vedi sezione Packer). Con la strategia greedy pura (Left-Bottom-Back), il bias di piazzamento verso l'angolo sinistro-anteriore-basso può causare molti rifiuti e ridurre l'utilizzo dello spazio.

##### `central_corridor_accessibility` (peso: 21)
Vincolo che impone uno spazio rettangolare all'interno del vano di carico all'interno del quale vieta il posizionamento dei pacchi per permettere all'operatore di accedere alla merce.

**Parametri aggiuntivi:**
- `corridor_width_percent`: float - largezza del corridoio in relazione a quella del vano di carico (default: 0.2 = 20%)
- `corridor_depth_percent`: float - profondità del corridoio in relazione a quella del van di carico (default: 0.85 = 85%)
- 

#### Creare vincoli personalizzati
```python
from py3dbl import constraint

@constraint(weight=25)
def custom_constraint(bin: Bin, item: Item):
    # La tua logica qui
    return True  # o False

# Aggiunto automaticamente al dizionario constraints
```

---

### 5. `Packer.py` - Algoritmo di Packing

Il modulo contiene due strategie di piazzamento e la classe `Packer` che le orchestra.

#### Strategie disponibili

| Strategia | Chiave | Descrizione |
|-----------|--------|-------------|
| **Greedy (LBB)** | `'greedy'` | Left-Bottom-Back: accetta la prima posizione valida trovata iterando sui pivot degli item già piazzati. Veloce, ma tende a sbilanciare il carico verso l'angolo sinistro-anteriore-basso. |
| **Multi-Anchor** | `'multi_anchor'` | Genera posizioni candidate da più sorgenti di ancoraggio, valuta tutte le combinazioni (posizione × Y × rotazione) e seleziona il piazzamento migliore secondo una funzione di scoring. |

#### `multi_anchor_packer()` – Dettaglio della strategia Multi-Anchor

La strategia multi-anchor mitiga il bias dell'algoritmo greedy attraverso 4 fasi:

**Principio di design:** la componente CoG nella funzione di scoring viene attivata **solo se** il vincolo `maintain_center_of_gravity` è presente nella lista dei constraint attivi. Questo preserva la separazione tra algoritmo di piazzamento e sistema di vincoli: senza il vincolo, il multi-anchor ottimizza solo per altezza e compattezza; con il vincolo, aggiunge il bilanciamento del carico.

**1. Generazione ancore (X, Z)**
Per ogni item, le posizioni candidate sul piano orizzontale vengono generate da:
- **Angoli del pavimento** del bin (4 corner)
- **Centro geometrico** del pavimento del bin
- **Posizioni adiacenti** agli ultimi 8 item piazzati (destra, dietro, diagonale, sinistra, davanti) — limitati agli ultimi 8 per ottimizzazione delle prestazioni
- **Riflessi speculari** di ogni ancora rispetto ai piani centrali X e Z, così che entrambe le metà del bin vengano esplorate equamente

**2. Scanner superfici Y**
Per ogni posizione (x, z), vengono calcolate tutte le superfici di appoggio valide scansionando gli item che si sovrappongono nella proiezione X-Z. I valori Y sono ordinati dal più alto al più basso (preferenza per lo stacking).

**3. Funzione di scoring**
Ogni combinazione (ancora × livello Y × rotazione) valida viene valutata con uno score composto (più basso = migliore):
- **Penalità altezza** (`height_weight`, default 0.3) – preferisce piazzamenti più bassi per stabilità
- **Compattezza** (`compact_weight`, default 0.2) – preferisce posizioni vicine agli item esistenti per evitare frammentazione

**Nota importante:** il bilanciamento CoG **non** è gestito dalla funzione di scoring, ma interamente dal vincolo `maintain_center_of_gravity` (se presente). Il ruolo del multi-anchor è generare abbastanza posizioni candidate diverse affinché il vincolo possa accettarne una.

**4. Commit del migliore**
Solo il piazzamento con lo score più basso viene effettivamente committato.

#### `Packer`
Classe principale per eseguire l'algoritmo di bin packing.

**Parametri del costruttore:**
```python
Packer(default_bin=None, fleet=None, items=None, current_configuration=None)
```
- `default_bin`: BinModel - bin da usare se la flotta si esaurisce
- `fleet`: list[BinModel] | None - lista di bin disponibili (default: lista vuota)
- `items`: list[Item] | None - oggetti da impacchettare (default: lista vuota)
- `current_configuration`: list[Bin] | None - configurazione di partenza (default: lista vuota)

**Attributi:**
- `unfitted_items`: list[Item] - item non piazzati dopo l'esecuzione di `pack()` (inizializzato a lista vuota)

**Metodi principali:**

##### `set_default_bin(bin)`
Imposta il bin di default.

##### `add_bin(bin)` / `add_fleet(fleet)`
Aggiunge bin alla flotta disponibile.

##### `add_batch(batch)`
Aggiunge oggetti da impacchettare.

##### `pack(constraints, bigger_first, follow_priority, number_of_decimals, strategy, height_weight, compact_weight)`
Esegue l'algoritmo di packing.

**Parametri:**
- `constraints`: list[Constraint] - vincoli da rispettare (default: `BASE_CONSTRAINTS`)
- `bigger_first`: bool - ordina per volume decrescente (default: `True`)
- `follow_priority`: bool - considera la priorità degli oggetti (default: `True`)
- `number_of_decimals`: int - precisione decimale per la formattazione (default: 3)
- `strategy`: str - strategia di piazzamento: `'greedy'` o `'multi_anchor'` (default: `'greedy'`)
- `height_weight`: float - (solo multi_anchor) peso dello scoring per altezza di piazzamento (default: 0.3)
- `compact_weight`: float - (solo multi_anchor) peso dello scoring per compattezza (default: 0.2)

**Ritorna:** nulla, ma aggiorna `current_configuration` e `unfitted_items`

**Attributi aggiornati dopo `pack()`:**
- `current_configuration`: list[Bin] - configurazione finale con i bin caricati
- `unfitted_items`: list[Item] - item che non è stato possibile piazzare

##### `calculate_statistics()`
Calcola statistiche sulla configurazione corrente.

**Ritorna:** dict con:
- `loaded_volume`: volume totale caricato (Decimal)
- `loaded_weight`: peso totale caricato (Decimal)
- `average_volume`: percentuale di utilizzo del volume (Decimal, 0 se configurazione vuota)

**Nota:** Include protezione contro divisione per zero quando non ci sono bin caricati.

**Esempio completo:**
```python
from py3dbl import Packer, BinModel, Item, Volume, Vector3, constraints
from decimal import Decimal

# Definisci il modello di bin
van = BinModel(name="Van", size=(2, 2, 5), max_weight=1000)

# Crea oggetti
items = [
    Item("Box1", Volume(Vector3(0.5, 0.5, 0.5)), Decimal(10), priority=1),
    Item("Box2", Volume(Vector3(0.3, 0.3, 0.3)), Decimal(5), priority=2),
]

# Configura il packer
packer = Packer()
packer.set_default_bin(van)
packer.add_batch(items)

# Esegui il packing
packer.pack(constraints=[
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['no_overlap']
])

# Visualizza risultati
print(f"Bins utilizzati: {len(packer.current_configuration)}")
for bin in packer.current_configuration:
    print(f"  {bin}: {len(bin.items)} items")

# Statistiche
stats = packer.calculate_statistics()
print(f"Utilizzo volume: {stats['average_volume']*100:.2f}%")
```

##### `calculate_moves_v5()`
Calcola il numero di movimentazioni da attuare per scaricare l'intero carico
**Ritorna:** il numero di movimentazioni (int)

---

### 6. `item_generator.py` - Generazione Items

#### `item_generator()`
Genera automaticamente oggetti con caratteristiche casuali.

**Parametri:**
```python
item_generator(
    width, height, depth,      # tuple (min, max) o (mu, sigma)
    weight,                    # tuple (min, max) o (mu, sigma)
    priority_range=(0,0),      # tuple (min, max)
    batch_size=1,              # numero di items
    use_gaussian_distrib=False,# distribuzione gaussiana
    decimals=3                 # precisione decimale
)
```

**Comportamento:**
- Se `use_gaussian_distrib=False`: distribuzione uniforme tra min e max
- Se `use_gaussian_distrib=True`: distribuzione gaussiana con media (mu) e deviazione standard (sigma)

**Ritorna:**
- Se `batch_size=1`: un singolo Item
- Altrimenti: list[Item]

**Nota importante:** Quando si usa `item_generator` con `batch_size=1`, restituisce un singolo oggetto `Item` invece di una lista. Se passi il risultato a `Packer.add_batch()`, assicurati di avvolgerlo in una lista:
```python
item = item_generator(..., batch_size=1)
if not isinstance(item, list):
    item = [item]
packer.add_batch(item)
```

**Esempio:**
```python
from py3dbl import item_generator

# Distribuzione uniforme
items_uniform = item_generator(
    width=(0.1, 1.0),
    height=(0.1, 1.0),
    depth=(0.1, 1.0),
    weight=(1, 50),
    priority_range=(0, 10),
    batch_size=100
)

# Distribuzione gaussiana
items_gaussian = item_generator(
    width=(0.5, 0.1),    # mu=0.5, sigma=0.1
    height=(0.5, 0.1),
    depth=(0.5, 0.1),
    weight=(25, 5),       # mu=25, sigma=5
    batch_size=100,
    use_gaussian_distrib=True
)
```

---

### 7. `render.py` - Visualizzazione 3D

#### Funzioni di rendering

##### `render_bin_interactive(bin, colors=COLORS, render_bin=True, ...)`
Crea una visualizzazione 3D interattiva usando Plotly.

**Parametri:**
- `bin`: Bin - contenitore da visualizzare
- `colors`: list[str] - colori per gli oggetti
- `render_bin`: bool - mostra il contenitore
- `border_width`: float - spessore bordi
- `border_color`: str - colore bordi
- `transparency`: float - trasparenza (0-1)

**Esempio:**
```python
from py3dbl import render_bin_interactive

render_bin_interactive(
    packer.current_configuration[0],
    border_width=1.0,
    transparency=0.8
)
```

##### `render_bin(bin, colors=COLORS, ...)`
Visualizzazione statica con Matplotlib.

##### `render_volume_interactive(volume, fig, color, name, ...)`
Rendering di un singolo volume (basso livello).

##### `render_item_interactive(item, fig, color, ...)`
Rendering di un singolo item (basso livello).

##### `test_slider.py`
test con visualizzazione grafica interattiva che simula lo scarico ad ogni fermata.

---

### 8. `Decimal.py` - Gestione Precisione

#### Funzioni

##### `set_to_decimal(value, number_of_decimals)`
Converte un valore in Decimal con precisione specificata.

```python
from py3dbl.Decimal import set_to_decimal

value = set_to_decimal(3.14159, 2)  # Decimal('3.14')
```

##### `get_limit_number_of_decimals(number_of_decimals)`
Ottiene il valore limite per la quantizzazione.

**Variabile globale:**
- `decimals = 3`: precisione di default

---

## Esempi di Utilizzo

### Esempio 1: Caso Base - Caricamento Furgone

```python
import py3dbl
from decimal import Decimal

# Definisci il furgone (Fiat Ducato L2H2)
furgone = py3dbl.BinModel(
    name="DucatoL2H2",
    size=(1.87, 1.932, 3.120),
    max_weight=3000
)

# Genera ordini casuali
orders = py3dbl.item_generator(
    width=(0.05, 1.5),
    height=(0.05, 1.5),
    depth=(0.05, 1.5),
    weight=(1, 10),
    priority_range=(0, 10),
    batch_size=100,
    use_gaussian_distrib=False
)

# Assicurati che orders sia una lista (item_generator può restituire un singolo Item se batch_size=1)
if not isinstance(orders, list):
    orders = [orders]

# Configura il packer
packer = py3dbl.Packer()
packer.set_default_bin(furgone)
packer.add_batch(orders)

# Esegui il packing con supporto fisico
import time
start = time.time()

packer.pack(constraints=[
    py3dbl.constraints['weight_within_limit'],
    py3dbl.constraints['fits_inside_bin'],
    py3dbl.constraints['no_overlap'],
    py3dbl.constraints['is_supported']
])

end = time.time()
print(f"Tempo di esecuzione: {end - start:.2f}s")

# Risultati
print(f"Furgoni utilizzati: {len(packer.current_configuration)}")
total_items = sum(len(bin.items) for bin in packer.current_configuration)
print(f"Items caricati: {total_items}/{len(orders)}")

# Statistiche
stats = packer.calculate_statistics()
print(f"Volume caricato: {stats['loaded_volume']:.2f}")
print(f"Peso caricato: {stats['loaded_weight']:.2f}")
print(f"Utilizzo medio volume: {stats['average_volume']*100:.2f}%")

# Visualizza il primo furgone
py3dbl.render_bin_interactive(
    packer.current_configuration[0],
    render_bin=True,
    border_width=1.0,
    transparency=0.7
)
```

### Esempio 2: Flotta Mista

```python
import py3dbl

# Definisci diversi modelli di veicoli
piccolo = py3dbl.BinModel("Furgoncino", (1.2, 1.5, 2.0), max_weight=800)
medio = py3dbl.BinModel("Furgone", (1.8, 1.9, 3.0), max_weight=2000)
grande = py3dbl.BinModel("Camion", (2.4, 2.5, 5.0), max_weight=5000)

# Flotta disponibile
fleet = [piccolo, piccolo, medio, grande]

# Genera oggetti
items = py3dbl.item_generator(
    width=(0.2, 1.0),
    height=(0.2, 1.2),
    depth=(0.2, 1.5),
    weight=(5, 50),
    batch_size=200
)

# Packer con flotta
packer = py3dbl.Packer(fleet=fleet, items=items, default_bin=medio)

# Esegui
packer.pack()

# Analizza utilizzo per tipo
for bin in packer.current_configuration:
    print(f"{bin._model.name}: {len(bin.items)} items, "
          f"peso {bin.weight}/{bin.max_weight}")
```

### Esempio 3: Vincolo Personalizzato - Oggetti Fragili

```python
import py3dbl
from py3dbl import constraint, Bin, Item

# Definisci vincolo personalizzato
@constraint(weight=30)
def fragile_on_top(bin: Bin, item: Item):
    """Gli oggetti fragili devono stare sopra"""
    if not hasattr(item, 'fragile'):
        return True
    
    if item.fragile:
        # Verifica che sotto non ci siano oggetti non fragili pesanti
        for other in bin.items:
            if (other.position.y + other.height <= item.position.y and
                other.weight > 20 and not getattr(other, 'fragile', False)):
                return False
    return True

# Crea items con attributo fragile
items = []
for i in range(50):
    item = py3dbl.item_generator(
        width=(0.2, 0.5),
        height=(0.2, 0.5),
        depth=(0.2, 0.5),
        weight=(5, 30),
        batch_size=1
    )
    item.fragile = (i % 5 == 0)  # 20% fragili
    item.name = f"Item_{i}_{'FRAGILE' if item.fragile else 'OK'}"
    items.append(item)

# Packing con vincolo personalizzato
bin_model = py3dbl.BinModel("Container", (2, 2, 2), max_weight=500)
packer = py3dbl.Packer(default_bin=bin_model)
packer.add_batch(items)

packer.pack(constraints=[
    py3dbl.constraints['weight_within_limit'],
    py3dbl.constraints['fits_inside_bin'],
    py3dbl.constraints['no_overlap'],
    py3dbl.constraints['is_supported'],
    py3dbl.constraints['fragile_on_top']  # Vincolo custom
])
```

### Esempio 4: Confronto Greedy vs Multi-Anchor

Questo esempio confronta le due strategie di piazzamento con il vincolo di centro di gravità attivo, evidenziando come la strategia multi-anchor produca un carico bilanciato.

```python
from decimal import Decimal
from py3dbl import BinModel, Packer, Item, constraints
from py3dbl.Space import Vector3, Volume

# Scenario: mix di item pesanti e leggeri
def create_items():
    items = []
    for i in range(5):  # 5 heavy items
        items.append(Item(f"Heavy_{i}",
            Volume(size=Vector3(Decimal('0.40'), Decimal('0.40'), Decimal('0.40'))),
            weight=Decimal('80'), priority=5))
    for i in range(15):  # 15 light items
        items.append(Item(f"Light_{i}",
            Volume(size=Vector3(Decimal('0.50'), Decimal('0.50'), Decimal('0.50'))),
            weight=Decimal('3'), priority=1))
    return items

furgone = BinModel("Van Maxi", size=(1.870, 2.172, 4.070), max_weight=1400)

active_constraints = [
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['no_overlap'],
    constraints['is_supported'],
    constraints['maintain_center_of_gravity'],
]

# ─── Greedy ───
packer_greedy = Packer()
packer_greedy.set_default_bin(furgone)
packer_greedy.add_batch(create_items())
packer_greedy.pack(constraints=active_constraints, strategy='greedy')

# ─── Multi-Anchor ───
packer_ma = Packer()
packer_ma.set_default_bin(furgone)
packer_ma.add_batch(create_items())
packer_ma.pack(constraints=active_constraints, strategy='multi_anchor')

# ─── Confronto ───
for label, p in [("Greedy", packer_greedy), ("Multi-Anchor", packer_ma)]:
    for bin in p.current_configuration:
        cog = bin.calculate_center_of_gravity()
        cx, cz = bin.width / Decimal(2), bin.depth / Decimal(2)
        print(f"{label}: {len(bin.items)} items, "
              f"CoG dX={abs(cog.x - cx):.3f} ({float(abs(cog.x - cx) / bin.width) * 100:.1f}%) "
              f"dZ={abs(cog.z - cz):.3f} ({float(abs(cog.z - cz) / bin.depth) * 100:.1f}%)")
```

**Risultato tipico:**

| Strategia    | Items caricati | Deviazione CoG X | Deviazione CoG Z |
| ------------ | -------------- | ---------------- | ---------------- |
| Greedy (LBB) | 20/20          | ~12.7%           | ~29.1%           |
| Multi-Anchor | 20/20          | ~0.0%            | ~0.0%            |

### Esempio 5: Multi-Anchor con pesi di scoring personalizzati

```python
import py3dbl

bin_model = py3dbl.BinModel("Container", (2, 2, 3), max_weight=1000)
items = py3dbl.item_generator(
    width=(0.1, 0.8), height=(0.1, 0.8), depth=(0.1, 0.8),
    weight=(1, 50), batch_size=50
)

packer = py3dbl.Packer(default_bin=bin_model)
packer.add_batch(items)

# Multi-anchor con enfasi sulla compattezza
packer.pack(
    constraints=[
        py3dbl.constraints['weight_within_limit'],
        py3dbl.constraints['fits_inside_bin'],
        py3dbl.constraints['no_overlap'],
        py3dbl.constraints['is_supported'],
    ],
    strategy='multi_anchor',
    height_weight=0.2,    # leggera preferenza per piazzamenti bassi
    compact_weight=1.0    # massima compattezza
)
```

---


## Test di Confronto fra corridoio presente e non

Il file `test_slider.py` permette di confrontare il caricamento con il corridoio o senza. i risultati del test sono esportati in file .csv ragruppati per numero di oggetti caricati. Vengono inoltre generati dei grafici in funzione della grandezza del corridoio.

Esempio di esecuzione:
```bash
python test_slider.py [-num.items] [-corr.widht]
```

---

### Costanti

#### `BASE_CONSTRAINTS`
```python
BASE_CONSTRAINTS = [
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['no_overlap']
]
```

#### `PACKING_STRATEGIES`
```python
PACKING_STRATEGIES = ['greedy', 'multi_anchor']
```

#### `COLORS` (in render.py)
```python
COLORS = ["cyan", "red", "yellow", "blue", "green", "brown", "magenta"]
```

---

## Note Tecniche

### Sistema di Coordinate
- **X**: Larghezza (width)
- **Y**: Altezza (height)  
- **Z**: Profondità (depth)

### Rotazioni
Le rotazioni sono sempre di 90° e possono essere:
- **Orizzontale**: scambia X ↔ Z (width ↔ depth)
- **Verticale**: scambia Y ↔ Z (height ↔ depth)

### Algoritmi di Packing

#### `base_packer` – Strategia Greedy (Left-Bottom-Back)
L'algoritmo `base_packer` segue questa logica:
1. Ordina bins e items (opzionalmente per volume)
2. Per ogni bin disponibile o di default:
   - Tenta di inserire il primo item in posizione (0,0,0)
   - Per gli altri items, cerca posizioni valide:
     - Usa come pivot gli angoli degli items già inseriti
     - Prova 3 assi × 2 rotazioni orizzontali × 2 rotazioni verticali = 12 orientamenti
   - Verifica tutti i vincoli ad ogni tentativo
   - Accetta la **prima** posizione valida trovata
   - **Importante:** Se un item non può essere inserito, la sua posizione e dimensioni originali vengono ripristinate
3. Se un bin è pieno o non può accogliere altri items, passa al successivo
4. Continua finché tutti gli items sono inseriti o i bin finiscono

> **Limite noto:** l'euristica LBB ha un bias intrinseco verso l'angolo sinistro-anteriore-basso del bin perché le posizioni candidate sono generate iterando sugli item già piazzati in ordine di inserimento. Quando il vincolo di centro di gravità è attivo, questo bias causa molti rifiuti e riduce l'utilizzo dello spazio.

#### `multi_anchor_packer` – Strategia Multi-Anchor
L'algoritmo `multi_anchor_packer` risolve il bias del greedy:
1. Ordina bins e items (opzionalmente per volume)
2. Per ogni bin disponibile o di default:
   - Per ogni item, genera posizioni candidate (x, z) da **4 sorgenti** di ancoraggio:
     - Angoli del pavimento del bin
     - Centro geometrico del pavimento
     - Posizioni adiacenti agli **ultimi 8 item** piazzati (5 direzioni) — ottimizzazione prestazioni
     - Riflessi speculari delle ancore rispetto ai piani centrali X e Z
   - Per ogni ancora, calcola tutte le superfici di appoggio Y valide
   - Prova tutte le 4 rotazioni (2 orizzontali × 2 verticali) per ogni combinazione
   - Valida i vincoli su ogni candidato
   - Calcola uno **score** per ogni piazzamento valido (CoG + altezza + compattezza)
   - **Committa solo il piazzamento con lo score migliore** (più basso)
3. Stessa logica multi-bin del greedy


## Crediti e Riferimenti

- Basato su py3dbp
- Sviluppato per ricerca su algoritmi di ottimizzazione logistica
- Focus su last-mile delivery

## Licenza

Vedi repository originale per dettagli sulla licenza.

---
