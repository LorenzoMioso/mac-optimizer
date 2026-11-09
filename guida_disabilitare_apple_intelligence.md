# 🧠 Guida: Disabilitare Apple Intelligence su macOS 27 (M1 8GB)

Questa guida illustra la procedura per disattivare i modelli e i demoni locali di **Apple Intelligence** su macOS 27, liberando tra **1 e 2 GB di RAM unificata** e oltre **12 GB di spazio su disco SSD** (fondamentale per lo swap di memoria durante lo sviluppo).

---

## 🧐 Il Problema: Apple Intelligence su Mac con 8 GB di RAM

A partire da macOS 15 e in particolare su **macOS 27**, Apple ha integrato profondamente i modelli di inferenza locale (LLM e modelli di diffusione) nel sistema operativo.
Su un Mac con 8 GB di memoria unificata:
- Non esiste più un singolo pulsante "Off" globale nelle impostazioni standard.
- Demoni in background come `intelligenceplatformd`, `modelmanagerd` e `com.apple.siri.uaf` rimangono costantemente residenti in RAM unificata (condivisa tra CPU, GPU e Neural Engine).
- I modelli scaricati occupano da 12 a 15 GB su SSD. Su unità da 256 GB, questo spazio sottratto riduce drasticamente il margine per la memoria virtuale (swap file), causando blocchi di sistema quando si lanciano contemporaneamente VS Code, il Simulatore e xcodebuild.

---

## 🚀 Metodo 1: Disattivazione Automatica via CLI (RemoveMacAI) - Consigliato

L'utility open-source **`RemoveMacAI`** agisce a livello di profili di configurazione locali e gestione asset UAF (`com.apple.siri.uaf`), **senza richiedere la disattivazione di SIP (System Integrity Protection)**.

### Passo 1: Installazione tramite Homebrew
Apri il Terminale ed esegui:
```bash
brew install omlahore/tap/removemacai
```

### Passo 2: Verifica dello Stato Attuale e Simulazione (Dry Run)
Prima di applicare modifiche, controlla lo stato dei modelli e dei demoni:
```bash
# Mostra lo stato dei demoni e modelli attivi
removemacai status

# Esegui una simulazione delle azioni che verranno intraprese
removemacai off --dry-run
```

### Passo 3: Disattivazione dei Demoni e Rimozione Modelli
Applica la disattivazione:
```bash
removemacai off
```
Questo comando:
1. Termina i demoni in background legati all'AI locale.
2. Rimuove i pesanti file dei modelli dalla cache di sistema (recuperando oltre 12 GB di disco).
3. Genera un profilo di restrizione locale per impedire che macOS riscarichi e riavvii i demoni in automatico.

### Passo 4: Approvazione del Profilo di Sistema
Al termine del comando, si aprirà automaticamente la schermata delle impostazioni (oppure aprila manualmente):
1. Vai su **Impostazioni di Sistema > Generali > Gestione dispositivi** (oppure *Profili*).
2. Seleziona il profilo di configurazione generato da RemoveMacAI e clicca su **Installa / Approva**.
3. Inserisci la tua password di amministratore per confermare.

### Passo 5: Verifica Finale
Controlla nuovamente lo stato:
```bash
removemacai status
```
In **Monitoraggio Attività** (Activity Monitor), verifica che i processi `intelligenceplatformd` o `modelmanagerd` non siano più presenti nell'elenco della memoria attiva.

*(Nota: se in futuro desideri riattivare le funzionalità, ti basterà eseguire `removemacai on` e rimuovere il profilo da Impostazioni di Sistema).*

---

## 🛠️ Metodo 2: Disattivazione Manuale (Senza Tool Esterni)

Se preferisci non installare tool di terze parti, puoi limitare fortemente l'impatto di Apple Intelligence tramite le impostazioni di sistema:

1. **Limitare Siri alle funzioni classiche:**
   - Vai in **Impostazioni di Sistema > Tempo di utilizzo > Contenuti e privacy**.
   - Abilita le restrizioni (se non attive).
   - Entra nella sezione **Siri** (o *Funzionalità e App*).
   - Imposta la modalità su **Siri Classic** (disattivando le risposte generative e i modelli contestuali).
2. **Disattivare Writing Tools & Image Playground:**
   - Vai in **Impostazioni di Sistema > Apple Intelligence e Siri** (se presente).
   - Disattiva tutti gli interruttori relativi a *Strumenti di scrittura*, *Generazione immagini*, e *Suggerimenti proattivi*.
3. **Escludere la cartella dei modelli da Spotlight:**
   - Vai in **Impostazioni di Sistema > Spotlight > Privacy da Spotlight**.
   - Assicurati che le cartelle temporanee di build e le cache pesanti non vengano indicizzate continuamente.

---

## 📈 Risultati Attesi

| Componente | Prima dell'Ottimizzazione | Dopo l'Ottimizzazione | Guadagno |
| :--- | :--- | :--- | :--- |
| **RAM Unificata occupata da AI** | 1.2 – 2.0 GB | ~0 MB | **+1.5 GB RAM libera** |
| **Spazio SSD occupato da modelli** | 12 – 15 GB | < 500 MB | **+12 GB Disco per Swap** |
| **Pressione memoria durante build** | Giallo / Rosso (Thrashing) | Verde (Stabile) | **Fluidità generale** |
