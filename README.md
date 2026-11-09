# 🚀 Mac Developer Optimizer & Cleaner

> Suite di ottimizzazione, manutenzione e pulizia profonda per **macOS (Apple Silicon M1/M2/M3/M4 & Intel)**.  
> Progettata per sviluppatori mobile e web (**iOS, Xcode, Flutter, Android, Node/NPM, Docker, VS Code, Homebrew**), in particolare su macchine con risorse limitate (es. **MacBook 8 GB RAM / 256 GB SSD**).

---

## ⚡ In Sintesi: Cosa fa questa repository

1. **`clean_mac.py` (Script con Terminal UI interattiva):**  
   Analizza e ripulisce in sicurezza oltre **30–50 GB** di cache di compilazione, runtime orfani, container, vecchie estensioni e file temporanei senza toccare credenziali, account, cookie o repository di lavoro.
2. **Terminal UI (TUI):**  
   Interfaccia a tutto schermo nel terminale per navigare, abilitare/disabilitare moduli con la **barra spaziatrice**, alternare **Dry-Run** e vedere lo spazio stimato in tempo reale.
3. **Guide di Ottimizzazione RAM di Sistema:**  
   - [`guida_simslim.md`](guida_simslim.md): Riduzione RAM del Simulatore iOS da **3.5 GB a < 900 MB**.  
   - [`guida_disabilitare_apple_intelligence.md`](guida_disabilitare_apple_intelligence.md): Recupero di **> 12 GB SSD** e **1.5 GB RAM** disattivando i modelli AI locali su macOS 15+.

---

## 🖥️ Terminal UI (TUI) Interattiva

Lanciando semplicemente `./clean_mac.py` in un terminale si apre la **Terminal UI interattiva** (scritta con `curses`, zero dipendenze esterne):

```text
================================================================================
 🧹 Mac Developer Cleaner & Optimizer              [ SIMULAZIONE (DRY-RUN) ]
 Disco: 34.0 GB liberi su 228.0 GB (85.1% usato)
--------------------------------------------------------------------------------
 -- 🍎 Sviluppo iOS & macOS --
 [X] Xcode DerivedData                                21.8 GB  [Consigliato]
 [X] Xcode Archives (> 30 giorni)                    837.3 MB  [Sicuro]
 [X] Xcode iOS DeviceSupport                              0 B  [Sicuro]
 [X] Xcode IDE Caches & Docs                           2.4 MB  [Sicuro]
 [X] Simulatori iOS: Cache & Orfani                       0 B  [Consigliato]
 [X] Swift Package Manager Cache                     946.6 MB  [Sicuro]
 -- 📦 Package Manager & SDK --
 [X] Homebrew Cache & Bottles                         92.3 MB  [Sicuro]
 [X] CocoaPods Cache                                 442.9 MB  [Sicuro]
 [X] Node / NPM / Yarn / PNPM                          1.4 GB  [Sicuro]
 [X] Gradle & Android Build Caches                   896.2 MB  [Sicuro]
 [X] Python / Pip / UV Cache                         115.7 MB  [Sicuro]
 [ ] Flutter & Dart Pub Git Cache                         0 B  [Sicuro]
 -- 💻 Editor & Docker --
 [X] VS Code: Estensioni Obsolete                    120.4 MB  [Sicuro]
 [ ] Docker System Prune                                  0 B  [Attenzione]
 -- 🌐 Cache App & Browser --
 [X] Spotify Streaming Cache                           3.9 GB  [Sicuro]
 [X] Browser Web Caches                                2.8 GB  [Sicuro]
 -- ⚙️ Sistema macOS & RAM --
 [X] Cestino macOS (~/.Trash)                        416.8 MB  [Sicuro]
 [X] Log Utente & DiagnosticReports                   39.1 MB  [Sicuro]
 [X] Time Machine Local Snapshots                         0 B  [Sicuro]
 [X] Termina Demoni Gradle/Kotlin in RAM                  0 B  [Sicuro]
 [X] macOS Purge RAM                                      0 B  [Sicuro]
 -- ⚠️ Operazioni Avanzate (Opt-in) --
 [ ] Reset Totale Simulatori iOS                          0 B  [Attenzione]
--------------------------------------------------------------------------------
 ℹ️  Descrizione: Build cache intermedie dei progetti Xcode e Flutter iOS.
 Selezionati: 18/22  |  Spazio stimato recuperabile: 33.8 GB
 [↑/↓] Naviga  [Spazio] Seleziona  [a] Tutti  [n] Nessuno  [d] Dry-run  [s] Riscansiona  [Invio] Esegui  [q] Esci
```

