from rift.__main__ import main


def test_version(capsys):
    rc = main(["version"])
    assert rc == 0
    assert capsys.readouterr().out.startswith("rift 0.")
