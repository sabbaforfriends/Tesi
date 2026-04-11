#!/bin/bash

# Nome del file in cui verranno salvati tutti i log
OUTPUT_FILE="report_simulazioni.txt"

# Svuota il file di output se esiste già, o lo crea se non c'è
> "$OUTPUT_FILE"

echo "=== AVVIO BATTERIA DI TEST ===" | tee -a "$OUTPUT_FILE"
echo "I risultati dettagliati verranno salvati in: $OUTPUT_FILE"
echo "------------------------------------------" >> "$OUTPUT_FILE"

# Ciclo per il numero di oggetti: da 0 a 100 con passo 10
for n in $(seq 10 10 100); do
    # Ciclo per lo spessore del corridoio: da 0.0 a 0.50 con passo 0.05
    for w in $(seq 0.1 0.1 0.9); do
        
        echo "Lancio test con: Pacchi = $n | Corridoio = $w" | tee -a "$OUTPUT_FILE"
        echo "------------------------------------------" >> "$OUTPUT_FILE"
        
        # Eseguiamo lo script Python passando i parametri
        # Usiamo '2>&1' per catturare nel file di testo sia l'output normale che eventuali errori
        python3 test_slider.py -n "$n" -w "$w" >> "$OUTPUT_FILE" 2>&1
        
        # Aggiungiamo un paio di righe vuote di stacco per rendere il file leggibile
        echo -e "\n\n" >> "$OUTPUT_FILE"
        
    done
done

echo "=== BATTERIA DI TEST COMPLETATA ===" | tee -a "$OUTPUT_FILE"
echo "=== AVVIO GENERAZIONE DASHBOARD GLOBALE ===" | tee -a "$OUTPUT_FILE"
# Eseguiamo lo script per la dashboard a 3 grafici
python3 generate_dashboard.py >> "$OUTPUT_FILE" 2>&1

echo "Processo terminato con successo! Controlla la cartella 'results_simulation_final' per i risultati." | tee -a "$OUTPUT_FILE"