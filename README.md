# 🚀 Mac Developer Optimizer & Cleaner

> Suite di ottimizzazione, manutenzione e pulizia profonda per **macOS (Apple Silicon M1/M2/M3/M4 & Intel)**.  
> Progettata per sviluppatori mobile e web (**iOS, Xcode, Flutter, Android, Node/NPM, Docker, VS Code, Homebrew**), in particolare su macchine con risorse limitate (es. **MacBook 8 GB RAM / 256 GB SSD**).

---

## ⚡ In Sintesi: Cosa fa questa repository

1. **Architettura Modulare con Terminal UI basata su `Textual`:**  
   Il progetto è strutturato come un pacchetto Python modulare in `src/mac_optimizer/` con gestione delle dipendenze tramite **`uv`**.
   La nuova Terminal UI è sviluppata con la libreria **Textual**, garantendo interfaccia moderna, reattiva e calcolo delle dimensioni in background tramite worker asincroni.
2. **Terminal UI Interattiva (TUI):**  
   All'avvio mostra l'elenco delle attività di pulizia divise in **categorie**, tutte **attive di default con checkmark `[✔]`**.
   - Navigazione fluida con i tasti freccia **`↑ / ↓`**.
   - Con la **barra spaziatrice** puoi disabilitare o riattivare le opzioni.
   - **Selezione persistente:** le tue scelte vengono salvate automaticamente in `~/.config/mac-optimizer/config.json` e ricordate alle esecuzioni successive.
   - **Dry-Run integrato:** premi **`d`** per alternare in tempo reale tra simulazione sicura ed esecuzione effettiva.
3. **Suite Completa di Test Automatici con `pytest`:**  
   Ogni categoria e modulo dispone di test dedicati in `tests/` (33 test unitari e headless TUI) per garantire che nel tempo nessun comando o percorso si rompa.
4. **Gestione Intelligente dei Simulatori iOS:**  
   Rileva automaticamente tutti i runtime e i simulatori installati tramite `xcrun simctl`. Mantiene sempre intatta **l'ultima versione attiva** (es. iOS 27.0) ed elimina in sicurezza i runtime precedenti obsoleti (es. iOS 26.5) e i relativi simulatori virtuali associati, recuperando tipicamente **oltre 12 GB** di spazio SSD.
5. **Xcode Archives Completi:**  
   Elimina **tutti** gli archivi `.xcarchive` accumulati senza mantenere versioni storiche, liberando subito fino a decine di gigabyte.
6. **Guide di Ottimizzazione RAM di Sistema:**  
   - [`guida_simslim.md`](guida_simslim.md): Riduzione RAM del Simulatore iOS da **3.5 GB a < 900 MB**.  
   - [`guida_disabilitare_apple_intelligence.md`](guida_disabilitare_apple_intelligence.md): Recupero di **> 12 GB SSD** e **1.5 GB RAM** disattivando i modelli AI locali su macOS 15+.

---

## 🖥️ Terminal UI (TUI) Interattiva

Lanciando `./clean_mac.py` in un terminale, si avvia direttamente l'interfaccia interattiva:

