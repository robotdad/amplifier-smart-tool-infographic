"""Actual browser journeys with simulated external services, never live quality evidence."""

from pathlib import Path
import threading
from typing import Any

from playwright.sync_api import expect, sync_playwright
import pytest
from test_product import Reasoner, Renderer, png

from infographic import lib
from infographic.models import Brief
from infographic.storage import Store


@pytest.fixture
def browser_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    actual_generate, actual_select = lib.generate, lib.select
    calls: list[str] = []

    def generate(brief: Brief, *args: Any, **kwargs: Any) -> Any:
        calls.append("generate")
        kwargs.update(intelligence=Reasoner(brief.panels or 2), image_service=Renderer())
        return actual_generate(brief, *args, **kwargs)

    def select(*args: Any, **kwargs: Any) -> Any:
        calls.append("select")
        kwargs.update(intelligence=Reasoner(2), image_service=Renderer())
        return actual_select(*args, **kwargs)

    monkeypatch.setattr(lib, "generate", generate)
    monkeypatch.setattr(lib, "select", select)
    server = lib.dashboard(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server, calls
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


@pytest.mark.parametrize("width", [1280, 390])
def test_browser_freeform_upload_candidates_reload_refine_and_download(
    browser_server: Any, tmp_path: Path, width: int
) -> None:
    server, calls = browser_server
    content, style = tmp_path / "content.png", tmp_path / "style.png"
    content.write_bytes(png("red"))
    style.write_bytes(png("yellow"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.url)
        expect(page.locator("#connection")).to_have_text("Local · connected")
        page.locator("#create [name=mode]").select_option("freeform")
        expect(page.locator("#create [name=panels]")).to_be_hidden()
        page.locator("#create [name=topic]").fill("Watercolor observatory, no text")
        page.locator("#create [name=style]").fill("Watercolor, indigo and amber")
        page.locator("#create [name=candidates]").select_option("2")
        page.locator("#create [name=references]").set_input_files(content)
        page.locator("#create [name=style_references]").set_input_files(style)
        page.locator("#create button").click()
        expect(page.locator("#state")).to_have_text("awaiting-selection", timeout=15000)
        expect(page.locator("#candidates section")).to_have_count(2)
        records = lib.list_results(tmp_path)
        assert len(records) == 1
        run_id = records[0]["id"]
        assert [item["role"] for item in lib.inspect(run_id, tmp_path)["references"]] == ["content", "style"]
        page.reload()
        expect(page.locator("#state")).to_have_text("awaiting-selection")
        assert calls == ["generate"]
        page.get_by_role("button", name="Choose 2", exact=True).click()
        expect(page.locator("#state")).to_have_text("completed", timeout=15000)
        first = lib.inspect(run_id, tmp_path)
        assert first["selection"]["candidate"] == 2
        with page.expect_download() as downloaded:
            page.locator("#download").click()
        assert Path(downloaded.value.path()).read_bytes() == lib.artifact(run_id, first["composite"], tmp_path)
        page.locator("#refine [name=feedback]").fill("Make it dawn, preserving watercolor and no text")
        page.reload()
        expect(page.locator("#refine [name=feedback]")).to_have_value("Make it dawn, preserving watercolor and no text")
        page.locator("#refine summary").click()
        page.locator("#refine [name=candidates]").select_option("1")
        page.locator("#refine [name=orientation]").select_option("landscape")
        page.locator("#refine button").click()
        page.wait_for_function(
            "(old) => document.querySelector('#identity').textContent.includes('revision of '+old)", arg=run_id
        )
        expect(page.locator("#state")).to_have_text("completed", timeout=15000)
        child = lib.list_results(tmp_path)[0]
        assert child["parent_id"] == run_id
        assert child["brief"]["mode"] == "freeform"
        assert child["brief"]["orientation"] == "landscape"
        assert lib.inspect(run_id, tmp_path) == first
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth") is True
        assert not errors
        browser.close()


def test_browser_lost_ack_recovers_without_replay(browser_server: Any, tmp_path: Path) -> None:
    server, calls = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(server.url)
        expect(page.locator("#connection")).to_have_text("Local · connected")
        page.locator("#create [name=topic]").fill("Two-stage release")
        page.locator("#create [name=panels]").fill("2")

        def lose(route: Any) -> None:
            route.fetch()
            route.abort("failed")

        page.route("**/api/generate", lose)
        page.locator("#create button").click()
        expect(page.locator("#notice")).to_contain_text("Response uncertain", timeout=10000)
        assert len(lib.list_results(tmp_path)) == 1
        page.unroute("**/api/generate", lose)
        page.reload()
        expect(page.locator("#recovery")).to_be_visible()
        assert calls == ["generate"]
        page.locator("#observe").click()
        expect(page.locator("#state")).to_have_text("completed", timeout=10000)
        expect(page.locator("#recovery")).to_be_hidden()
        assert calls == ["generate"]
        browser.close()


def test_browser_duplicate_submit_during_async_preparation_has_one_identity(
    browser_server: Any, tmp_path: Path
) -> None:
    server, calls = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(server.url)
        expect(page.locator("#connection")).to_have_text("Local · connected")
        page.locator("#create [name=topic]").fill("A single deliberate request")
        page.evaluate("const f=document.querySelector('#create'); f.requestSubmit(); f.requestSubmit();")
        expect(page.locator("#state")).to_have_text("completed", timeout=15000)
        assert calls == ["generate"]
        assert len(lib.list_results(tmp_path)) == 1
        browser.close()


@pytest.mark.parametrize("loading", [False, True])
def test_browser_pending_revision_keeps_exact_target_and_does_not_steal_navigation(
    browser_server: Any, tmp_path: Path, loading: bool
) -> None:
    server, _ = browser_server
    first = lib.generate(Brief(topic="Alpha", panels=2), tmp_path)
    second = lib.generate(Brief(topic="Beta", panels=2), tmp_path)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(server.url)
        expect(page.locator("#connection")).to_have_text("Local · connected")
        page.locator("#library button").filter(has_text="Alpha").click()
        expect(page.locator("#identity")).to_contain_text(first["id"])
        page.locator("#refine [name=feedback]").fill("Change Alpha only")
        held = []
        navigation = []
        page.route("**/api/refine", lambda route: held.append(route))
        if loading:
            page.route(f"**/api/result/{second['id']}", lambda route: navigation.append(route))
        with page.expect_request("**/api/refine"):
            page.locator("#refine button").click()
        page.wait_for_function("document.querySelector('#refine button').disabled")
        assert len(held) == 1
        with page.expect_request(f"**/api/result/{second['id']}"):
            page.locator("#library button").filter(has_text="Beta").click()
        if loading:
            assert len(navigation) == 1
            expect(page.locator("#refine")).to_be_hidden()
        else:
            expect(page.locator("#identity")).to_contain_text(second["id"])
        held[0].continue_()
        page.wait_for_function("() => !sending")
        assert page.evaluate("selected") == second["id"]
        expect(page.locator("#notice")).to_contain_text("Your current selection has not changed", timeout=10000)
        if loading:
            navigation[0].continue_()
        expect(page.locator("#identity")).to_contain_text(second["id"])
        child = lib.list_results(tmp_path)[0]
        assert child["parent_id"] == first["id"]
        assert lib.inspect(first["id"], tmp_path) == first
        browser.close()


@pytest.mark.parametrize(("clear_content", "clear_style"), [(False, False), (True, False), (False, True), (True, True)])
def test_browser_reference_clear_flags_survive_target_navigation_reload_and_submission(
    browser_server: Any,
    tmp_path: Path,
    clear_content: bool,
    clear_style: bool,
) -> None:
    server, _ = browser_server
    first = lib.generate(
        Brief(topic="Alpha", panels=1), tmp_path, references=[png("red")], style_references=[png("yellow")]
    )
    second = lib.generate(Brief(topic="Beta", panels=1), tmp_path)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page()
            page.goto(server.url)
            expect(page.locator("#connection")).to_have_text("Local · connected")
            page.locator("#library button").filter(has_text="Alpha").click()
            expect(page.locator("#identity")).to_contain_text(first["id"])
            page.locator("#refine [name=feedback]").fill("Keep this exact reference choice")
            page.locator("#refine summary").click()
            page.locator("#refine [name=clear_references]").set_checked(clear_content)
            page.locator("#refine [name=clear_style_references]").set_checked(clear_style)
            page.locator("#library button").filter(has_text="Beta").click()
            expect(page.locator("#identity")).to_contain_text(second["id"])
            expect(page.locator("#refine [name=clear_references]")).not_to_be_checked()
            expect(page.locator("#refine [name=clear_style_references]")).not_to_be_checked()
            page.locator("#library button").filter(has_text="Alpha").click()
            expect(page.locator("#identity")).to_contain_text(first["id"])
            page.reload()
            expect(page.locator("#refine [name=feedback]")).to_have_value("Keep this exact reference choice")
            expect(page.locator("#refine [name=clear_references]")).to_be_checked(checked=clear_content)
            expect(page.locator("#refine [name=clear_style_references]")).to_be_checked(checked=clear_style)
            page.locator("#refine button").click()
            page.wait_for_function(
                "(id) => document.querySelector('#identity').textContent.includes('revision of '+id)",
                arg=first["id"],
            )
            expect(page.locator("#state")).to_have_text("completed", timeout=10000)
            child_id = next(item["id"] for item in lib.list_results(tmp_path) if item["parent_id"] == first["id"])
            child = lib.inspect(child_id, tmp_path)
            roles = [item["role"] for item in child["references"]]
            assert ("content" in roles) is not clear_content
            assert ("style" in roles) is not clear_style
            assert "revision" in roles
            assert lib.inspect(first["id"], tmp_path) == first
        finally:
            browser.close()


def test_freeform_labels_follow_mode_without_changing_the_brief(browser_server: Any) -> None:
    server, calls = browser_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page()
            page.goto(server.url)
            expect(page.locator("#connection")).to_have_text("Local · connected")
            page.locator("#create [name=topic]").fill("My unchanged artwork direction")
            page.locator("#create [name=mode]").select_option("freeform")
            expect(page.locator("#topic-label")).to_have_text("What should we create?")
            expect(page.locator("#create button")).to_have_text("Create image")
            expect(page.locator("#empty")).not_to_contain_text("individual panels")
            expect(page.locator("#planning-hint")).to_contain_text("one image per alternative")
            expect(page.locator("#create [name=topic]")).to_have_value("My unchanged artwork direction")
            page.locator("#create [name=mode]").select_option("infographic")
            expect(page.locator("#topic-label")).to_have_text("What should we explain?")
            expect(page.locator("#create button")).to_have_text("Create infographic")
            expect(page.locator("#empty")).to_contain_text("individual panels")
            assert not calls
        finally:
            browser.close()


@pytest.mark.parametrize("view_active", [False, True])
def test_retained_status_updates_without_replacing_selection_preview_or_draft(
    browser_server: Any,
    tmp_path: Path,
    view_active: bool,
) -> None:
    server, calls = browser_server
    active = lib.generate(Brief(topic="Active work", panels=1), tmp_path)
    other = lib.generate(Brief(topic="Other work", panels=1), tmp_path)
    storage = Store(tmp_path)
    storage.save({**active, "status": "planning"})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page()
            page.goto(server.url)
            expect(page.locator("#connection")).to_have_text("Local · connected")
            chosen = active if view_active else other
            page.locator("#library button").filter(has_text=chosen["brief"]["topic"]).click()
            expect(page.locator("#identity")).to_contain_text(chosen["id"])
            row = page.locator("#library button").filter(has_text="Active work")
            expect(row).to_contain_text("planning")
            if not view_active:
                page.locator("#refine [name=feedback]").fill("Keep this draft exactly")
                page.evaluate(
                    "window.previewNode=document.querySelector('#composite'); window.previewChanges=0;"
                    "new MutationObserver(m=>window.previewChanges+=m.length)"
                    ".observe(window.previewNode,{attributes:true});"
                )
            storage.save({**active, "status": "reviewing"})
            expect(row).to_contain_text("reviewing", timeout=10000)
            storage.save(active)
            expect(row).to_contain_text("completed", timeout=10000)
            expect(page.locator("#identity")).to_contain_text(chosen["id"])
            assert page.evaluate("selected") == chosen["id"]
            if view_active:
                expect(page.locator("#state")).to_have_text("completed", timeout=10000)
            else:
                expect(page.locator("#refine [name=feedback]")).to_have_value("Keep this draft exactly")
                assert page.evaluate("window.previewNode===document.querySelector('#composite')") is True
                assert page.evaluate("window.previewChanges") == 0
            assert calls == ["generate", "generate"]
        finally:
            browser.close()


def test_retained_rows_distinguish_original_and_revision_feedback(browser_server: Any, tmp_path: Path) -> None:
    server, _ = browser_server
    first = lib.generate(Brief(topic="Coastal observatory", mode="freeform"), tmp_path)
    child = lib.refine(first["id"], "Change blue hour to dawn", tmp_path)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page()
            page.goto(server.url)
            expect(page.locator("#connection")).to_have_text("Local · connected")
            original = page.locator("#library button").filter(has_text=f"Original {first['id'][:6]}")
            revision = page.locator("#library button").filter(has_text=f"Revision {child['id'][:6]}")
            expect(original).to_have_count(1)
            expect(revision).to_contain_text("Change blue hour to dawn")
            revision.click()
            expect(page.locator("#identity")).to_contain_text(child["id"])
            original.click()
            expect(page.locator("#identity")).to_contain_text(first["id"])
            page.reload()
            expect(revision).to_contain_text("Change blue hour to dawn")
        finally:
            browser.close()


@pytest.mark.parametrize("revision", [False, True])
def test_pending_submission_immediately_replaces_ready_or_completed_copy(
    browser_server: Any,
    tmp_path: Path,
    revision: bool,
) -> None:
    server, _ = browser_server
    first = lib.generate(Brief(topic="Original", panels=1), tmp_path) if revision else None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page()
            page.goto(server.url)
            expect(page.locator("#connection")).to_have_text("Local · connected")
            if first:
                page.locator("#library button").click()
                expect(page.locator("#identity")).to_contain_text(first["id"])
                expect(page.locator("#notice")).to_contain_text("Execution completed")
                page.locator("#refine [name=feedback]").fill("Dawn lighting")
            else:
                expect(page.locator("#notice")).to_contain_text("Ready")
                page.locator("#create [name=topic]").fill("A freeform image")
            path = "**/api/refine" if revision else "**/api/generate"
            held = []
            page.route(path, lambda route: held.append(route))
            with page.expect_request(path):
                page.locator("#refine button" if revision else "#create button").click()
            expect(page.locator("#notice")).to_contain_text("Submission pending")
            expect(page.locator("#notice")).not_to_contain_text("Ready")
            expect(page.locator("#notice")).not_to_contain_text("Execution completed")
            held[0].continue_()
            expect(page.locator("#state")).to_have_text("completed", timeout=15000)
            expect(page.locator("#notice")).to_contain_text("Execution completed", timeout=15000)
        finally:
            browser.close()
