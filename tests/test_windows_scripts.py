from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_bat_defaults_to_studio_launch() -> None:
    content = (REPO_ROOT / "run.bat").read_text(encoding="utf-8")
    assert 'if "%~1"=="" goto :launch_studio' in content
    assert "audio-engine studio" in content


def test_run_bat_keeps_cli_help_and_passthrough_paths() -> None:
    content = (REPO_ROOT / "run.bat").read_text(encoding="utf-8")
    assert "audio-engine %*" in content
    assert ":show_help" in content
    assert "audio-engine --help" in content


def test_setup_bat_completion_message_matches_run_bat_behavior() -> None:
    content = (REPO_ROOT / "setup.bat").read_text(encoding="utf-8")
    assert "double-click run.bat to launch the Studio GUI" in content
