# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for docs directory module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

import pytest

from gatekeeper import docs_directory, types_

from .. import factories


def create_directories_files(
    base_path: Path,
    directories: tuple[tuple[str, ...], ...],
    files: tuple[tuple[str, ...], ...],
) -> None:
    """Create directories and files.

    Args:
        base_path: The path to start with.
        directories: The directories to be created.
        files: The files to be created.
    """
    for directory in directories:
        (base_path / Path(*directory)).mkdir()
    for file in files:
        (base_path / Path(*file)).touch()


def create_nested_directories_file(
    base_path: Path, directories: tuple[str, ...], file: str | None
) -> Path:
    """Create directories and file.

    Args:
        base_path: The path to start with.
        directories: The directories to be created.
        file: The file to be created. If None, only creates directories.

    Returns:
        The deepest nested directory or file.
    """
    path = base_path
    for directory in directories:
        (path := path / directory).mkdir()
    if file is not None:
        (path := path / file).touch()
    return path


@pytest.mark.parametrize(
    "directories, files, expected_paths",
    [
        pytest.param((), (), (), id="empty"),
        pytest.param((("dir1",),), (), (("dir1",),), id="single directory"),
        pytest.param((("index",),), (), (("index",),), id="single directory called index"),
        pytest.param(
            (("dir1",), ("dir2",)), (), (("dir1",), ("dir2",)), id="multiple directories"
        ),
        pytest.param(
            (("dir1",), ("dir1", "subdir1")),
            (),
            (("dir1",), ("dir1", "subdir1")),
            id="nested directory",
        ),
        pytest.param((), (("file1.md",),), (("file1.md",),), id="single file"),
        pytest.param((), (("file1.MD",),), (("file1.MD",),), id="single file upper case suffix"),
        pytest.param((), (("file1.txt",),), (), id="single file not documentation"),
        pytest.param((), (("index.md",),), (), id="single file index"),
        pytest.param((), (("INDEX.md",),), (), id="single file index capitalised"),
        pytest.param(
            (), (("file1.md",), ("file2.md",)), (("file1.md",), ("file2.md",)), id="multiple files"
        ),
        pytest.param(
            (("dir1",),),
            (("file1.md",),),
            (("dir1",), ("file1.md",)),
            id="single directory and single file",
        ),
        pytest.param(
            (("dir1",),),
            (("dir1", "file1.md"),),
            (("dir1",), ("dir1", "file1.md")),
            id="file in directory",
        ),
        pytest.param(
            (("dir1",), ("dir2",)),
            (
                ("file1.md",),
                ("dir1", "dir1file1.md"),
                ("dir1", "dir1file2.md"),
                ("dir2", "dir2file1.md"),
                ("dir2", "dir2file2.md"),
            ),
            (
                ("dir1",),
                ("dir1", "dir1file1.md"),
                ("dir1", "dir1file2.md"),
                ("dir2",),
                ("dir2", "dir2file1.md"),
                ("dir2", "dir2file2.md"),
                ("file1.md",),
            ),
            id="multiple files in multiple directories",
        ),
    ],
)
def test__get_directories_files(
    directories: tuple[tuple[str, ...], ...],
    files: tuple[tuple[str, ...], ...],
    expected_paths: tuple[tuple[str, ...], ...],
    tmp_path: Path,
):
    """
    arrange: given docs directory with given directories and files created
    act: when _get_directories_files is called with the docs directory
    assert: then the expected paths are returned.
    """
    create_directories_files(base_path=tmp_path, directories=directories, files=files)

    returned_paths = docs_directory._get_directories_files(docs_path=tmp_path)

    assert [path.relative_to(tmp_path) for path in returned_paths] == [
        Path(*expected_path) for expected_path in expected_paths
    ]


@pytest.mark.parametrize(
    "directories, file, expected_level",
    [
        pytest.param((), "file1.md", 1, id="file in docs"),
        pytest.param(("dir1",), None, 1, id="directory in docs"),
        pytest.param(("dir1",), "file1.md", 2, id="directory file in docs"),
        pytest.param(("dir1", "dir2"), None, 2, id="multiple directories in docs"),
        pytest.param(("dir1", "dir2"), "file1.md", 3, id="multiple directories file in docs"),
        pytest.param(("dir1", "dir2", "dir3"), None, 3, id="many directories in docs"),
        pytest.param(("dir1", "dir2", "dir3"), "file1.md", 4, id="many directories file in docs"),
    ],
)
def test__calculate_level(
    directories: tuple[str, ...], file: str | None, expected_level: int, tmp_path: Path
):
    """
    arrange: given docs directory with given directories and file created
    act: when _calculate_level is called with the docs directory
    assert: then the expected level is returned.
    """
    path = create_nested_directories_file(base_path=tmp_path, directories=directories, file=file)

    returned_level = docs_directory._calculate_level(
        path_relative_to_docs=path.relative_to(tmp_path)
    )

    assert returned_level == expected_level


