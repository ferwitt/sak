import unittest

from saklib.sakcmd import SakCmd, SakCmdWrapper, sak_arg_parser


class SakCmdTest(unittest.TestCase):
    def test_always_passes(self) -> None:
        # GIVEN.
        cmd = SakCmd("foo", helpmsg="Dummy command")

        # WHEN.
        ret = sak_arg_parser(cmd, ["-h"])

        # THEN.
        self.assertEqual(
            ret["argparse"]["help"],
            "usage: foo [-h]\n\nDummy command\n\noptional arguments:\n  -h, --help  show this help message and exit\n",
        )

        self.assertEqual(ret["ret"], None)

        self.assertEqual(repr(ret["cmd"]), repr(SakCmdWrapper(cmd)))


class SakCmdWrapperTest(unittest.TestCase):
    def test_wrap_cmd_no_subcmd(self) -> None:
        # GIVEN.
        cmd = SakCmd("foo", helpmsg="Dummy command")
        wrap = SakCmdWrapper(cmd)

        # WHEN.
        ret = wrap.subcmds

        # THEN.
        self.assertEqual(ret, [])

    def test_wrap_cmd_one_subcmd(self) -> None:
        # GIVEN.
        cmd = SakCmd("foo", helpmsg="Dummy command")

        subcmd = SakCmd(name="bar", helpmsg="Dummy command 2")
        cmd.subcmds.append(subcmd)

        wrap = SakCmdWrapper(cmd)

        # WHEN.
        ret = wrap.subcmds

        # THEN.
        self.assertEqual(str(ret), str([SakCmdWrapper(subcmd)]))

    def test_wrap_cmd_no_help_string(self) -> None:
        # GIVEN.
        cmd = SakCmd("foo")
        wrap = SakCmdWrapper(cmd)

        # WHEN.
        ret = wrap.helpmsg

        # THEN.
        self.assertEqual(ret, "")

    def test_wrap_cmd_help_string(self) -> None:
        # GIVEN.
        cmd = SakCmd("foo", helpmsg="Dummy command")
        wrap = SakCmdWrapper(cmd)

        # WHEN.
        ret = wrap.helpmsg

        # THEN.
        self.assertEqual(ret, "Dummy command")
