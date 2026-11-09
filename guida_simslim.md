# 🪶 Guida: Ridurre la RAM del Simulatore iOS con simslim

Questa guida spiega come utilizzare l'utility open-source **`simslim`** per abbattere il consumo di memoria RAM del Simulatore iOS su MacBook Air M1 (8 GB RAM), riducendolo da **3.5 GB a meno di 900 MB**.

---

## 🧐 Il Problema: Il footprint del Simulatore iOS

Quando avvii un simulatore iOS standard (es. iPhone 15 o iPhone 16) su macOS, il sistema operativo emula un dispositivo iOS completo caricando circa **180-250 processi e demoni in background** (launchd). Molti di questi demoni non servono affatto durante lo sviluppo di un'app:
- Indicizzazione e ricerca Spotlight interna al simulatore (`spotlightknowledged`, `searchd`).
- Sincronizzazione foto e libreria multimediale (`assetsd`, `photolibraryd`).
- Sincronizzazione cloud e backup iCloud (`cloudd`, `bird`).
- Riconoscimento vocale e demoni Siri (`siriknowledged`, `assistantd`).
- Apple News, Apple Music, daemon di geofencing e analytics (`com.apple.diagnosticd`, `healthd`).

Su un Mac M1 con 8 GB di memoria unificata, un simulatore da solo assorbe tra i **2.5 e i 4 GB di RAM**. Se a questo aggiungi VS Code, Dart VM e la compilazione Xcode, la memoria si esaurisce istantaneamente, costringendo macOS a un uso massiccio dello swap su SSD (con conseguenti freeze e rallentamenti).

---

## 🚀 1. Installazione di simslim

`simslim` è un'utility specificamente progettata per disabilitare selettivamente fino a 170 demoni `launchd` non essenziali nel runtime del simulatore senza compromettere le API necessarie allo sviluppo di app.

Installa `simslim` tramite Homebrew:
```bash
brew install mobai-app/tap/simslim
```

---

## ⚡ 2. Utilizzo e Attivazione

### 2.1 Avvio e Snellimento
1. Avvia il tuo Simulatore iOS abituale (da Xcode, da VS Code o con `open -a Simulator`).
2. Una volta che il simulatore ha completato il boot ed è sulla schermata Home, apri il Terminale ed esegui:
   ```bash
   simslim on
   ```
3. L'utility spegnerà i demoni di background non necessari. In pochi secondi vedrai il numero di processi crollare da oltre 250 a circa 60-70.

### 2.2 Preservare Servizi Specifici (Eccezioni)
Se la tua applicazione necessita di servizi specifici (es. notifiche push remote o geolocalizzazione avanzata):
```bash
# Esempio: mantenere attivo il demone delle notifiche push (apsd)
simslim on --keep com.apple.apsd

# Esempio: mantenere push e geolocalizzazione
simslim on --keep com.apple.apsd,com.apple.locationd
```

### 2.3 Ripristino allo Stato di Fabbrica
In qualsiasi momento puoi ripristinare il simulatore con tutti i demoni attivi:
```bash
simslim off
```

---

## 📊 3. Misurazione e Verifica

Per verificare il risparmio di RAM e risorse:

1. **Da terminale:**
   ```bash
   simslim measure
   ```
   L'output mostrerà il confronto della RAM usata e del numero di thread/processi attivi.

2. **Da Monitoraggio Attività (Activity Monitor):**
   - Apri **Monitoraggio Attività** > scheda **Memoria**.
   - Cerca i processi `Simulator` e i processi con percorso contenente `CoreSimulator`.
   - Noterai una riduzione complessiva da ~3.5 GB a circa **700-900 MB**, lasciando libera preziosa memoria unificata per VS Code e Dart.

---

## 💡 4. Best Practice Aggiuntive per il Simulatore su 8GB

1. **Usa un dispositivo simulato leggero:**  
   Simulare dispositivi con schermi enormi o ad altissima densità (es. iPad Pro 13" o iPhone 16 Pro Max) richiede più memoria grafica per i frame buffer. Per i test quotidiani dell'interfaccia, preferisci un modello standard (es. iPhone SE 3rd gen o iPhone 15/16 standard).
2. **Scala della finestra al 50%:**  
   Nel Simulatore vai su **Window > Zoom** o premi `Cmd + 3` per visualizzare la finestra al 50% di scala: riduce il carico sulla GPU unificata e sul `WindowServer`.
3. **Preferisci un dispositivo fisico quando possibile:**  
   Se hai a disposizione un iPhone fisico, collegarlo via cavo o Wi-Fi (`flutter run -d <id_iphone>`) azzera completamente l'overhead del simulatore, risparmiando il 100% della RAM dedicata al runtime virtuale.