@pytest.mark.parametrize(
    "directories, file, expected_table_path",
    [
        pytest.param((), "file1.md", ("file1",), id="file in docs"),
        pytest.param((), "file_1.md", ("file-1",), id="file in docs including space"),
        pytest.param((), "file 1.md", ("file-1",), id="file in docs including underscore"),
        pytest.param((), "file1.MD", ("file1",), id="file in docs upper case suffix"),
        pytest.param((), "FILE1.md", ("file1",), id="file upper case in docs"),
        pytest.param(("dir1",), None, ("dir1",), id="directory in docs"),
        pytest.param(
            ("dir1",),
            "file1.md",
            (
                "dir1",
                "file1",
            ),
            id="directory file in docs",
        ),
        pytest.param(
            ("dir1", "dir2"),
            None,
            (
                "dir1",
                "dir2",
            ),
            id="multiple directories in docs",
        ),
        pytest.param(
            ("dir1", "dir2"),
            "file1.md",
            (
                "dir1",
                "dir2",
                "file1",
            ),
            id="multiple directories file in docs",
        ),
        pytest.param(
            ("dir1", "dir2", "dir3"),
            None,
            (
                "dir1",
                "dir2",
                "dir3",
            ),
            id="many directories in docs",
        ),
        pytest.param(
            ("dir1", "dir2", "dir3"),
            "file1.md",
            (
                "dir1",
                "dir2",
                "dir3",
                "file1",
            ),
            id="many directories file in docs",
        ),
    ],
)
def test_calculate_table_path(
    directories: tuple[str, ...], file: str | None, expected_table_path: str, tmp_path: Path
):
    """
    arrange: given docs directory with given directories and file created
    act: when calculate_table_path is called with the docs directory
    assert: then the expected table path is returned.
    """
    path = create_nested_directories_file(base_path=tmp_path, directories=directories, file=file)

    returned_level = docs_directory.calculate_table_path(
        path_relative_to_docs=path.relative_to(tmp_path)
    )

    assert returned_level == expected_table_path


@pytest.mark.parametrize(
    "directories, file, content, expected_navlink_title",
    [
        pytest.param(("dir1",), None, None, "Dir1", id="directory in docs"),
        pytest.param(("dir1", "dir2"), None, None, "Dir2", id="nested directory in docs"),
        pytest.param(("the-dir-1",), None, None, "The Dir 1", id="directory in docs with -"),
        pytest.param(("the_dir_1",), None, None, "The Dir 1", id="directory in docs with _"),
        pytest.param((), "file1.md", None, "File1", id="file in docs empty"),
        pytest.param(("dir1",), "file1.md", None, "File1", id="file in subdirectory empty"),
        pytest.param((), "the-file-1.md", None, "The File 1", id="file including - in docs empty"),
        pytest.param((), "the_file_1.md", None, "The File 1", id="file including _ in docs empty"),
        pytest.param((), "file1.md", "", "File1", id="file in docs empty string"),
        pytest.param((), "file1.md", "line 1", "line 1", id="file in docs single line no title"),
        pytest.param(
            (),
            "file1.md",
            "line 1\nline 2",
            "line 1",
            id="file in docs multiple line no title",
        ),
        pytest.param((), "file1.md", "# line 1", "line 1", id="file in docs title on first line"),
        pytest.param(
            (),
            "file1.md",
            "# line 1\nline 2",
            "line 1",
            id="file in docs title on first line with more lines",
        ),
        pytest.param(
            (),
            "file1.md",
            "line 1\n# line 2",
            "line 2",
            id="file in docs title on second line",
        ),
        pytest.param(
            (),
            "file1.md",
            "line 1\n# line 2\nline 3",
            "line 2",
            id="file in docs title on second line with more lines",
        ),
    ],
)
def test__calculate_navlink_title(
    directories: tuple[str, ...],
    file: str | None,
    content: str | None,
    expected_navlink_title: str,
    tmp_path: Path,
):
    """
    arrange: given docs directory with given directories and file created and contents of the file
        added
    act: when _calculate_navlink_title is called with the docs directory
    assert: then the expected navlink title is returned.
    """
    path = create_nested_directories_file(base_path=tmp_path, directories=directories, file=file)
    if file is not None and content is not None:
        path.write_text(content, encoding="utf-8")

    returned_navlink_title = docs_directory._calculate_navlink_title(path=path)

    assert returned_navlink_title == expected_navlink_title


