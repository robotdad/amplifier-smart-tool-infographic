"""Command line entry point for Infographic."""

from collections.abc import Callable
import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import ValidationError
import typer

# Typer 0.27 vendors Click, so a command that overrides Click's own hooks has to speak the vendored types.
from typer._click import Context, Parameter
from typer.core import TyperCommand, TyperOption
from typer.models import CommandFunctionType

from infographic import lib
from infographic.models import DEFAULT_IMAGE_MODEL, Brief
from infographic.schemas import InfographicError
from infographic.storage import DEFAULT_STORE


class CapabilityCommand(TyperCommand):
    """Every capability answers `-h` with the generated summary and `--help` with its skill from the library."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help_option"] = False
        super().__init__(*args, **kwargs)

    def get_params(self, ctx: Context) -> list[Parameter]:
        def short(ctx: Context, param: Parameter, value: bool) -> None:
            if value and not ctx.resilient_parsing:
                typer.echo(ctx.get_help())
                ctx.exit()

        def capability_skill(ctx: Context, param: Parameter, value: bool) -> None:
            if value and not ctx.resilient_parsing:
                typer.echo(lib.skill(self.name))
                ctx.exit()

        return [
            *super().get_params(ctx),
            TyperOption(
                param_decls=["-h"],
                is_flag=True,
                is_eager=True,
                expose_value=False,
                callback=short,
                help="Terse summary of this capability.",
            ),
            TyperOption(
                param_decls=["--help"],
                is_flag=True,
                is_eager=True,
                expose_value=False,
                callback=capability_skill,
                help="This capability's skill, for an agent about to call it.",
            ),
        ]


class SmartToolTyper(typer.Typer):
    """A Typer whose commands are CapabilityCommand by default, so a capability added later inherits the help split."""

    def command(
        self, *args: Any, cls: type[TyperCommand] = CapabilityCommand, **kwargs: Any
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        return super().command(*args, cls=cls, **kwargs)


app = SmartToolTyper(
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    # `-h` is the terse summary and `--help` is the skill, at both scopes. On the root, the callback's parameter
    # claims `--help` and Click drops a help option name a parameter already took, which leaves the generated
    # summary on `-h`; on a capability, CapabilityCommand splits the two itself.
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _print_skill(value: bool) -> None:
    """Answer the root `--help` with the skill the library composes, leaving `-h` to Typer."""
    if value:
        typer.echo(lib.skill())
        raise typer.Exit()


@app.callback()
def cli(
    help: Annotated[
        bool,
        typer.Option(
            "--help", is_eager=True, callback=_print_skill, help="This tool's skill, for an agent driving it."
        ),
    ] = False,
) -> None:
    """Create and refine styled single- and multi-panel infographics with Amplifier Agent and image generation"""


@app.command()
def manifest() -> None:
    """Print the tool's manifest as JSON. Deterministic."""
    typer.echo(lib.load_manifest().model_dump_json(indent=2))


def _result(value: Any) -> None:
    typer.echo(json.dumps(value, indent=2, default=str))
    if isinstance(value, dict) and value.get("status") == "failed":
        raise typer.Exit(1)


@app.command()
def generate(
    topic: str,
    mode: str = "infographic",
    store: Path = DEFAULT_STORE,
    source: Path | None = None,
    panels: int | None = None,
    orientation: str = "auto",
    layout: str = "auto",
    style: str = "",
    representation: str = "auto",
    candidates: int = 1,
    selection: str = "manual",
    constraints: str = "",
    provider: str = "openai",
    model: str = "",
    reasoning_effort: str = "medium",
    image_model: str = DEFAULT_IMAGE_MODEL,
    timeout_seconds: int = 180,
    repair_rounds: int = 0,
    reference: list[Path] | None = None,
    style_reference: list[Path] | None = None,
    request_id: str | None = None,
) -> None:
    """Create a retained infographic. Model-backed."""
    brief = Brief.model_validate(
        {
            "topic": topic,
            "mode": mode,
            "representation": representation,
            "candidates": candidates,
            "selection": selection,
            "source": source.read_text(encoding="utf-8") if source else "",
            "panels": panels,
            "orientation": orientation,
            "layout": layout,
            "style": style,
            "constraints": constraints,
            "provider": provider,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "image_model": image_model,
            "timeout_seconds": timeout_seconds,
            "repair_rounds": repair_rounds,
        }
    )
    _result(
        lib.generate(
            brief,
            store,
            [path.read_bytes() for path in reference or []],
            request_id=request_id,
            style_references=[path.read_bytes() for path in style_reference or []],
        )
    )


