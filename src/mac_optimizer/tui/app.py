"""
tui/app.py - Applicazione principale Terminal UI interattiva basata su Textual.
Offre una grafica scura ad altissimo contrasto (stile tokyo-night/dracula),
con checkmark [✔] verdi brillanti, categorie evidenziate, navigazione fluida e reattiva.
"""

from typing import List, Dict, Optional
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, OptionList, Static, Label
from textual.widgets.option_list import Option
from textual.binding import Binding
from rich.text import Text

from mac_optimizer.models import ModuleDef
from mac_optimizer.utils import format_bytes, get_disk_free_info
from mac_optimizer.config import save_module_selections
from mac_optimizer.tui.screens import ExecutionScreen


class MacOptimizerApp(App):
    """Applicazione TUI moderna ad alto contrasto per ottimizzazione e pulizia macOS."""

    TITLE = "🧹 Mac Developer Optimizer & Cleaner"
    SUB_TITLE = "Ottimizzazione disco e RAM per sviluppatori"
    theme = "tokyo-night"

    BINDINGS = [
        Binding("space", "toggle_selection", "Attiva/Disattiva (Spazio)", priority=True),
        Binding("enter", "run_cleaning", "Esegui Pulizia (Invio)", priority=True),
        Binding("d", "toggle_dry_run", "Dry-Run (d)", priority=True),
        Binding("a", "select_all", "Seleziona Tutti (a)", priority=True),
        Binding("n", "select_none", "Deseleziona Tutti (n)", priority=True),
        Binding("s", "rescan", "Riscansiona (s)", priority=True),
        Binding("escape", "smart_quit", "Indietro / Esci", priority=True),
        Binding("q", "smart_quit", "Esci (q)", priority=True),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
        background: #0d1117;
    }
    #top_info_bar {
        height: 4;
        background: #161b22;
        padding: 0 2;
        border-bottom: solid #30363d;
    }
    #app_banner {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: #58a6ff;
    }
    #status_row {
        height: 2;
        content-align: left middle;
    }
    #disk_label {
        width: auto;
        color: #c9d1d9;
        margin-right: 2;
    }
    #selection_top_label {
        width: 1fr;
        text-style: bold;
        color: #f0f6fc;
    }
    #mode_label {
        width: auto;
        text-style: bold;
    }
    #main_container {
        height: 1fr;
        padding: 0 1;
        background: #0d1117;
    }
    OptionList {
        height: 1fr;
        background: #0d1117;
        border: solid #30363d;
        padding: 0 1;
    }
    OptionList:focus {
        border: solid #58a6ff;
    }
    OptionList > .option-list--option-highlighted {
        background: #1f2937;
        color: #ffffff;
        text-style: bold;
    }
    OptionList > .option-list--option-disabled {
        background: #0d1117;
        color: #ff79c6;
        text-style: bold;
    }
    #bottom_info_bar {
        height: 4;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 2;
    }
    #module_desc {
        height: 1;
        content-align: left middle;
        color: #58a6ff;
    }
    #selection_stats {
        height: 1;
        content-align: left middle;
        text-style: bold;
        color: #f0f6fc;
    }
    """

    def __init__(self, modules: List[ModuleDef], dry_run: bool = True) -> None:
        super().__init__()
        self.modules = modules
        self.modules_by_id: Dict[str, ModuleDef] = {m.id: m for m in modules}
        self.dry_run = dry_run
        self.disk_info = get_disk_free_info()
        self._stop_scan = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="top_info_bar"):
            yield Label(" 🧹 Mac Developer Optimizer & Cleaner ", id="app_banner")
            with Horizontal(id="status_row"):
                disk_str = f"💾 Disco: {self.disk_info['free']} liberi su {self.disk_info['total']} ({self.disk_info['percent']} usato)"
                yield Label(disk_str, id="disk_label")
                yield Label(self._get_selection_top_text(), id="selection_top_label")
                yield Label(self._get_mode_badge(), id="mode_label")

        with Container(id="main_container"):
            ol = OptionList(id="modules_list")
            self._populate_option_list(ol)
            yield ol

        with Vertical(id="bottom_info_bar"):
            first_desc = self.modules[0].description if self.modules else ""
            yield Static(f"ℹ️  {first_desc}", id="module_desc")
            yield Label(self._get_selection_stats_text(), id="selection_stats")

        yield Footer()

    def on_mount(self) -> None:
        self.scan_sizes_worker()

    def on_unmount(self) -> None:
        self._stop_scan = True

    def _get_mode_badge(self) -> str:
        if self.dry_run:
            return "[bold #ffcc00]🔍 MODALITÀ: DRY-RUN (Simulazione)[/]"
        return "[bold #00ff66]⚡ MODALITÀ: ESECUZIONE REALE[/]"

    def _get_selection_top_text(self) -> str:
        sel_count = sum(1 for m in self.modules if m.selected)
        sel_bytes = sum(m.estimated_bytes for m in self.modules if m.selected)
        still_scanning = any(not m.scan_done for m in self.modules)
        scan_tag = " [dim]⏳[/]" if still_scanning else ""
        return f"✨ Da liberare: [bold #00ff66]{format_bytes(sel_bytes)}[/] [dim]({sel_count}/{len(self.modules)})[/]{scan_tag}"

    def _get_selection_stats_text(self) -> str:
        sel_count = sum(1 for m in self.modules if m.selected)
        sel_bytes = sum(m.estimated_bytes for m in self.modules if m.selected)
        still_scanning = any(not m.scan_done for m in self.modules)
        scan_tag = " [dim]⏳ (scansione dimensioni in corso...)[/]" if still_scanning else ""
        return f"Spazio recuperabile stimato: [bold #00ff66]{format_bytes(sel_bytes)}[/] ({sel_count}/{len(self.modules)} moduli selezionati){scan_tag}"

    def _build_option_prompt(self, m: ModuleDef) -> Text:
        """Costruisce il testo Rich formattato ad alto contrasto per un modulo."""
        prompt = Text()

        # Checkmark ad altissimo contrasto: verde brillante o grigio tenue
        if m.selected:
            prompt.append("[✔] ", style="bold #00ff66")
        else:
            prompt.append("[ ] ", style="dim #777777")

        # Nome modulo
        name_style = "bold #ffffff" if m.selected else "#c9d1d9"
        prompt.append(f"{m.name:<48}", style=name_style)
        prompt.append("  ")

        # Dimensione
        if m.scan_done:
            if m.estimated_bytes > 0:
                prompt.append(f"{format_bytes(m.estimated_bytes):>9}", style="bold #00e5ff")
            else:
                prompt.append("      0 B", style="dim #6e7681")
        else:
            prompt.append(" (calcolo)", style="italic dim #8b949e")

        prompt.append("  ")

        # Badge rischio
        if m.risk_level == "caution":
            prompt.append("[Attenzione]", style="bold #ffcc00")
        elif m.risk_level == "recommended":
            prompt.append("[Consigliato]", style="bold #58a6ff")
        else:
            prompt.append("[Sicuro]", style="bold #00ff66")

        return prompt

    def _populate_option_list(self, ol: OptionList) -> None:
        """Inserisce categorie (disabilitate) e moduli nella OptionList."""
        categories: Dict[str, List[ModuleDef]] = {}
        for m in self.modules:
            categories.setdefault(m.category, []).append(m)

        for cat_name, cat_modules in categories.items():
            cat_prompt = Text(f"▸ {cat_name}", style="bold #ff79c6")
            ol.add_option(Option(cat_prompt, id=f"cat_{cat_name}", disabled=True))
            for m in cat_modules:
                prompt = self._build_option_prompt(m)
                ol.add_option(Option(prompt, id=m.id))

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Aggiorna la descrizione in basso quando il cursore si sposta."""
        opt_id = event.option_id
        if opt_id and opt_id in self.modules_by_id:
            m = self.modules_by_id[opt_id]
            self.query_one("#module_desc", Static).update(f"ℹ️  {m.description}")
        elif opt_id and opt_id.startswith("cat_"):
            cat_name = opt_id[4:]
            self.query_one("#module_desc", Static).update(f"📁 Categoria: {cat_name}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Supporta anche il click con il mouse per commutare la selezione."""
        if event.option_id and not event.option_id.startswith("cat_") and event.option_id in self.modules_by_id:
            self.action_toggle_selection(target_id=event.option_id)

    def action_toggle_selection(self, target_id: Optional[str] = None) -> None:
        """Commuta la selezione del modulo evidenziato o cliccato."""
        ol = self.query_one(OptionList)
        if target_id and target_id in self.modules_by_id:
            mod_id = target_id
            try:
                idx = ol.get_option_index(mod_id)
            except Exception:
                idx = ol.highlighted
        else:
            idx = ol.highlighted
            if idx is None:
                return
            opt = ol.get_option_at_index(idx)
            if not opt.id or opt.id.startswith("cat_") or opt.disabled:
                return
            mod_id = opt.id

        if mod_id in self.modules_by_id:
            m = self.modules_by_id[mod_id]
            m.selected = not m.selected
            new_prompt = self._build_option_prompt(m)
            if idx is not None:
                ol.replace_option_prompt_at_index(idx, new_prompt)
            else:
                ol.replace_option_prompt(mod_id, new_prompt)
            save_module_selections(self.modules, self.dry_run)
            self._refresh_stats()

    @work(thread=True)
    def scan_sizes_worker(self) -> None:
        """Worker in background per calcolare le dimensioni senza bloccare l'UI."""
        ol = self.query_one(OptionList)
        for m in self.modules:
            if self._stop_scan:
                break
            try:
                m.estimated_bytes = m.scan_func()
                m.scan_done = True
            except Exception:
                m.estimated_bytes = 0
                m.scan_done = True

            new_prompt = self._build_option_prompt(m)
            self.call_from_thread(self._safe_replace_prompt, m.id, new_prompt)
            self.call_from_thread(self._refresh_stats)

        # Aggiornamento finale a fine scansione
        self.call_from_thread(self._refresh_stats)

    def _safe_replace_prompt(self, mod_id: str, prompt: Text) -> None:
        ol = self.query_one(OptionList)
        try:
            ol.replace_option_prompt(mod_id, prompt)
        except Exception:
            pass

    def _refresh_stats(self) -> None:
        try:
            self.query_one("#selection_stats", Label).update(self._get_selection_stats_text())
        except Exception:
            pass
        try:
            self.query_one("#selection_top_label", Label).update(self._get_selection_top_text())
        except Exception:
            pass

    def action_toggle_dry_run(self) -> None:
        """Alterna tra modalità simulazione (dry-run) ed esecuzione effettiva."""
        self.dry_run = not self.dry_run
        save_module_selections(self.modules, self.dry_run)
        self.query_one("#mode_label", Label).update(self._get_mode_badge())

    def action_select_all(self) -> None:
        """Seleziona tutti i moduli raccomandati e sicuri."""
        ol = self.query_one(OptionList)
        for idx in range(ol.option_count):
            opt = ol.get_option_at_index(idx)
            if opt.id and opt.id in self.modules_by_id:
                m = self.modules_by_id[opt.id]
                if m.risk_level in ("safe", "recommended"):
                    m.selected = True
                    ol.replace_option_prompt_at_index(idx, self._build_option_prompt(m))
        save_module_selections(self.modules, self.dry_run)
        self._refresh_stats()

    def action_select_none(self) -> None:
        """Deseleziona tutti i moduli."""
        ol = self.query_one(OptionList)
        for idx in range(ol.option_count):
            opt = ol.get_option_at_index(idx)
            if opt.id and opt.id in self.modules_by_id:
                m = self.modules_by_id[opt.id]
                m.selected = False
                ol.replace_option_prompt_at_index(idx, self._build_option_prompt(m))
        save_module_selections(self.modules, self.dry_run)
        self._refresh_stats()

    def action_rescan(self) -> None:
        """Riavvia la scansione in background delle dimensioni."""
        for m in self.modules:
            m.scan_done = False
        self.scan_sizes_worker()

    def _refresh_disk_info(self) -> None:
        self.disk_info = get_disk_free_info()
        disk_str = f"💾 Disco: {self.disk_info['free']} liberi su {self.disk_info['total']} ({self.disk_info['percent']} usato)"
        try:
            self.query_one("#disk_label", Label).update(disk_str)
        except Exception:
            pass

    def action_run_cleaning(self) -> None:
        """Avvia la schermata di esecuzione dei moduli selezionati o conferma uscita se già completata."""
        if isinstance(self.screen, ExecutionScreen):
            if self.screen.completed:
                self.screen.action_finish()
            return

        selected = [m for m in self.modules if m.selected]
        if not selected:
            self.notify("Nessun modulo selezionato per la pulizia!", severity="warning")
            return

        def _on_clean_done(freed_bytes: Optional[int] = None) -> None:
            self._refresh_disk_info()
            if not self.dry_run and freed_bytes:
                self.action_rescan()

        self.push_screen(ExecutionScreen(selected, self.dry_run), _on_clean_done)

    def action_smart_quit(self) -> None:
        """Chiude la schermata di esecuzione o esce dall'applicazione."""
        if isinstance(self.screen, ExecutionScreen):
            self.screen.action_finish()
            return
        self.exit()