def test__get_path_info(tmp_path: Path):
    """
    arrange: given docs directory with a directory
    act: when _get_path_info is called with the docs director
    assert: then the expected local path, level, table path and navlink title is returned.
    """
    rel_path = "dir1"
    (path := tmp_path / rel_path).mkdir()
    alphabetical_rank = 1

    returned_path_info = docs_directory._get_path_info(
        path=path, alphabetical_rank=alphabetical_rank, docs_path=tmp_path
    )

    assert returned_path_info == factories.PathInfoFactory(
        local_path=path,
        level=1,
        table_path=(rel_path,),
        navlink_title="Dir1",
        alphabetical_rank=alphabetical_rank,
    )


def _test_read_parameters():
    """Generate parameters for the test_read test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), [], id="empty"),
        pytest.param(
            ((dir_1 := "dir1",),),
            (),
            (
                factories.PathInfoFactory(
                    local_path=dir_1,
                    level=1,
                    table_path=(dir_1,),
                    navlink_title=dir_1.title(),
                    alphabetical_rank=0,
                ),
            ),
            id="single directory",
        ),
        pytest.param(
            ((dir_1 := "dir1",), (dir_2 := "dir2",)),
            (),
            (
                factories.PathInfoFactory(
                    local_path=dir_1,
                    level=1,
                    table_path=(dir_1,),
                    navlink_title=dir_1.title(),
                    alphabetical_rank=0,
                ),
                factories.PathInfoFactory(
                    local_path=dir_2,
                    level=1,
                    table_path=(dir_2,),
                    navlink_title=dir_2.title(),
                    alphabetical_rank=1,
                ),
            ),
            id="multiple directories",
        ),
        pytest.param(
            ((dir_2 := "dir2",), (dir_1 := "dir1",)),
            (),
            (
                factories.PathInfoFactory(
                    local_path=dir_1,
                    level=1,
                    table_path=(dir_1,),
                    navlink_title=dir_1.title(),
                    alphabetical_rank=0,
                ),
                factories.PathInfoFactory(
                    local_path=dir_2,
                    level=1,
                    table_path=(dir_2,),
                    navlink_title=dir_2.title(),
                    alphabetical_rank=1,
                ),
            ),
            id="multiple directories alternate order",
        ),
        pytest.param(
            (),
            ((file_1 := "file1.md",),),
            (
                factories.PathInfoFactory(
                    local_path=file_1,
                    level=1,
                    table_path=("file1",),
                    navlink_title="File1",
                    alphabetical_rank=0,
                ),
            ),
            id="single file",
        ),
        pytest.param(
            ((dir_1 := "dir1",),),
            ((dir_1, file_1 := "file1.md"),),
            (
                factories.PathInfoFactory(
                    local_path=dir_1,
                    level=1,
                    table_path=(dir_1,),
                    navlink_title=dir_1.title(),
                    alphabetical_rank=0,
                ),
                factories.PathInfoFactory(
                    local_path=f"{dir_1}/{file_1}",
                    level=2,
                    table_path=("dir1", "file1"),
                    navlink_title="File1",
                    alphabetical_rank=1,
                ),
            ),
            id="single file in directory",
        ),
        pytest.param(
            (),
            ((file_1 := "file1.md",), (file_2 := "file2.md",)),
            (
                factories.PathInfoFactory(
                    local_path=file_1,
                    level=1,
                    table_path=("file1",),
                    navlink_title="File1",
                    alphabetical_rank=0,
                ),
                factories.PathInfoFactory(
                    local_path=file_2,
                    level=1,
                    table_path=("file2",),
                    navlink_title="File2",
                    alphabetical_rank=1,
                ),
            ),
            id="multiple files",
        ),
        pytest.param(
            (),
            ((file_2 := "file2.md",), (file_1 := "file1.md",)),
            (
                factories.PathInfoFactory(
                    local_path=file_1,
                    level=1,
                    table_path=("file1",),
                    navlink_title="File1",
                    alphabetical_rank=0,
                ),
                factories.PathInfoFactory(
                    local_path=file_2,
                    level=1,
                    table_path=("file2",),
                    navlink_title="File2",
                    alphabetical_rank=1,
                ),
            ),
            id="multiple files alternate order",
        ),
    ]


@pytest.mark.parametrize("directories, files, expected_path_infos", _test_read_parameters())
def test_read(
    directories: tuple[tuple[str, ...], ...],
    files: tuple[tuple[str, ...], ...],
    expected_path_infos: tuple[types_.PathInfo, ...],
    tmp_path: Path,
):
    """
    arrange: given docs directory with given directories and files created
    act: when read is called with the docs directory
    assert: then the expected path infos are returned.
    """
    create_directories_files(base_path=tmp_path, directories=directories, files=files)

    returned_path_infos = docs_directory.read(docs_path=tmp_path)

    assert tuple(returned_path_infos) == tuple(
        types_.PathInfo(tmp_path / expected_path_info.local_path, *expected_path_info[1:])
        for expected_path_info in expected_path_infos
    )


def test_read_indico(tmp_path: Path):
    """
    arrange: given docs directory structured based on the indico docs
    act: when read is called with the docs directory
    assert: then the indico path infos are returned.
    """
    (tutorials := tmp_path / "tutorials").mkdir()
    (how_to_guides := tmp_path / "how-to-guides").mkdir()
    (contributing := how_to_guides / "contributing.md").touch()
    contributing.write_text("# Contributing\nThis is how to contribute", encoding="utf-8")
    (cross_model_db_relations := how_to_guides / "cross-model-db-relations.md").touch()
    cross_model_db_relations.write_text(
        "# Cross-model DB Relations\nThis is how to create cross-model DB relations",
        encoding="utf-8",
    )
    (refresh_external_resources := how_to_guides / "refresh-external-resources.md").touch()
    refresh_external_resources.write_text(
        "# Refreshing external resources\nThis is how to refresh external resources",
        encoding="utf-8",
    )
    (reference := tmp_path / "reference").mkdir()
    (plugins := reference / "plugins.md").touch()
    plugins.write_text("# Plugins\nPlugins reference", encoding="utf-8")
    (theme_customisation := reference / "theme-customisation.md").touch()
    theme_customisation.write_text(
        "# Theme Customisation\nTheme customisation reference", encoding="utf-8"
    )
    (explanation := tmp_path / "explanation").mkdir()
    (charm_architecture := explanation / "charm-architecture.md").touch()
    charm_architecture.write_text(
        "# Charm Architecture\nCharm architecture explanation", encoding="utf-8"
    )

    returned_path_infos = docs_directory.read(docs_path=tmp_path)

    assert tuple(returned_path_infos) == (
        factories.PathInfoFactory(
            local_path=explanation,
            level=1,
            table_path=("explanation",),
            navlink_title="Explanation",
            alphabetical_rank=0,
        ),
        factories.PathInfoFactory(
            local_path=charm_architecture,
            level=2,
            table_path=("explanation", "charm-architecture"),
            navlink_title="Charm Architecture",
            alphabetical_rank=1,
        ),
        factories.PathInfoFactory(
            local_path=how_to_guides,
            level=1,
            table_path=("how-to-guides",),
            navlink_title="How To Guides",
            alphabetical_rank=2,
        ),
        factories.PathInfoFactory(
            local_path=contributing,
            level=2,
            table_path=("how-to-guides", "contributing"),
            navlink_title="Contributing",
            alphabetical_rank=3,
        ),
        factories.PathInfoFactory(
            local_path=cross_model_db_relations,
            level=2,
            table_path=("how-to-guides", "cross-model-db-relations"),
            navlink_title="Cross-model DB Relations",
            alphabetical_rank=4,
        ),
        factories.PathInfoFactory(
            local_path=refresh_external_resources,
            level=2,
            table_path=("how-to-guides", "refresh-external-resources"),
            navlink_title="Refreshing external resources",
            alphabetical_rank=5,
        ),
        factories.PathInfoFactory(
            local_path=reference,
            level=1,
            table_path=("reference",),
            navlink_title="Reference",
            alphabetical_rank=6,
        ),
        factories.PathInfoFactory(
            local_path=plugins,
            level=2,
            table_path=("reference", "plugins"),
            navlink_title="Plugins",
            alphabetical_rank=7,
        ),
        factories.PathInfoFactory(
            local_path=theme_customisation,
            level=2,
            table_path=("reference", "theme-customisation"),
            navlink_title="Theme Customisation",
            alphabetical_rank=8,
        ),
        factories.PathInfoFactory(
            local_path=tutorials,
            level=1,
            table_path=("tutorials",),
            navlink_title="Tutorials",
            alphabetical_rank=9,
        ),
    )