### Comandi da Tastiera nella TUI:
- **`↑ / ↓`** (oppure **`k / j`**): Naviga tra i moduli.
- **`Spazio`**: Abilita o disabilita il modulo evidenziato `[X]` / `[ ]`.
- **`a`**: Seleziona tutti i moduli raccomandati e sicuri.
- **`n`**: Deseleziona tutti i moduli.
- **`d`**: Alterna tra modalità **Simulazione (Dry-run)** ed **Esecuzione Reale**.
- **`s`**: Avvia una nuova scansione in background delle dimensioni.
- **`Invio`**: Mostra il prompt di conferma ed esegue la pulizia.
- **`q`** o **`Esc`**: Esci senza apportare alcuna modifica.

---

## 🧹 Tutti i Moduli di Pulizia Supportati (22 Moduli)

| Categoria | ID Modulo | Descrizione | Livello Rischio | Default |
| :--- | :--- | :--- | :--- | :--- |
| **🍎 iOS & Xcode** | `deriveddata` | Build cache intermedie di Xcode e Flutter iOS (`~/Library/Developer/Xcode/DerivedData`) | `[Consigliato]` | **Attivo** |
| | `archives` | Vecchi archivi `.xcarchive` più vecchi di 30 giorni (`~/Library/Developer/Xcode/Archives`) | `[Sicuro]` | **Attivo** |
| | `devicesupport` | Simboli di debug di vecchi dispositivi fisici iOS (`~/Library/Developer/Xcode/iOS DeviceSupport`) | `[Sicuro]` | **Attivo** |
| | `xcode_cache` | Cache di indicizzazione e documentazione temporanea di Xcode IDE | `[Sicuro]` | **Attivo** |
| | `simulators` | Rimuove runtime e dispositivi non disponibili (`xcrun simctl`) e svuota la cache CoreSimulator | `[Consigliato]` | **Attivo** |
| | `swiftpm` | Cache globale di clone e build dei pacchetti SwiftPM (`~/Library/Caches/org.swift.swiftpm`) | `[Sicuro]` | **Attivo** |
| **📦 Package Managers** | `brew` | Cache download vecchi pacchetti e formule (`brew cleanup --prune=all`) | `[Sicuro]` | **Attivo** |
| | `cocoapods` | Cache archivio tarball pod scaricati (`~/Library/Caches/CocoaPods`) | `[Sicuro]` | **Attivo** |
| | `npm` | Cache pacchetti JavaScript Node (`~/.npm`, `~/.yarn/cache`, `~/.pnpm-store`) | `[Sicuro]` | **Attivo** |
| | `gradle` | Cache di build e artefatti di Android e Gradle (`~/.gradle/caches`, `~/.android/cache`) | `[Sicuro]` | **Attivo** |
| | `pip` | Cache download wheel e tarball Python (`~/Library/Caches/pip`, `~/.cache/uv`) | `[Sicuro]` | **Attivo** |
| | `flutter` | Cache repository git clonati da Flutter/Dart (`~/.pub-cache/git`) | `[Sicuro]` | Disattivo |
| **💻 Editor & Docker** | `vscode` | Versioni obsolete e duplicate delle estensioni in `~/.vscode/extensions` | `[Sicuro]` | **Attivo** |
| | `docker` | Prune di container fermi, immagini orfane, volumi non associati e build cache | `[Attenzione]` | Disattivo |
| **🌐 App & Browser** | `spotify` | Cache locale dei brani in streaming in `~/Library/Caches/com.spotify.client` *(account intatto)* | `[Sicuro]` | **Attivo** |
| | `browser` | File temporanei di cache di Brave, Google Chrome e Safari *(cookie/password intatti)* | `[Sicuro]` | **Attivo** |
| **⚙️ Sistema & RAM** | `trash` | Svuotamento definitivo del Cestino utente (`~/.Trash`) | `[Sicuro]` | **Attivo** |
| | `logs` | File di log applicativi e report di crash archiviati in `~/Library/Logs` | `[Sicuro]` | **Attivo** |
| | `snapshots` | Assottigliamento degli snapshot locali APFS di Time Machine via `tmutil` | `[Sicuro]` | **Attivo** |
| | `daemons` | Chiusura dei processi inattivi `GradleDaemon` e `KotlinCompileDaemon` in RAM | `[Sicuro]` | **Attivo** |
| | `ram_purge` | Rilascio della memoria disco inattiva tramite comando di sistema `purge` | `[Sicuro]` | **Attivo** |
| **⚠️ Avanzate** | `simulators_erase` | Reset totale alle impostazioni di fabbrica di tutti i simulatori (`xcrun simctl erase all`) | `[Attenzione]` | Disattivo |

