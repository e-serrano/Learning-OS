from app.obsidian.frontmatter import parse_frontmatter


def test_no_frontmatter_returns_empty_dict_and_full_body() -> None:
    content = "# Just a note\n\nNo frontmatter here."
    result = parse_frontmatter(content)
    assert result.frontmatter == {}
    assert result.body == content
    assert result.error is None


def test_parses_valid_frontmatter() -> None:
    content = (
        "---\n"
        "id: concept_sql_window_functions\n"
        "type: concept\n"
        "mastery: 3.2\n"
        "---\n"
        "# SQL Window Functions\n"
        "\n"
        "Body content.\n"
    )
    result = parse_frontmatter(content)
    assert result.error is None
    assert result.frontmatter == {
        "id": "concept_sql_window_functions",
        "type": "concept",
        "mastery": 3.2,
    }
    assert result.body == "# SQL Window Functions\n\nBody content.\n"


def test_unclosed_frontmatter_reports_error_without_raising() -> None:
    content = "---\nid: concept_1\nno closing marker"
    result = parse_frontmatter(content)
    assert result.error == "Frontmatter not closed"
    assert result.frontmatter == {}
    assert result.body == content


def test_malformed_yaml_reports_error_without_raising() -> None:
    content = "---\nid: [unclosed bracket\n---\nBody\n"
    result = parse_frontmatter(content)
    assert result.error is not None
    assert result.frontmatter == {}
    assert result.body == content


def test_non_mapping_frontmatter_reports_error() -> None:
    content = "---\n- just\n- a\n- list\n---\nBody\n"
    result = parse_frontmatter(content)
    assert result.error == "Frontmatter is not a YAML mapping"
    assert result.frontmatter == {}


def test_empty_frontmatter_block_returns_empty_dict() -> None:
    content = "---\n---\nBody\n"
    result = parse_frontmatter(content)
    assert result.error is None
    assert result.frontmatter == {}
    assert result.body == "Body\n"


def test_never_raises_on_arbitrary_garbage() -> None:
    for garbage in ["", "---", "-", "\n\n\n", "---\n\t\x00---\nbody"]:
        result = parse_frontmatter(garbage)
        assert result.body is not None  # must not raise


def test_body_preserves_line_endings_style() -> None:
    content = "---\r\nid: x\r\n---\r\nBody line 1\r\nBody line 2\r\n"
    result = parse_frontmatter(content)
    assert result.error is None
    assert result.body == "Body line 1\r\nBody line 2\r\n"


def test_yaml_mapping_values_keep_native_types() -> None:
    content = "---\nmastery: 3.2\nimportance: 5\nmanaged_by: learning_os\n---\nBody\n"
    result = parse_frontmatter(content)
    assert result.frontmatter["mastery"] == 3.2
    assert result.frontmatter["importance"] == 5
    assert isinstance(result.frontmatter["importance"], int)