```text
================================================================================
 🧹 Mac Developer Optimizer & Cleaner 
 Disco: 34.0 GB liberi su 228.0 GB (85.1% usato)  |  Modalità: [✔] 🔍 DRY-RUN (Simulazione)
--------------------------------------------------------------------------------
  (Usa [↑/↓] per muoverti, [Spazio] per abilitare/disabilitare, [d] Dry-run, [Invio] Avvia)

  ▸ 🍎 Sviluppo iOS & macOS
❯ [✔] Xcode DerivedData                                21.8 GB  [Consigliato]
  [✔] Xcode Archives (TUTTI gli archivi)              837.3 MB  [Sicuro]
  [✔] Xcode iOS DeviceSupport                              0 B  [Sicuro]
  [✔] Xcode IDE Caches & Documentazione                 3.1 MB  [Sicuro]
  [✔] Vecchi Simulatori iOS (Mantiene solo iOS 27.0)    12.0 GB  [Consigliato]
  [✔] Swift Package Manager Cache                     946.6 MB  [Sicuro]
  ▸ 📦 Package Managers & SDK
  [✔] Homebrew Cache & Bottles                         92.3 MB  [Sicuro]
  [✔] CocoaPods Cache                                 442.9 MB  [Sicuro]
  [✔] Node / NPM / Yarn / PNPM Caches                   1.4 GB  [Sicuro]
  [✔] Gradle & Android Build Caches                   896.2 MB  [Sicuro]
  [✔] Python / Pip / UV Cache                           1.1 GB  [Sicuro]
  [✔] Flutter & Dart Pub Git Cache                         0 B  [Sicuro]
  ▸ 💻 Editor & Strumenti
  [✔] VS Code: Estensioni Obsolete                         0 B  [Sicuro]
  [ ] Docker System Prune                                  0 B  [Attenzione]
  ▸ 🌐 Cache App & Browser
  [✔] Spotify Streaming Cache                           3.9 GB  [Sicuro]
  [✔] Browser Web Caches (Brave, Chrome, Safari)        2.8 GB  [Sicuro]
  ▸ ⚙️ Sistema macOS & RAM
  [✔] Cestino macOS (~/.Trash)                        416.8 MB  [Sicuro]
  [✔] Log Utente & Crash Reports                       39.1 MB  [Sicuro]
  [✔] Time Machine Local Snapshots                         0 B  [Sicuro]
  [✔] Termina Demoni Gradle/Kotlin in RAM                  0 B  [Sicuro]
  [✔] macOS Purge RAM (svuota cache inattiva)              0 B  [Sicuro]
  ▸ ⚠️ Operazioni Avanzate (Opt-in)
  [ ] Reset Totale Simulatori iOS                          0 B  [Attenzione]
--------------------------------------------------------------------------------
ℹ️  Descrizione: Build cache intermedie dei progetti Xcode e Flutter iOS.
Totale selezionato: 33.9 GB (20/22 moduli attivi)
[↑/↓] Naviga  [Spazio] Attiva/Disattiva  [a] Tutti  [n] Nessuno  [d] Dry-run  [Invio] Esegui  [q] Esci
```

### Comandi da Tastiera nella TUI:
- **`↑ / ↓`** (oppure **`k / j`**): Naviga tra i moduli (salta automaticamente i titoli di categoria).
- **`Spazio`**: Attiva o disattiva il modulo evidenziato `[✔]` / `[ ]` (salvando subito la preferenza).
- **`a`**: Seleziona tutti i moduli raccomandati e sicuri.
- **`n`**: Deseleziona tutti i moduli.
- **`d`**: Alterna tra modalità **Simulazione (Dry-run)** ed **Esecuzione Reale**.
- **`s`**: Riavvia la scansione in background delle dimensioni.
- **`Invio`**: Esegue la pulizia dei moduli selezionati con resoconto finale.
- **`q`** o **`Esc`**: Esci senza apportare modifiche.

---

## 🧹 Tutti i Moduli di Pulizia Supportati (22 Moduli)

