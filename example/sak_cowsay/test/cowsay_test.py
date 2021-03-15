from sak_cowsay.cowsay import cowsay


def test_cowsay_default() -> None:
    # GIVEN.
    ref = """\
 _____________
< Hello world >
 -------------
        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||
"""

    # WHEN.
    ret = cowsay()

    # THEN
    assert ret == ref


def test_cowsay_foo() -> None:
    # GIVEN.
    ref = """\
 _____________
< foo >
 -------------
        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||
"""

    # WHEN.
    ret = cowsay("foo")

    # THEN
    assert ret == ref