@app.command()
def refine(
    run_id: str,
    feedback: str,
    store: Path = DEFAULT_STORE,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    image_model: str | None = None,
    panels: int | None = None,
    orientation: str | None = None,
    layout: str | None = None,
    style: str | None = None,
    constraints: str | None = None,
    mode: str | None = None,
    representation: str | None = None,
    candidates: int | None = None,
    selection: str | None = None,
    reference: list[Path] | None = None,
    style_reference: list[Path] | None = None,
    auto_panels: bool = False,
    request_id: str | None = None,
) -> None:
    """Revise a completed result, preserving its parent. Model-backed."""
    changes: dict[str, Any] = {
        key: value
        for key, value in {
            "provider": provider,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "image_model": image_model,
            "panels": panels,
            "orientation": orientation,
            "layout": layout,
            "style": style,
            "constraints": constraints,
            "mode": mode,
            "representation": representation,
            "candidates": candidates,
            "selection": selection,
        }.items()
        if value is not None
    }
    if auto_panels:
        if panels is not None:
            raise InfographicError("Choose --auto-panels or an explicit --panels count, not both.")
        changes["panels"] = None
    _result(
        lib.refine(
            run_id,
            feedback,
            store,
            changes,
            request_id=request_id,
            references=[path.read_bytes() for path in reference] if reference is not None else None,
            style_references=[path.read_bytes() for path in style_reference] if style_reference is not None else None,
        )
    )


@app.command()
def select(run_id: str, candidate: int, store: Path = DEFAULT_STORE, request_id: str | None = None) -> None:
    """Select a retained candidate and complete generation. Model-backed."""
    _result(lib.select(run_id, candidate, store, request_id))


@app.command(name="close-interrupted")
def close_interrupted(run_id: str, store: Path = DEFAULT_STORE) -> None:
    """Acknowledge an interrupted run; never replay or stop live work."""
    _result(lib.close_interrupted(run_id, store))


@app.command()
def inspect(run_id: str, store: Path = DEFAULT_STORE) -> None:
    """Inspect retained metadata and verify image integrity."""
    _result(lib.inspect(run_id, store))


@app.command(name="list")
def list_command(store: Path = DEFAULT_STORE, limit: int = 50) -> None:
    """List recent retained runs."""
    _result(lib.list_results(store, limit))


@app.command()
def styles() -> None:
    """List original suggested aesthetics."""
    _result(lib.styles())


@app.command()
def check() -> None:
    """Inspect local readiness without model calls."""
    _result(lib.check())


@app.command()
def stitch(images: list[Path], output: Annotated[Path, typer.Option("--output")], layout: str = "vertical") -> None:
    """Assemble panels as a new PNG, without overwriting files."""
    data = lib.stitch_bytes([path.read_bytes() for path in images], layout)
    with output.open("xb") as handle:
        handle.write(data)
    _result({"output": str(output), "bytes": len(data)})


@app.command()
def serve(store: Path = DEFAULT_STORE, port: int = 8765) -> None:
    """Serve the loopback-only dashboard. Creation calls models only when submitted."""
    server = lib.dashboard(store, port)
    typer.echo(f"Open {server.url}", err=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    try:
        app()
    except InfographicError as error:
        typer.echo(error, err=True)
        return 1
    except (ValidationError, OSError) as error:
        typer.echo(
            f"Invalid input or local I/O failure ({type(error).__name__}). Check arguments and file permissions.",
            err=True,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