| Categoria | ID Modulo | Descrizione | Livello Rischio | Default |
| :--- | :--- | :--- | :--- | :--- |
| **🍎 iOS & Xcode** | `deriveddata` | Build cache intermedie di Xcode e Flutter iOS (`~/Library/Developer/Xcode/DerivedData`) | `[Consigliato]` | **Attivo [✔]** |
| | `archives` | **TUTTI** gli archivi `.xcarchive` generati (`~/Library/Developer/Xcode/Archives`) | `[Sicuro]` | **Attivo [✔]** |
| | `devicesupport` | Simboli di debug di dispositivi fisici iOS connessi in passato | `[Sicuro]` | **Attivo [✔]** |
| | `xcode_cache` | Cache di indicizzazione e documentazione temporanea di Xcode IDE | `[Sicuro]` | **Attivo [✔]** |
| | `simulators` | Rimuove i vecchi runtime obsoleti e simulatori associati, conservando solo l'ultima versione (es. iOS 27.0) | `[Consigliato]` | **Attivo [✔]** |
| | `swiftpm` | Cache globale di clone e build dei pacchetti SwiftPM (`~/Library/Caches/org.swift.swiftpm`) | `[Sicuro]` | **Attivo [✔]** |
| **📦 Package Managers** | `brew` | Cache download vecchi pacchetti e formule (`brew cleanup --prune=all`) | `[Sicuro]` | **Attivo [✔]** |
| | `cocoapods` | Cache archivio tarball pod scaricati (`~/Library/Caches/CocoaPods`) | `[Sicuro]` | **Attivo [✔]** |
| | `npm` | Cache pacchetti JavaScript Node (`~/.npm`, `~/.yarn/cache`, `~/.pnpm-store`) | `[Sicuro]` | **Attivo [✔]** |
| | `gradle` | Cache di build e artefatti di Android e Gradle (`~/.gradle/caches`, `~/.android/cache`) | `[Sicuro]` | **Attivo [✔]** |
| | `pip` | Cache download wheel e tarball Python (`~/Library/Caches/pip`, `~/.cache/uv`) | `[Sicuro]` | **Attivo [✔]** |
| | `flutter` | Cache repository git clonati da Flutter/Dart (`~/.pub-cache/git`) | `[Sicuro]` | **Attivo [✔]** |
| **💻 Editor & Strumenti** | `vscode` | Versioni obsolete e duplicate delle estensioni in `~/.vscode/extensions` | `[Sicuro]` | **Attivo [✔]** |
| | `docker` | Prune di container fermi, immagini orfane, volumi non associati e build cache | `[Attenzione]` | Disattivo [ ] |
| **🌐 App & Browser** | `spotify` | Cache locale dei brani in streaming in `~/Library/Caches/com.spotify.client` *(account intatto)* | `[Sicuro]` | **Attivo [✔]** |
| | `browser` | File temporanei di cache di Brave, Google Chrome e Safari *(cookie/password intatti)* | `[Sicuro]` | **Attivo [✔]** |
| **⚙️ Sistema & RAM** | `trash` | Svuotamento definitivo del Cestino utente (`~/.Trash`) | `[Sicuro]` | **Attivo [✔]** |
| | `logs` | File di log applicativi e report di crash archiviati in `~/Library/Logs` | `[Sicuro]` | **Attivo [✔]** |
| | `snapshots` | Assottigliamento degli snapshot locali APFS di Time Machine via `tmutil` | `[Sicuro]` | **Attivo [✔]** |
| | `daemons` | Chiusura dei processi inattivi `GradleDaemon` e `KotlinCompileDaemon` in RAM | `[Sicuro]` | **Attivo [✔]** |
| | `ram_purge` | Rilascio della memoria disco inattiva tramite comando di sistema `purge` | `[Sicuro]` | **Attivo [✔]** |
| **⚠️ Avanzate** | `simulators_erase` | Reset totale alle impostazioni di fabbrica di tutti i simulatori (`xcrun simctl erase all`) | `[Attenzione]` | Disattivo [ ] |

---

## 🚀 Utilizzo Rapido

### 1. Avvio Interattivo con Checkmark (TUI)
```bash
./clean_mac.py
# oppure:
make tui
```

### 2. Simulazione Rapida in CLI (Dry-Run)
```bash
./clean_mac.py --dry-run
# oppure:
make dry-run
```

### 3. Esecuzione Automatica Diretta (senza prompt)
```bash
./clean_mac.py --yes
# oppure:
make clean-auto
```