---

## 🚀 Utilizzo Rapido

### 1. Avvio Interattivo (TUI)
```bash
./clean_mac.py
# oppure
make tui
```

### 2. Simulazione Rapida in CLI (Dry-Run)
```bash
./clean_mac.py --dry-run
# oppure
make dry-run
```

### 3. Esecuzione Automatica Diretta (senza prompt)
```bash
./clean_mac.py --yes
# oppure
make clean-auto
```

### 4. Pulizia Selettiva di Moduli Specifici
```bash
# Esegui solo DerivedData, Homebrew e Cestino in simulazione:
./clean_mac.py --only deriveddata,brew,trash --dry-run

# Salta moduli specifici (es. non toccare Spotify né Browser):
./clean_mac.py --skip spotify,browser --dry-run
```

### 5. Elenco Completo Moduli da CLI
```bash
./clean_mac.py --list
```

---

## 📚 Guide e Strategie Avanzate per Mac Apple Silicon

Oltre allo script di pulizia, in questa repository trovi le strategie più efficaci per far rendere al massimo un Mac M1/M2/M3 con 8 GB di RAM:

1. **[Guida simslim per il Simulatore iOS](guida_simslim.md)**:  
   Disabilita ~170 demoni `launchd` non essenziali all'interno del simulatore, abbattendo l'assorbimento da **3.5 GB a meno di 900 MB di RAM**.
   ```bash
   make simslim-on
   ```

2. **[Guida Disabilitare Apple Intelligence](guida_disabilitare_apple_intelligence.md)**:  
   Elimina i modelli locali e disattiva i demoni `intelligenceplatformd` e `modelmanagerd` tramite `RemoveMacAI`, recuperando **oltre 12 GB di SSD** (fondamentali per lo swap) e **1.5 GB di RAM unificata**.
   ```bash
   make remove-ai
   ```

3. **Time Machine Local Snapshots Thinning:**  
   Su macOS gli snapshot APFS possono congelare fino a 40 GB senza comparire nelle dimensioni delle singole cartelle. Il modulo `snapshots` esegue automaticamente `tmutil thinlocalsnapshots` per restituirli al sistema operativo.

4. **RAM Purge:**  
   macOS mantiene in memoria file e cache inattive che non sempre rilascia celermente quando si avvia un tool pesante come Xcode o l'emulatore Android. Il modulo `ram_purge` esegue la syscall `purge` per restituire RAM fisica immediatamente disponibile.

---

## 🔒 Sicurezza e Integrità

Lo script rispetta rigorosamente i seguenti principi:
- **Nessuna perdita di credenziali:** Non tocca token Git, portachiavi Keychain, chiavi SSH, profili browser, password salvate, cronologie o sessioni di accesso.
- **Isolamento della cache:** I percorsi browser e Spotify targettizzano esclusivamente `~/Library/Caches/`, lasciando invariata `~/Library/Application Support/`.
- **Dry-Run per verificare tutto prima:** Puoi sempre visualizzare esattamente ogni singolo file e byte prima di eliminarlo con il tasto `d` o il flag `--dry-run`.
