import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from .editorial import validate_public
from .models import ContentPerformance, EditorialFeedback
from .pipeline import Pipeline

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
inbox = typer.Typer()
performance = typer.Typer()
review = typer.Typer()
app.add_typer(inbox, name="inbox")
app.add_typer(performance, name="performance")
app.add_typer(review, name="review")
Root = Annotated[Path, typer.Option(help="Directory containing config/ and data/")]
Limit = Annotated[int, typer.Option(min=1, max=30)]


@app.command()
def collect(root: Root = Path(".")):
    typer.echo(json.dumps(Pipeline(root).collect(), ensure_ascii=False, indent=2))


@app.command()
def rank(root: Root = Path("."), limit: Limit = 10):
    for index, item in enumerate(Pipeline(root).rank(limit), 1):
        typer.echo(
            f"{index:02d}  {item.editorial_verdict}  "
            f"editorial={item.editorial_score:.2f} discovery={item.discovery_score:.2f}  "
            f"{item.editorial_title_seed}"
        )


@app.command()
def export(root: Root = Path("."), limit: Limit = 10):
    typer.echo(str(Pipeline(root).export(limit)))


@app.command()
def run(root: Root = Path("."), limit: Limit = 10):
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


@review.command("add")
def review_add(file: Path, root: Root = Path(".")):
    data = json.loads(file.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else [data]
    # Validate the whole batch before persisting any feedback.
    feedback = [EditorialFeedback.model_validate(row) for row in records]
    store = Pipeline(root).store
    for record in feedback:
        store.save_editorial_feedback(record)
    typer.echo(f"saved {len(feedback)} editorial reviews")


@review.command("list")
def review_list(root: Root = Path("."), candidate_id: str | None = None):
    typer.echo(
        json.dumps(
            [
                r.model_dump(mode="json")
                for r in Pipeline(root).store.editorial_feedback(candidate_id)
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("check-public")
def check_public(file: Path, root: Root = Path(".")):
    """Check an eventual human/ChatGPT-written public draft before publication."""
    validate_public(file.read_text(encoding="utf-8"), Pipeline(root).style)
    typer.echo("public platform policy: PASS")


if __name__ == "__main__":
    app()