### 4. Pulizia Selettiva di Moduli Specifici
```bash
# Esegui solo DerivedData, Archivi e Cestino in simulazione:
./clean_mac.py --only deriveddata,archives,trash --dry-run

# Salta moduli specifici:
./clean_mac.py --skip spotify,browser --dry-run
```

### 5. Elenco Completo Moduli da CLI
```bash
./clean_mac.py --list
```

---

## 🔒 Sicurezza, Integrità e Persistenza

- **Selezione Salvata:** Ogni modifica apportata con la barra spaziatrice viene registrata in `~/.config/mac-optimizer/config.json`. La volta successiva ritroverai esattamente le tue impostazioni personalizzate.
- **Nessuna perdita di credenziali:** Non tocca token Git, portachiavi Keychain, chiavi SSH, profili browser, password salvate, cronologie o sessioni di accesso.
- **Isolamento della cache:** I percorsi browser e Spotify targettizzano esclusivamente `~/Library/Caches/`, lasciando invariata `~/Library/Application Support/`.
- **Dry-Run per verificare tutto prima:** Puoi sempre visualizzare esattamente ogni singolo file e byte prima di eliminarlo con il tasto `d` o il flag `--dry-run`.

---

## 🛠️ Sviluppo, Gestione Dipendenze con `uv` e Test

Il progetto adotta **`uv`** come package manager veloce e moderno per Python.

### Installazione e Sincronizzazione Dipendenze
```bash
uv sync
# oppure:
make sync
```

### Esecuzione Test Automatici (33 Test)
Per verificare che tutti i moduli di pulizia, il parser simulatori, la deduplicazione estensioni e la TUI funzionino correttamente nel tempo:
```bash
uv run pytest
# oppure con output dettagliato:
make test
```

### Struttura del Progetto
```text
mac-optimizer/
├── pyproject.toml              # Definizione progetto e dipendenze uv (textual, rich, pytest)
├── uv.lock                     # Lockfile deterministico uv
├── Makefile                    # Target make per tui, dry-run, test, sync, ecc.
├── clean_mac.py                # Script di avvio compatibile CLI / TUI
├── src/
│   └── mac_optimizer/
│       ├── models.py           # Dataclass ModuleDef, CleanResult, RiskLevel
│       ├── utils.py            # Calcolo dimensioni, comandi shell sicuri, info disco
│       ├── config.py           # Persistenza selezioni (~/.config/mac-optimizer/config.json)
│       ├── registry.py         # Registro e categorie dei 22 moduli
│       ├── cli.py              # Runner riga di comando e tabelle Rich
│       ├── modules/            # Moduli indipendenti per ciascuna categoria
│       │   ├── xcode.py        # DerivedData, Archives (tutti), DeviceSupport, Cache IDE
│       │   ├── simulators.py   # Rilevamento runtime simctl, eliminazione obsoleti, keep newest
│       │   ├── package_managers.py # Homebrew, SPM, CocoaPods, NPM, Gradle, Pip/UV, Flutter
│       │   ├── developer_tools.py  # VS Code estensioni duplicate, Docker prune
│       │   ├── apps.py         # Spotify cache, Browser cache (Brave, Chrome, Safari)
│       │   └── system.py       # Cestino, Log, Snapshots APFS, Demoni Java, Purge RAM
│       └── tui/
│           ├── app.py          # Applicazione Terminal UI moderna basata su Textual
│           └── screens.py      # Schermata di esecuzione live e streaming risultati
└── tests/                      # Suite di test unitari e headless TUI (pytest)
    ├── test_utils.py
    ├── test_config.py
    ├── test_registry.py
    ├── test_modules_xcode.py
    ├── test_modules_simulators.py
    ├── test_modules_package_managers.py
    ├── test_modules_developer_tools.py
    ├── test_modules_apps.py
    ├── test_modules_system.py
    ├── test_tui.py
    └── test_cli.py
```
