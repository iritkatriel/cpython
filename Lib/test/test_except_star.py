
import unittest

class TestInvalidExceptStar(unittest.TestCase):
    def test_mixed_except_and_except_star_is_syntax_error(self):
        errors = [
            "try: pass\nexcept ValueError: pass\nexcept* TypeError: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept TypeError: pass\n",
            "try: pass\nexcept ValueError as e: pass\nexcept* TypeError: pass\n",
            "try: pass\nexcept* ValueError as e: pass\nexcept TypeError: pass\n",
            "try: pass\nexcept ValueError: pass\nexcept* TypeError as e: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept TypeError as e: pass\n",
            "try: pass\nexcept ValueError: pass\nexcept*: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept: pass\n",
        ]

        for err in errors:
            with self.assertRaises(SyntaxError):
                compile(err, "<string>", "exec")


class TestExceptStarSplitSemantics(unittest.TestCase):

    def assertExceptionIsLike(self, exc, template):
        if not isinstance(exc, ExceptionGroup):
            self.assertEqual(exc.__class__, template.__class__)
            self.assertEqual(exc.args[0], template.args[0])
        else:
            self.assertEqual(exc.msg, template.msg)
            self.assertEqual(len(exc.excs), len(template.excs))
            for e, t in zip(exc.excs, template.excs):
                self.assertExceptionIsLike(e, t)

    # TODO: add unnamed versions of these tests once sys.exc_info() is working.

    def test_match_single_type___named(self):
        try:
            raise ExceptionGroup("eg", ValueError("one"), ValueError("two"))
        except *ValueError as e:
            eg = e
        else:
            self.fail('Exception not raised')

        self.assertExceptionIsLike(
            eg, ExceptionGroup("eg", ValueError("one"), ValueError("two")))

    def test_match_single_type_partial_match___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg",
                    ValueError("one"),
                    OSError("OS err"),
                    ValueError("two"))
            except *ValueError as e:
                match = e
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match, ExceptionGroup("eg", ValueError("one"), ValueError("two")))
        self.assertExceptionIsLike(
            rest, ExceptionGroup("eg", OSError("OS err")))

    def test_match_single_type_nested___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg",
                    ValueError("one"),
                    OSError("OS err1"),
                    ExceptionGroup(
                        "nested",
                        OSError("OS err2"),
                        ValueError("two"),
                        TypeError("bad type")))
            except *ValueError as e:
                match = e
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match,
            ExceptionGroup("eg",
                           ValueError("one"),
                           ExceptionGroup(
                               "nested",
                               ValueError("two"))))

        self.assertExceptionIsLike(
            rest,
            ExceptionGroup("eg",
                    OSError("OS err1"),
                    ExceptionGroup(
                        "nested",
                        OSError("OS err2"),
                        TypeError("bad type"))))

    def test_match_type_tuple_nested___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg",
                    ValueError("one"),
                    OSError("OS err1"),
                    ExceptionGroup(
                        "nested",
                        OSError("OS err2"),
                        ValueError("two"),
                        TypeError("bad type")))
            except *(ValueError, TypeError) as e:
                match = e
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match,
            ExceptionGroup("eg",
                           ValueError("one"),
                           ExceptionGroup(
                               "nested",
                               ValueError("two"),
                               TypeError("bad type"))))

        self.assertExceptionIsLike(
            rest,
            ExceptionGroup("eg",
                    OSError("OS err1"),
                    ExceptionGroup(
                        "nested", OSError("OS err2"))))

    def test_empty_groups_removed___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg",
                    ExceptionGroup(
                        "nested1",
                        ValueError("one")),
                    ExceptionGroup(
                        "nested2",
                        ValueError("two"),
                        TypeError("bad type1")),
                    ExceptionGroup(
                        "nested3",
                        TypeError("bad type2")))
            except *TypeError as e:
                match = e
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match,
            ExceptionGroup("eg",
                    ExceptionGroup(
                        "nested2",
                        TypeError("bad type1")),
                    ExceptionGroup(
                        "nested3",
                        TypeError("bad type2"))))

        self.assertExceptionIsLike(
            rest,
            ExceptionGroup("eg",
                    ExceptionGroup(
                        "nested1",
                        ValueError("one")),
                    ExceptionGroup(
                        "nested2",
                        ValueError("two"))))

    def test_singleton_groups_are_kept___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg",
                    ExceptionGroup(
                        "parent",
                        ExceptionGroup(
                            "nested1",
                            ValueError("one")),
                        ExceptionGroup(
                            "nested2",
                            TypeError("bad type1"))))
            except *TypeError as e:
                match = e
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match,
            ExceptionGroup(
                "eg",
                ExceptionGroup(
                    "parent",
                    ExceptionGroup("nested2", TypeError("bad type1")))))

        self.assertExceptionIsLike(
            rest,
            ExceptionGroup(
                "eg",
                ExceptionGroup(
                    "parent",
                    ExceptionGroup("nested1", ValueError("one")))))

    @unittest.skip("not implemented yet")
    def test_plain_exceptions_matched___named(self):
        type_error = None
        value_error = None
        try:
            raise ValueError("bad value")
        except *TypeError as e:
            type_error = e
        except *ValueError as e:
            value_error = e

        self.assertIsNone(type_error)
        self.assertExceptionIsLike(
            value_error, ExceptionGroup("", ValueError("bad value")))

    def test_first_match_wins___named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", BlockingIOError("bad io"), TypeError("bad type"))
            except* OSError as e:
                match = e
            except* BlockingIOError as e:
                self.fail('Should not happen')
            else:
                self.fail('Exception not raised')
        except ExceptionGroup as e:
            rest = e

        self.assertExceptionIsLike(
            match, ExceptionGroup("eg", BlockingIOError("bad io")))

        self.assertExceptionIsLike(
            rest, ExceptionGroup("eg", TypeError("bad type")))


class TestExceptStarReraiseSemantics(unittest.TestCase):
    pass


class TestExceptStarChainingSemantics(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
