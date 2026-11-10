"""
tui/app.py - Applicazione principale Terminal UI interattiva con Textual.
Supporta navigazione con frecce, selezione con barra spaziatrice, categorie,
calcolo asincrono delle dimensioni in background e persistenza configurazione.
"""

from typing import List, Dict, Optional
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, SelectionList, Static, Label
from textual.widgets.selection_list import Selection
from rich.text import Text

from mac_optimizer.models import ModuleDef
from mac_optimizer.utils import format_bytes, get_disk_free_info
from mac_optimizer.config import save_module_selections, load_config
from mac_optimizer.tui.screens import ExecutionScreen


class MacOptimizerApp(App):
    """Applicazione TUI moderna per ottimizzazione e pulizia macOS."""

    TITLE = "Mac Developer Optimizer & Cleaner"
    SUB_TITLE = "Ottimizzazione disco e RAM per sviluppatori"

    BINDINGS = [
        ("d", "toggle_dry_run", "Dry-Run (d)"),
        ("a", "select_all", "Seleziona Tutti (a)"),
        ("n", "select_none", "Deseleziona Tutti (n)"),
        ("s", "rescan", "Riscansiona (s)"),
        ("enter", "run_cleaning", "Esegui (Invio)"),
        ("q", "quit", "Esci (q)"),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    #top_info_bar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
        content-align: center middle;
        border-bottom: solid $primary;
    }
    #disk_label {
        width: 1fr;
        content-align: left middle;
    }
    #mode_label {
        width: auto;
        content-align: right middle;
        text-style: bold;
    }
    #main_container {
        height: 1fr;
        padding: 0 1;
    }
    SelectionList {
        height: 1fr;
        border: solid $secondary;
        padding: 0 1;
    }
    #bottom_info_bar {
        height: 4;
        dock: bottom;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }
    #module_desc {
        height: 2;
        content-align: left middle;
        color: $text-muted;
    }
    #selection_stats {
        height: 1;
        content-align: left middle;
        text-style: bold;
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
        with Horizontal(id="top_info_bar"):
            disk_str = f"💾 Disco: {self.disk_info['free']} liberi su {self.disk_info['total']} ({self.disk_info['percent']} usato)"
            yield Label(disk_str, id="disk_label")
            yield Label(self._get_mode_badge(), id="mode_label")

        with Container(id="main_container"):
            sl = SelectionList[str]()
            self._populate_selection_list(sl)
            yield sl

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
            return "[bold yellow]🔍 MODALITÀ: DRY-RUN (Simulazione)[/]"
        return "[bold green]⚡ MODALITÀ: ESECUZIONE REALE[/]"

    def _get_selection_stats_text(self) -> str:
        sel_count = sum(1 for m in self.modules if m.selected)
        sel_bytes = sum(m.estimated_bytes for m in self.modules if m.selected)
        return f"Totale selezionato: [bold cyan]{format_bytes(sel_bytes)}[/] ({sel_count}/{len(self.modules)} moduli attivi)"

    def _build_option_prompt(self, m: ModuleDef) -> Text:
        """Costruisce il testo Rich formattato per un modulo nella lista."""
        if m.scan_done:
            sz_str = f"{format_bytes(m.estimated_bytes):>9}"
        else:
            sz_str = " (calcolo)"

        if m.risk_level == "caution":
            risk_badge = "[Attenzione]"
            risk_style = "yellow"
        elif m.risk_level == "recommended":
            risk_badge = "[Consigliato]"
            risk_style = "cyan"
        else:
            risk_badge = "[Sicuro]"
            risk_style = "green"

        prompt = Text()
        prompt.append(f"{m.name:<48}", style="bold" if m.selected else "")
        prompt.append("  ")
        prompt.append(sz_str, style="bold green" if m.scan_done and m.estimated_bytes > 0 else "dim")
        prompt.append("  ")
        prompt.append(risk_badge, style=risk_style)
        return prompt

    def _populate_selection_list(self, sl: SelectionList[str]) -> None:
        """Inserisce categorie (disabilitate) e moduli nella SelectionList."""
        categories: Dict[str, List[ModuleDef]] = {}
        for m in self.modules:
            categories.setdefault(m.category, []).append(m)

        for cat_name, cat_modules in categories.items():
            cat_prompt = Text(f"▸ {cat_name}", style="bold magenta")
            sl.add_option(Selection(cat_prompt, f"cat_{cat_name}", disabled=True))
            for m in cat_modules:
                prompt = self._build_option_prompt(m)
                sl.add_option(Selection(prompt, m.id, initial_state=m.selected, id=m.id))

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        """Aggiorna lo stato dei moduli quando la selezione cambia."""
        selected_set = set(event.selection_list.selected)
        for m in self.modules:
            m.selected = (m.id in selected_set)

        save_module_selections(self.modules, self.dry_run)
        self.query_one("#selection_stats", Label).update(self._get_selection_stats_text())

    def on_selection_list_selection_highlighted(self, event: SelectionList.SelectionHighlighted) -> None:
        """Aggiorna la descrizione in basso quando il cursore si sposta."""
        sel = getattr(event, "selection", None)
        if not sel:
            return
        val = getattr(sel, "value", None)
        if val in self.modules_by_id:
            m = self.modules_by_id[val]
            self.query_one("#module_desc", Static).update(f"ℹ️  {m.description}")
        elif isinstance(val, str) and val.startswith("cat_"):
            cat_name = val[4:]
            self.query_one("#module_desc", Static).update(f"📁 Categoria: {cat_name}")

    @work(thread=True)
    def scan_sizes_worker(self) -> None:
        """Worker in background per calcolare le dimensioni senza bloccare l'UI."""
        sl = self.query_one(SelectionList)
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
            self.call_from_thread(sl.replace_option_prompt, m.id, new_prompt)
            self.call_from_thread(self._refresh_stats)

    def _refresh_stats(self) -> None:
        self.query_one("#selection_stats", Label).update(self._get_selection_stats_text())

    def action_toggle_dry_run(self) -> None:
        """Alterna tra modalità simulazione (dry-run) ed esecuzione effettiva."""
        self.dry_run = not self.dry_run
        save_module_selections(self.modules, self.dry_run)
        self.query_one("#mode_label", Label).update(self._get_mode_badge())

    def action_select_all(self) -> None:
        """Seleziona tutti i moduli raccomandati e sicuri."""
        sl = self.query_one(SelectionList)
        for m in self.modules:
            if m.risk_level in ("safe", "recommended"):
                sl.select(m.id)
                m.selected = True

    def action_select_none(self) -> None:
        """Deseleziona tutti i moduli."""
        sl = self.query_one(SelectionList)
        for m in self.modules:
            sl.deselect(m.id)
            m.selected = False

    def action_rescan(self) -> None:
        """Riavvia la scansione in background delle dimensioni."""
        for m in self.modules:
            m.scan_done = False
        self.scan_sizes_worker()

    def action_run_cleaning(self) -> None:
        """Avvia la schermata di esecuzione dei moduli selezionati."""
        selected = [m for m in self.modules if m.selected]
        if not selected:
            self.notify("Nessun modulo selezionato per la pulizia!", severity="warning")
            return
        self.push_screen(ExecutionScreen(selected, self.dry_run))
