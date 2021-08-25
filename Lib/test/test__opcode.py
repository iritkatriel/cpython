import dis
from test.support.import_helper import import_module
import unittest
import opcode

_opcode = import_module("_opcode")
from _opcode import stack_effect


class OpcodeTests(unittest.TestCase):

    def test_stack_effect(self):
        self.assertEqual(stack_effect(dis.opmap['POP_TOP']), -1)
        self.assertEqual(stack_effect(dis.opmap['DUP_TOP_TWO']), 2)
        self.assertEqual(stack_effect(dis.opmap['BUILD_SLICE'], 0), -1)
        self.assertEqual(stack_effect(dis.opmap['BUILD_SLICE'], 1), -1)
        self.assertEqual(stack_effect(dis.opmap['BUILD_SLICE'], 3), -2)
        self.assertRaises(ValueError, stack_effect, 30000)
        self.assertRaises(ValueError, stack_effect, dis.opmap['BUILD_SLICE'])
        self.assertRaises(ValueError, stack_effect, dis.opmap['POP_TOP'], 0)
        # All defined opcodes
        for name, code in dis.opmap.items():
            with self.subTest(opname=name):
                if code < dis.HAVE_ARGUMENT:
                    stack_effect(code)
                    self.assertRaises(ValueError, stack_effect, code, 0)
                else:
                    stack_effect(code, 0)
                    self.assertRaises(ValueError, stack_effect, code)
        # All not defined opcodes
        for code in set(range(256)) - set(dis.opmap.values()):
            with self.subTest(opcode=code):
                self.assertRaises(ValueError, stack_effect, code)
                self.assertRaises(ValueError, stack_effect, code, 0)

    def test_stack_effect_jump(self):
        JUMP_IF_TRUE_OR_POP = dis.opmap['JUMP_IF_TRUE_OR_POP']
        self.assertEqual(stack_effect(JUMP_IF_TRUE_OR_POP, 0), 0)
        self.assertEqual(stack_effect(JUMP_IF_TRUE_OR_POP, 0, jump=True), 0)
        self.assertEqual(stack_effect(JUMP_IF_TRUE_OR_POP, 0, jump=False), -1)
        FOR_ITER = dis.opmap['FOR_ITER']
        self.assertEqual(stack_effect(FOR_ITER, 0), 1)
        self.assertEqual(stack_effect(FOR_ITER, 0, jump=True), -1)
        self.assertEqual(stack_effect(FOR_ITER, 0, jump=False), 1)
        JUMP_FORWARD = dis.opmap['JUMP_FORWARD']
        self.assertEqual(stack_effect(JUMP_FORWARD, 0), 0)
        self.assertEqual(stack_effect(JUMP_FORWARD, 0, jump=True), 0)
        self.assertEqual(stack_effect(JUMP_FORWARD, 0, jump=False), 0)
        # All defined opcodes
        has_jump = dis.hasjabs + dis.hasjrel
        for name, code in dis.opmap.items():
            with self.subTest(opname=name):
                if code < dis.HAVE_ARGUMENT:
                    common = stack_effect(code)
                    jump = stack_effect(code, jump=True)
                    nojump = stack_effect(code, jump=False)
                else:
                    common = stack_effect(code, 0)
                    jump = stack_effect(code, 0, jump=True)
                    nojump = stack_effect(code, 0, jump=False)
                if code in has_jump:
                    self.assertEqual(common, max(jump, nojump))
                else:
                    self.assertEqual(jump, common)
                    self.assertEqual(nojump, common)


class IsCommonConstTests(unittest.TestCase):
    def test_ints(self):
        self.assertFalse(_opcode.is_common_const(-220))
        self.assertFalse(_opcode.is_common_const(-6))
        self.assertTrue(_opcode.is_common_const(-5))
        self.assertTrue(_opcode.is_common_const(-1))
        self.assertTrue(_opcode.is_common_const(0))
        self.assertTrue(_opcode.is_common_const(20))
        self.assertTrue(_opcode.is_common_const(228))
        self.assertFalse(_opcode.is_common_const(229))
        self.assertFalse(_opcode.is_common_const(1010))

    def test_floats(self):
        self.assertFalse(_opcode.is_common_const(-1.0))
        self.assertFalse(_opcode.is_common_const(-0.5))
        self.assertFalse(_opcode.is_common_const(-0.0))
        self.assertFalse(_opcode.is_common_const(0.0))
        self.assertTrue(_opcode.is_common_const(0.5))
        self.assertTrue(_opcode.is_common_const(1.0))
        self.assertTrue(_opcode.is_common_const(2.0))
        self.assertFalse(_opcode.is_common_const(2.2))
        self.assertFalse(_opcode.is_common_const(100.0))

    def test_strings(self):
        common_strings = [
            "", " ", "a", "b", "c", "x", "A", "B", "foo", "bar",
            "data", "id", "name", "return", "utf-8", "__main__",
            "/", ".", "\n",
        ]

        uncommon_strings = [
            "X", "1", "1.0", "main", "def"
        ]

        for s in common_strings:
            self.assertTrue(_opcode.is_common_const(s))

        for s in uncommon_strings:
            self.assertFalse(_opcode.is_common_const(s))

    def test_other_types(self):
        values = [
            (1, 2),
            lambda x: 1,
        ]
        for v in values:
            self.assertFalse(_opcode.is_common_const(v))


class SpecializationStatsTests(unittest.TestCase):
    def test_specialization_stats(self):
        stat_names = opcode._specialization_stats

        specialized_opcodes = [
            op[:-len("_ADAPTIVE")].lower() for
            op in opcode._specialized_instructions
            if op.endswith("_ADAPTIVE")]
        self.assertIn('load_attr', specialized_opcodes)
        self.assertIn('binary_subscr', specialized_opcodes)

        stats = _opcode.get_specialization_stats()
        if stats is not None:
            self.assertIsInstance(stats, dict)
            self.assertCountEqual(stats.keys(), specialized_opcodes)
            self.assertCountEqual(
                stats['load_attr'].keys(),
                stat_names + ['specialization_failure_kinds'])
            for sn in stat_names:
                self.assertIsInstance(stats['load_attr'][sn], int)
            self.assertIsInstance(
                stats['load_attr']['specialization_failure_kinds'],
                tuple)
            for v in stats['load_attr']['specialization_failure_kinds']:
                self.assertIsInstance(v, int)


if __name__ == "__main__":
    unittest.main()
