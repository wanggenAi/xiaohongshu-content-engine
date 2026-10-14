import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from .editorial import validate_public
from .models import ContentPerformance
from .pipeline import Pipeline

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
inbox = typer.Typer()
performance = typer.Typer()
app.add_typer(inbox, name="inbox")
app.add_typer(performance, name="performance")
Root = Annotated[Path, typer.Option(help="Directory containing config/ and data/")]
Limit = Annotated[int, typer.Option(min=1, max=30)]


@app.command()
def collect(root: Root = Path(".")):
    typer.echo(json.dumps(Pipeline(root).collect(), ensure_ascii=False, indent=2))


@app.command()
def rank(root: Root = Path("."), limit: Limit = 20):
    for index, item in enumerate(Pipeline(root).rank(limit), 1):
        typer.echo(f"{index:02d}  {item.score:6.2f}  {item.title}")


@app.command()
def export(root: Root = Path("."), limit: Limit = 20):
    typer.echo(str(Pipeline(root).export(limit)))


@app.command()
def run(root: Root = Path("."), limit: Limit = 20):
    typer.echo(json.dumps(Pipeline(root).run(limit), ensure_ascii=False, indent=2))


@inbox.command("add")
def inbox_add(
    url: str,
    root: Root = Path("."),
    title: str | None = None,
    note: str | None = None,
    author: str | None = None,
    published_at: str | None = None,
):
    if published_at:
        value = datetime.fromisoformat(published_at)
        if value.tzinfo is None:
            raise typer.BadParameter("published-at must include a timezone")
    typer.echo(
        Pipeline(root).store.add_inbox(
            url, title=title, note=note, author=author, published_at=published_at
        )
    )


@performance.command("add")
def performance_add(file: Path, root: Root = Path(".")):
    record = ContentPerformance.model_validate_json(file.read_text(encoding="utf-8"))
    Pipeline(root).store.save_performance(record)
    typer.echo(record.id)


@app.command("check-public")
def check_public(file: Path, root: Root = Path(".")):
    """Check an eventual human/ChatGPT-written public draft before publication."""
    validate_public(file.read_text(encoding="utf-8"), Pipeline(root).style)
    typer.echo("public platform policy: PASS")


if __name__ == "__main__":
    app()
