"""
tui/screens.py - Schermi dedicati dell'interfaccia Textual (es. esecuzione pulizia in tempo reale).
"""

from typing import List
from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, RichLog, ProgressBar, Label
from textual.containers import Vertical, Container
from rich.text import Text
from mac_optimizer.models import ModuleDef, CleanResult
from mac_optimizer.utils import format_bytes


class ExecutionScreen(Screen):
    """Schermo di esecuzione della pulizia con output in streaming."""

    BINDINGS = [
        ("enter", "finish", "Torna / Esci"),
        ("q", "finish", "Esci"),
        ("escape", "finish", "Indietro"),
    ]

    DEFAULT_CSS = """
    ExecutionScreen {
        layout: vertical;
        background: $background;
    }
    #exec_header {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
        content-align: center middle;
    }
    #progress_container {
        height: 3;
        margin: 1 2;
    }
    #exec_log {
        height: 1fr;
        border: solid $primary;
        margin: 0 2 1 2;
        background: $surface;
    }
    #status_label {
        height: 2;
        content-align: center middle;
        text-style: bold;
    }
    """

    def __init__(self, modules_to_run: List[ModuleDef], dry_run: bool) -> None:
        super().__init__()
        self.modules_to_run = modules_to_run
        self.dry_run = dry_run
        self.completed = False
        self.total_freed_bytes = 0

    def compose(self) -> ComposeResult:
        yield Header()
        mode_str = "[DRY-RUN] Simulazione attiva" if self.dry_run else "[REALE] Esecuzione effettiva"
        yield Label(f"🧹 Pulizia Sistema macOS - Modalità: {mode_str}", id="exec_header")
        with Container(id="progress_container"):
            yield ProgressBar(total=len(self.modules_to_run), show_eta=False, id="pbar")
        yield RichLog(id="exec_log", highlight=True, markup=True)
        yield Label("Esecuzione in corso...", id="status_label")
        yield Footer()

    def on_mount(self) -> None:
        self.run_clean_worker()

    @work(thread=True)
    def run_clean_worker(self) -> None:
        log = self.query_one(RichLog)
        pbar = self.query_one(ProgressBar)
        status = self.query_one("#status_label", Label)

        header_tag = "[bold yellow]🔍 SIMULAZIONE DRY-RUN[/]" if self.dry_run else "[bold green]⚡ ESECUZIONE REALE[/]"
        log.write(f"\n{header_tag} - Avvio pulizia di {len(self.modules_to_run)} moduli selezionati...\n")

        for idx, m in enumerate(self.modules_to_run, 1):
            if not self.is_mounted:
                break
            log.write(f"[bold cyan]▶ [{idx}/{len(self.modules_to_run)}] {m.name}[/]...")
            try:
                res: CleanResult = m.clean_func(self.dry_run)
                self.total_freed_bytes += res.freed_bytes
                for det in res.details:
                    log.write(f"   [dim]•[/] {det}")
            except Exception as e:
                log.write(f"   [bold red]❌ Errore durante l'esecuzione: {e}[/]")

            if self.is_mounted:
                self.app.call_from_thread(pbar.advance, 1)

        summary_msg = f"[bold green]✔ Operazione completata![/] Spazio recuperato / stimato: [bold cyan]{format_bytes(self.total_freed_bytes)}[/]"
        log.write("\n" + "=" * 60)
        log.write(summary_msg)
        log.write("[bold yellow]Premi [Invio] o [q] per terminare.[/]\n")

        self.completed = True
        if self.is_mounted:
            self.app.call_from_thread(status.update, "Completato! Premi [Invio] o [q] per uscire.")

    def action_finish(self) -> None:
        self.dismiss(self.total_freed_bytes)
