from pathlib import Path

import pytest

from cs2_analytics.cli import main


def test_cli_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_no_args_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code != 0


def test_cli_lists_subcommands_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for cmd in ("parse", "ticks", "analyze", "visualize", "vision"):
        assert cmd in out


def test_parse_refuses_when_demo_dir_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    from cs2_analytics import cli as cli_mod

    (tmp_path / "parsed" / "fake").mkdir(parents=True)
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"not a real demo")

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {})

    rc = cli_mod.main(["parse", str(demo), "--output-dir", str(tmp_path / "parsed")])
    assert rc == 2
    assert "already exists" in capsys.readouterr().err


def test_parse_force_overwrites(
    tmp_path: Path, monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"not a real demo")

    sample = {"kills": pd.DataFrame({"x": [1]})}
    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: sample)

    rc = cli_mod.main(["parse", str(demo), "--output-dir", str(parsed), "--force"])
    assert rc == 0
    assert (parsed / "fake" / "kills.parquet").exists()


def test_ticks_refuses_when_ticks_parquet_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)
    (parsed / "fake" / "ticks.parquet").write_bytes(b"x")
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"x")

    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["ticks", str(demo), "--output-dir", str(parsed)])
    assert rc == 2
    assert "ticks.parquet" in capsys.readouterr().err


def test_ticks_runs_when_demo_dir_exists_but_no_ticks_yet(
    tmp_path: Path, monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)  # dir exists, but no ticks.parquet
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"x")

    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["ticks", str(demo), "--output-dir", str(parsed)])
    assert rc == 0
    assert (parsed / "fake" / "ticks.parquet").exists()


def test_parse_batch_skips_existing_and_parses_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    (demos_dir / "b.dem").write_bytes(b"x")

    parsed = tmp_path / "parsed"
    (parsed / "a").mkdir(parents=True)  # 'a' already parsed
    (parsed / "a" / "ticks.parquet").write_bytes(b"x")  # has ticks too

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {"kills": pd.DataFrame({"x": [1]})})
    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["parse-batch", str(demos_dir), "--output-dir", str(parsed)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "skip: a" in out
    assert "parse: b" in out
    assert "1 parsed, 1 skipped, 0 failed" in out
    assert (parsed / "b" / "kills.parquet").exists()
    assert (parsed / "b" / "ticks.parquet").exists()


def test_parse_batch_no_ticks_flag(tmp_path: Path, monkeypatch) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    parsed = tmp_path / "parsed"

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {"kills": pd.DataFrame({"x": [1]})})
    called = {"ticks": False}

    def fake_ticks(_p, sample_rate=16):
        called["ticks"] = True
        return pd.DataFrame({"t": [1]})

    monkeypatch.setattr(cli_mod, "generate_tick_dataset", fake_ticks)

    rc = cli_mod.main(
        ["parse-batch", str(demos_dir), "--output-dir", str(parsed), "--no-ticks"]
    )
    assert rc == 0
    assert called["ticks"] is False


def test_parse_batch_continues_after_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    (demos_dir / "b.dem").write_bytes(b"x")
    parsed = tmp_path / "parsed"

    def flaky_parse(p):
        if "a.dem" in p:
            raise RuntimeError("boom")
        return {"kills": pd.DataFrame({"x": [1]})}

    monkeypatch.setattr(cli_mod, "parse_demo", flaky_parse)
    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["parse-batch", str(demos_dir), "--output-dir", str(parsed)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "fail: a" in out
    assert "parse: b" in out
    assert "1 parsed, 0 skipped, 1 failed" in out


def test_analyze_demo_missing_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from cs2_analytics import cli as cli_mod

    rc = cli_mod.main(
        [
            "analyze",
            "--parsed-dir",
            str(tmp_path / "parsed"),
            "--demo",
            "nope",
            "rounds",
        ]
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "nope" in err
