import chicago95animations


def test_read_animations_skips_a_line_of_an_unknown_kind(tmp_path):
    table_file = tmp_path / "animations.conf"
    table_file.write_text("UNSET|speed|1\nFUTURE|whatever|else\nEVENT|open|Open|-|windows\n")

    table = chicago95animations.read_animations(table_file)

    assert (table.unset, [(event.key, event.category) for event in table.events]) == ({"speed": "1"}, [("open", None)])
