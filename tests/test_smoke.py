import pytest


def test_all_modules_import() -> None:
    import cs2_analytics  # noqa: F401
    import cs2_analytics.analysis.death_zones  # noqa: F401
    import cs2_analytics.analysis.entry_kills  # noqa: F401
    import cs2_analytics.analysis.reaction_time  # noqa: F401
    import cs2_analytics.analysis.reaction_time_advanced  # noqa: F401
    import cs2_analytics.analysis.round_analyzer  # noqa: F401
    import cs2_analytics.cli  # noqa: F401
    import cs2_analytics.data.repository  # noqa: F401
    import cs2_analytics.parser.parse_demo  # noqa: F401
    import cs2_analytics.parser.tick_dataset  # noqa: F401
    import cs2_analytics.utils.maps  # noqa: F401
    import cs2_analytics.vision.build_dataset  # noqa: F401
    import cs2_analytics.vision.frame_extractor  # noqa: F401
    import cs2_analytics.visualization.heatmap  # noqa: F401


def test_cli_top_level_help_exits_zero() -> None:
    from cs2_analytics.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_every_subcommand_help_exits_zero() -> None:
    from cs2_analytics.cli import main

    for argv in (
        ["parse", "--help"],
        ["parse-batch", "--help"],
        ["ticks", "--help"],
        ["analyze", "rounds", "--help"],
        ["analyze", "death-zones", "--help"],
        ["analyze", "entry-kills", "--help"],
        ["analyze", "reaction-time", "--help"],
        ["visualize", "heatmap", "--help"],
        ["vision", "extract", "--help"],
        ["vision", "build-dataset", "--help"],
    ):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 0, f"failed for argv={argv}"
