import unittest
from typing import List, Optional

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


class SakCmdWrapperFunctionDocTest(unittest.TestCase):
    def test_wrap_func_docstring(self) -> None:
        # GIVEN.
        def function_docstring(arg_int: int, arg_str: str, arg_list: List[str]) -> bool:
            """Brief description.

            Long description, this is a long description.

            :arg_int: This is an int param.
            :arg_str: This is an string param.
            :arg_list: This is an list param.
            :returns: This is an bool return.

            """
            return False

        # WHEN.
        wrap = SakCmdWrapper(function_docstring)

        # THEN.
        self.assertEqual(wrap.name, "function_docstring")
        self.assertEqual(wrap.helpmsg, "Brief description.")
        self.assertEqual(
            wrap.description,
            "Brief description.\n\nLong description, this is a long description.",
        )
        self.assertEqual(wrap.callback, function_docstring)
        self.assertEqual(wrap.subcmds, [])
        self.assertEqual(len(wrap.args), 3)

        self.assertEqual(wrap.args[0].name, "arg_int")
        self.assertEqual(wrap.args[0].helpmsg, "This is an int param.")
        self.assertEqual(wrap.args[0].short_name, None)
        self.assertEqual(wrap.args[0].vargs["required"], True)
        self.assertEqual(wrap.args[0].vargs["type"], int)
        self.assertEqual(wrap.args[0].completercb, None)

        self.assertEqual(wrap.args[1].name, "arg_str")
        self.assertEqual(wrap.args[1].helpmsg, "This is an string param.")
        self.assertEqual(wrap.args[1].short_name, None)
        self.assertEqual(wrap.args[1].vargs["required"], True)
        self.assertEqual(wrap.args[1].vargs["type"], str)
        self.assertEqual(wrap.args[1].completercb, None)

        self.assertEqual(wrap.args[2].name, "arg_list")
        self.assertEqual(wrap.args[2].helpmsg, "This is an list param.")
        self.assertEqual(wrap.args[2].short_name, None)
        self.assertEqual(wrap.args[2].vargs["required"], True)
        self.assertEqual(wrap.args[2].vargs["type"], str)
        self.assertEqual(wrap.args[2].vargs["action"], "append")
        self.assertEqual(wrap.args[2].completercb, None)

    def test_wrap_func_docstring_optional_param(self) -> None:
        # GIVEN.
        def function_docstring(
            arg_int: int, arg_str: Optional[str] = "Hello world"
        ) -> bool:
            """Brief description.

            Long description, this is a long description.

            :arg_int: This is an int param.
            :arg_str: This is an optional string param.
            :returns: This is an bool return.

            """
            return False

        # WHEN.
        wrap = SakCmdWrapper(function_docstring)

        # THEN.
        self.assertEqual(wrap.name, "function_docstring")
        self.assertEqual(wrap.helpmsg, "Brief description.")
        self.assertEqual(
            wrap.description,
            "Brief description.\n\nLong description, this is a long description.",
        )
        self.assertEqual(wrap.callback, function_docstring)
        self.assertEqual(wrap.subcmds, [])
        self.assertEqual(len(wrap.args), 2)

        self.assertEqual(wrap.args[0].name, "arg_int")
        self.assertEqual(wrap.args[0].helpmsg, "This is an int param.")
        self.assertEqual(wrap.args[0].short_name, None)
        self.assertEqual(wrap.args[0].vargs["required"], True)
        self.assertEqual(wrap.args[0].vargs["type"], int)
        self.assertEqual(wrap.args[0].completercb, None)

        self.assertEqual(wrap.args[1].name, "arg_str")
        self.assertEqual(wrap.args[1].helpmsg, "This is an optional string param.")
        self.assertEqual(wrap.args[1].short_name, None)
        self.assertEqual(wrap.args[1].vargs["required"], False)
        self.assertEqual(wrap.args[1].vargs["type"], Optional[str])
        self.assertEqual(wrap.args[1].vargs["default"], "Hello world")
        self.assertEqual(wrap.args[1].completercb, None)
