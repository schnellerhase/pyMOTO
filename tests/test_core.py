import unittest
import pymoto as pym
import numpy as np


class TestSignal(unittest.TestCase):
    def test_initialize(self):
        a = pym.Signal('foo')
        self.assertEqual(a.tag, 'foo', msg="Initialize tag")
        self.assertIsNone(a.state, msg="Initialize state to None")
        self.assertIsNone(a.state, msg="Initialize sensitivity to None")

    def test_state(self):
        a = pym.Signal('foo')
        a.state = 1.0
        self.assertEqual(a.state, 1.0, msg="Set state to scalar")

        a.state = np.array([1.0, 2.0, 3.0])
        self.assertTrue(np.allclose(a.state, np.array([1.0, 2.0, 3.0])), msg="Set state to array")

        b = pym.Signal('foo', np.array([5.0, 6.0]))
        self.assertEqual(b.tag, 'foo', msg="Set tag from init with state")
        self.assertTrue(np.allclose(b.state, np.array([5.0, 6.0])), msg="Set state from init")

    def test_sensitivity(self):
        a = pym.Signal('foo')
        a.sensitivity = 2.0
        self.assertEqual(a.sensitivity, 2.0, msg="Set initial sensitivity to scalar")

        a.add_sensitivity(3.0)
        self.assertEqual(a.sensitivity, 5.0, msg="Add scalar sensitivity")

        a.sensitivity = 1.0
        self.assertEqual(a.sensitivity, 1.0, msg="Rewrite sensitivity by set_sens")

        a.reset(keep_alloc=True)
        self.assertEqual(a.sensitivity, 0.0, msg="Reset while keeping memory allocation")

        a.reset()
        self.assertEqual(a.sensitivity, None, msg="Reset sensitivity")

        a.add_sensitivity(np.array([1.1, 2.2, 3.3]))
        self.assertTrue(np.allclose(a.sensitivity, np.array([1.1, 2.2, 3.3])),
                        msg="Set initial sensitivity by add_sensitivity")

        a.add_sensitivity(None)
        self.assertTrue(np.allclose(a.sensitivity, np.array([1.1, 2.2, 3.3])),
                        msg="After adding None by add_sensitivity")

        b = pym.Signal('foo', np.array([5.0, 6.0]), np.array([7.0, 8.0]))
        self.assertEqual(b.tag, 'foo',
                         msg="Set tag from init with state and sensitivity")
        self.assertTrue(np.allclose(b.state, np.array([5.0, 6.0])),
                        msg="Set state from init and sensitivity")
        self.assertTrue(np.allclose(b.sensitivity, np.array([7.0, 8.0])),
                        msg="Set sensitivity from init and sensitivity")

        c = pym.Signal('bar', sensitivity=np.array([7.0, 8.0]))
        self.assertEqual(c.tag, 'bar', msg="Set tag from init with sensitivity")
        self.assertTrue(np.allclose(c.sensitivity, np.array([7.0, 8.0])),
                        msg="Set sensitivity from init with sensitivity")

    def test_make_signals(self):
        d = pym.make_signals('a', 'b', 'c')
        self.assertIsInstance(d['a'], pym.Signal)
        self.assertIsInstance(d['b'], pym.Signal)
        self.assertIsInstance(d['c'], pym.Signal)
        self.assertEqual(d['a'].tag, 'a')
        self.assertEqual(d['b'].tag, 'b')
        self.assertEqual(d['c'].tag, 'c')

    def test_add_sensitivity_errors(self):
        a = pym.Signal('foo')
        a.sensitivity = np.array([1.0, 2.0, 3.0])
        # Add wrong type
        self.assertRaises(TypeError, a.add_sensitivity, "cannot add a string")
        # a.add_sensitivity("cannot add a string")

        # Add wrong value
        self.assertRaises(ValueError, a.add_sensitivity, np.random.rand(3, 3))
        # a.add_sensitivity(np.random.rand(3, 3))

        # Adding complex array to real array does not give problems
        b = pym.Signal('real', np.random.rand(3))
        b.add_sensitivity(np.random.rand(3) + 1j*np.random.rand(3))

        c = pym.Signal('integer', 1)
        c.add_sensitivity(1.234)
        c.add_sensitivity(np.array(1.345))
        c.add_sensitivity(np.array([1.3344]))
        # c.add_sensitivity(np.array([[394]]))
        self.assertRaises(ValueError, c.add_sensitivity, np.array([[23454]]))  # Cannot add this shape to existing array

        d = pym.Signal('integer', 1.0)
        d.add_sensitivity(np.array([[23454]]))  # But it can be added to a float

        # Type which doesnt have +=
        class MyObj:
            def __init__(self, val):
                self.val = val
        e = pym.Signal('foo')
        e.add_sensitivity(MyObj(1.3))
        # e.add_sensitivity(MyObj(3.4))
        self.assertRaises(TypeError, e.add_sensitivity, MyObj(3.4))

    def test_reset_errors(self):
        a = pym.Signal('floatingpoint')
        a.add_sensitivity(1.3)
        a.reset(True)

        # With an object that doesnt have [] and *=
        class MyObj:
            def __init__(self, val):
                self.val = val
        b = pym.Signal('foo')
        b.add_sensitivity(MyObj(1.3)), self.assertWarns(RuntimeWarning, b.reset, True)
        # b.add_sensitivity(MyObj(1.3)), b.reset(True)  # Gives a warning, and just replaced by None


class TestSignalSlice(unittest.TestCase):
    def test_slice_1d(self):

        sx = pym.Signal('x')
        sx.state = np.random.rand(100)
        sx.state[1] = 0.314
        assert sx[0].state == sx.state[0]
        assert np.allclose(sx[0:5].state, sx.state[0:5])
        sx[0].state = 0.1
        assert sx[0].state == 0.1
        assert sx.state[0] == 0.1
        assert sx[1].state == 0.314

        sx[0].state += 0.1
        assert sx[0].state == 0.2
        assert sx.state[0] == 0.2

        sx[4:9].state = 0.1
        assert np.allclose(sx[4:9].state, 0.1)
        assert np.allclose(sx.state[4:9], 0.1)

        sx[4:9].state += 0.1
        assert np.allclose(sx[4:9].state, 0.2)
        assert np.allclose(sx.state[4:9], 0.2)

        assert sx[0].sensitivity is None
        assert sx[1:34, 53, 123:56, [2, 34, 5]].sensitivity is None

        sx[1].add_sensitivity(1.0)
        self.assertRaises(ValueError, sx[1].add_sensitivity, np.array([1, 2, 34]))
        assert sx.state.size == sx.sensitivity.size
        assert sx[1].state.size == sx[1].sensitivity.size
        assert sx[1].sensitivity == 1.0
        assert sx[0].sensitivity == 0.0

        sx[0].add_sensitivity(2.0)
        assert sx[0].sensitivity == 2.0
        assert sx.sensitivity[0] == 2.0
        assert sx[1].sensitivity == 1.0

        sx[0].reset()
        assert sx[0].sensitivity == 0.0
        assert sx[1].sensitivity == 1.0

        sx[4:8].add_sensitivity(3.0)
        assert sx[0].sensitivity == 0.0
        assert sx[1].sensitivity == 1.0
        assert np.allclose(sx[4:8].sensitivity, 3.0)
        assert np.allclose(sx.sensitivity[4:8], 3.0)
        assert np.allclose(sx[9].sensitivity, 0.0)

        sx[9:12].add_sensitivity(np.array([4, 5, 6]))
        self.assertRaises(ValueError, sx[9:12].add_sensitivity, np.array([4, 5, 6, 4]))
        assert np.allclose(sx[9:12].sensitivity, np.array([4, 5, 6]))
        sx[9:11].reset()
        assert np.allclose(sx[9:11].sensitivity, 0)
        assert sx[11].sensitivity == 6.0

    def test_slice_error(self):
        class MyObj:
            def __init__(self, val):
                self.val = val

        def call_state(s):
            return s.state

        def call_sens(s):
            return s.sensitivity

        # Object that cannot be sliced
        a = pym.Signal("myobj", state=MyObj(1.23), sensitivity=MyObj(1.34))
        # call_state(a[2]) # Empty state
        # call_sens(a[2])
        self.assertRaises(TypeError, call_state, a[2])
        self.assertRaises(TypeError, call_sens, a[2])

        # Too many dimensions
        b = pym.Signal("2dim", state=np.random.rand(10, 10), sensitivity=np.random.rand(10, 10))
        # call_state(b[2,3,4]) # Too many dimensions
        # call_sens(b[2,3,4])
        self.assertRaises(IndexError, call_state, b[2, 3, 4])
        self.assertRaises(IndexError, call_sens, b[2, 3, 4])
        # call_state(b[np.array([1,2,493]), 1]) # Out of range
        # call_sens(b[np.array([1,2,493]), 1])
        self.assertRaises(IndexError, call_state, b[np.array([1, 2, 493]), 1])
        self.assertRaises(IndexError, call_sens, b[np.array([1, 2, 493]), 1])

    def test_sensitivity_set_error(self):
        s = pym.Signal("empty")

        def set_sens(s, val):
            s.sensitivity = val

        # set_sens(s[2], 3.4) # Cannot set when state is None
        self.assertRaises(TypeError, set_sens, s[2], 3.4)

        class MyObj:
            def __init__(self, val):
                self.val = val
        a = pym.Signal("obj", MyObj(1.3))
        # set_sens(a[3], 3.4) # Cannot zero-initialize this object
        self.assertRaises(TypeError, set_sens, a[3], 3.4)

    def test_slice_2d(self):
        s = pym.Signal("2D_vals", np.random.rand(10, 10))

        s[0, 4].state = 0.4
        self.assertEqual(s[0, 4].state, 0.4)
        self.assertEqual(s.state[0, 4], 0.4)

        s[:, 3].state = 0.8
        self.assertTrue(np.alltrue(s[:, 3].state == 0.8))
        self.assertTrue(np.alltrue(s.state[:, 3] == 0.8))

        s[0, 2:8].sensitivity = 1.0
        self.assertEqual(s.sensitivity.shape, s.state.shape)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == 1.0))
        self.assertEqual(s.sensitivity[0, 0], 0.0)
        self.assertEqual(s.state[0, 4], 0.4)  # Must be still the same as previously
        self.assertTrue(np.alltrue(s.state[:, 3] == 0.8))

        s[0, 2:8].sensitivity = 0.0
        self.assertTrue(np.alltrue(s.sensitivity == 0.0))

        # Test add_sensitivity
        add_arr = np.random.rand(6)
        s[0, 2:8].add_sensitivity(add_arr)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == add_arr))
        s[0, 2:8].add_sensitivity(add_arr)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == 2*add_arr))

        # Test reset
        s[0, 2:8].reset(keep_alloc=False)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == 0))

        s[0, 2:8].add_sensitivity(add_arr)
        s[0, 2:8].reset(keep_alloc=True)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == 0))

        s[0, 2:8].add_sensitivity(add_arr)
        s[0, 2:8].add_sensitivity(None)
        self.assertTrue(np.alltrue(s.sensitivity[0, 2:8] == add_arr))


class TestSignalConcat(unittest.TestCase):
    def test_state(self):
        s1 = pym.Signal('sig1', 0.0)
        s2 = pym.Signal('sig2', np.array([1.0, 2.0, 3.0, 4.0]))
        s3 = pym.Signal('sig3', 5.0)
        s4 = pym.Signal('sig4', np.array([[6.0, 7.0]]))
        s5 = pym.Signal('sig5', np.array(8.0))

        # Get the state of the concatenated signal
        s = pym.SignalConcat(s1, s2, s3, s4, s5, tag='Concatenated')
        self.assertTrue(np.allclose(s.state, np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])))

        # Set the state of the concatenated signal
        s.state = np.array([8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0])
        self.assertEqual(s1.state, 8.0)
        self.assertEqual(type(s1.state), float)

        self.assertTrue(np.allclose(s2.state, np.array([7.0, 6.0, 5.0, 4.0])))
        self.assertEqual(s2.state.shape, (4,))
        self.assertEqual(type(s2.state), np.ndarray)

        self.assertEqual(s3.state, 3.0)
        self.assertEqual(type(s3.state), float)

        self.assertTrue(np.allclose(s4.state, np.array([[2.0, 1.0]])))
        self.assertEqual(type(s4.state), np.ndarray)
        self.assertEqual(s4.state.shape, (1, 2))

        self.assertEqual(s5.state, np.array(0.0))
        self.assertEqual(s5.state.shape, ())
        self.assertEqual(type(s5.state), np.ndarray)

        # Try incrementing
        s.state += np.ones_like(s.state)
        self.assertTrue(np.allclose(s.state, np.array([9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0])))

        # Try to slice the state and then set a new value (THIS DOESN'T WORK UNFORTUNATELY)
        # s.state[:4] = -1.0
        # self.assertTrue(np.allclose(s.state, np.array([-1.0, -1.0, -1.0, -1.0, 5.0, 4.0, 3.0, 2.0, 1.0])))

    def test_error_with_empty_state(self):
        s1 = pym.Signal('sig1', 0.0)
        s2 = pym.Signal('sig2', np.array([1.0, 2.0, 3.0, 4.0]))
        s3 = pym.Signal('sig3')
        s4 = pym.Signal('sig4', np.array([[6.0, 7.0]]))
        s5 = pym.Signal('sig5', np.array(8.0))

        # Get the state of the concatenated signal
        s = pym.SignalConcat(s1, s2, s3, s4, s5, tag='Concatenated')
        self.assertRaises(ValueError, lambda: s.state)

    def test_sensitivity(self):
        s1 = pym.Signal('sig1', 0.0)
        s2 = pym.Signal('sig2', np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.1, 2.1, 3.1, 4.1]))
        s3 = pym.Signal('sig3', 5.0, 5.1)
        s4 = pym.Signal('sig4', np.array([[6.0, 7.0]]))
        s5 = pym.Signal('sig5', np.array(8.0), np.array(8.1))

        # Get the sensitivity of the concatenated signal
        s = pym.SignalConcat(s1, s2, s3, s4, s5, tag='Concatenated')
        self.assertTrue(np.allclose(s.sensitivity, np.array([0.0, 1.1, 2.1, 3.1, 4.1, 5.1, 0.0, 0.0, 8.1])))

        # Set the sensitivity of the concatenated signal
        s.sensitivity = np.array([8.1, 7.1, 6.1, 5.1, 4.1, 3.1, 2.1, 1.1, 0.1])
        self.assertEqual(s1.sensitivity, 8.1)
        self.assertEqual(type(s1.sensitivity), float)

        self.assertTrue(np.allclose(s2.sensitivity, np.array([7.1, 6.1, 5.1, 4.1])))
        self.assertEqual(s2.sensitivity.shape, (4,))
        self.assertEqual(type(s2.sensitivity), np.ndarray)

        self.assertEqual(s3.sensitivity, 3.1)
        self.assertEqual(type(s3.sensitivity), float)

        self.assertTrue(np.allclose(s4.sensitivity, np.array([[2.1, 1.1]])))
        self.assertEqual(type(s4.sensitivity), np.ndarray)
        self.assertEqual(s4.sensitivity.shape, (1, 2))

        self.assertEqual(s5.sensitivity, np.array(0.1))
        self.assertEqual(s5.sensitivity.shape, ())
        self.assertEqual(type(s5.sensitivity), np.ndarray)

        # Try incrementing
        s.sensitivity += np.ones_like(s.state)
        self.assertTrue(np.allclose(s.sensitivity, np.array([9.1, 8.1, 7.1, 6.1, 5.1, 4.1, 3.1, 2.1, 1.1])))

        s.add_sensitivity(np.ones_like(s.state))
        self.assertTrue(np.allclose(s.sensitivity, np.array([10.1, 9.1, 8.1, 7.1, 6.1, 5.1, 4.1, 3.1, 2.1])))

        # Try to slice the sensitivity and then set a new value (THIS DOESN'T WORK UNFORTUNATELY)
        # s.sensitivity[:4] = -1.0
        # self.assertTrue(np.allclose(s.sensitivity, np.array([-1.0, -1.0, -1.0, -1.0, 5.1, 4.1, 3.1, 2.1, 1.1])))

        # Reset (without allocation)
        s.reset(keep_alloc=False)
        self.assertEqual(s.sensitivity, None)
        self.assertEqual(s1.sensitivity, None)
        self.assertEqual(s2.sensitivity, None)
        self.assertEqual(s3.sensitivity, None)
        self.assertEqual(s4.sensitivity, None)
        self.assertEqual(s5.sensitivity, None)

        # Add sensitivity to empty
        s.add_sensitivity(np.ones_like(s.state))
        self.assertTrue(np.allclose(s.sensitivity, np.ones_like(s.state)))

        # Reset (With allocation)
        s.sensitivity = np.array([8.1, 7.1, 6.1, 5.1, 4.1, 3.1, 2.1, 1.1, 0.1])
        s.reset(keep_alloc=True)
        self.assertTrue(np.allclose(s.sensitivity, np.zeros((9,))))
        self.assertEqual(s1.sensitivity, 0.0)
        self.assertTrue(np.allclose(s2.sensitivity, np.zeros(4,)))
        self.assertEqual(s3.sensitivity, 0.0)
        self.assertTrue(np.allclose(s4.sensitivity, np.zeros((1,2))))
        self.assertTrue(np.allclose(s5.sensitivity, np.zeros(())))




class TestModule(unittest.TestCase):
    def test_initialize1(self):
        a = pym.Signal('x_in')
        b = pym.Signal('x_out')
        self.assertRaises(TypeError, pym.Module, a, b, msg="Can't instantiate the abstract base class without implementation")
        # pym.Module(a, b)

        class MyMod(pym.Module):
            def _response(self, x):
                return x*2

        mod = MyMod(a, b)
        self.assertEqual(len(mod.sig_in), 1, msg="Should have 1 input")
        self.assertEqual(len(mod.sig_out), 1, msg="Should have 1 output")
        self.assertEqual(mod.sig_in[0], a, msg="Input should be a")
        self.assertEqual(mod.sig_out[0], b, msg="Output should be b")

    def test_initialize2(self):
        a = pym.Signal('x1')
        b = pym.Signal('x2')
        c = pym.Signal('x3')
        d = pym.Signal('y1')
        e = pym.Signal('y2')

        class MyMod(pym.Module):
            def _response(self, x, y, z):
                return x+y, y+x

        bl = MyMod([a, b, c], [d, e])

        self.assertEqual(len(bl.sig_in), 3)
        self.assertEqual(len(bl.sig_out), 2)
        self.assertEqual(bl.sig_in[0], a)
        self.assertEqual(bl.sig_in[1], b)
        self.assertEqual(bl.sig_in[2], c)
        self.assertEqual(bl.sig_out[0], d)
        self.assertEqual(bl.sig_out[1], e)

    def test_create(self):
        class FooMod(pym.Module):
            def _response(self, a_in):
                return a_in * 2

        print("test_create: ")
        pym.Module.print_children()
        a = pym.Signal('x_in')
        b = pym.Signal('x_out')
        bl = pym.Module.create('foomod', a, b)

        self.assertIsInstance(bl, pym.Module)
        self.assertIsInstance(bl, FooMod)

        self.assertEqual(len(bl.sig_in), 1)
        self.assertEqual(len(bl.sig_out), 1)
        self.assertEqual(bl.sig_in[0], a)
        self.assertEqual(bl.sig_out[0], b)

        a.state = 1.0
        bl.response()
        self.assertEqual(b.state, 2.0)

        b.sensitivity = 1.0
        self.assertWarns(Warning, bl.sensitivity)
        # bl.sensitivity() # Warns about non-existent sensitivity function
        self.assertIsNone(a.sensitivity, msg="Default sensitivity behavior is None")

    def test_create_fail(self):
        self.assertRaises(ValueError, pym.Module.create, 'foomod1234', msg="Try to create a non-existing module")

        class FooMod(pym.Module):
            def _response(self, a_in):
                return a_in * 2

        a = pym.Signal('a')
        self.assertRaises(TypeError, FooMod, a, 1.0, msg="Try to initialize with invalid Signal object as output")
        # FooMod(a, 1.0)

        self.assertRaises(TypeError, FooMod, [1.0, 2], a, msg="Try initializing with invalid input Signal object")
        # FooMod([1.0, 2], a)

        b = pym.Signal('b')
        self.assertRaises(TypeError, FooMod, [b, 2], a, msg="Try initializing with invalid input Signal object")
        # FooMod([b, 2], a)

    def test_create_duplicate(self):
        class MathGeneral(pym.Module):
            def _response(self, a_in):
                return a_in * 2

        class Mathgeneral(pym.Module):
            def _response(self, a_in):
                return a_in * 2

        print(pym.Module.__subclasses__())
        self.assertWarns(Warning, pym.Module.print_children), "A warning should be emitted in case of duplicates"

        # Remove the duplicate module again
        del MathGeneral
        del Mathgeneral

        import gc
        gc.collect()

        print(pym.Module.__subclasses__())

        print("test_create_duplicate: ")
        pym.Module.print_children()

    def test_response_and_sens(self):
        class TwoInTwoOut(pym.Module):
            def _prepare(self, argument):
                self.prepared = argument

            def _response(self, a, b):
                self.internalstate = True
                return a * b, a + b

            def _sensitivity(self, dc, dd):
                self.didsensitivity = True
                a, b = [s.state for s in self.sig_in]
                return b * dc + dd, a * dc + dd

            def _reset(self):
                self.internalstate = False
                self.didsensitivity = False

        sa = pym.Signal('a', 2.5)
        sb = pym.Signal('b', 3.5)
        sc = pym.Signal('c')
        sd = pym.Signal('d')
        m = TwoInTwoOut([sa, sb], [sc, sd], 'foo')
        self.assertEqual(m.prepared, 'foo', msg="Check if the preparation has been executed")

        m.response()
        self.assertTrue(m.internalstate, msg="Check if response has been called")

        m.sensitivity()
        self.assertTrue(not hasattr(m, 'didsensitivity'), msg="Sensitivity should not have been called, "
                                                              "since output sensitivities are None")

        sc.sensitivity = 1.0
        sd.sensitivity = 1.0
        m.sensitivity()
        self.assertTrue(m.didsensitivity, msg="Sensitivity should have been called")

        self.assertEqual(sa.sensitivity, 4.5, msg="Check sensitivity value")
        self.assertEqual(sb.sensitivity, 3.5, msg="Check other sensitivity value")

        m.reset()
        self.assertFalse(m.internalstate, msg="Check if reset has worked")
        self.assertFalse(m.didsensitivity, msg="Check if reset has worked")

    def test_zero_inputs(self):
        class FooMod1(pym.Module):
            def _response(self):
                return 3.14

        b = pym.Signal('x_out')
        bl = FooMod1([], b)
        bl.response()
        self.assertEqual(b.state, 3.14)

    def test_zero_outputs(self):
        class FooMod2(pym.Module):
            def _response(self, in1):
                self.got_in1 = in1

            def _sensitivity(self):
                self.did_sens = True
                return 2.15

        a = pym.Signal('x_in', 1.256)
        bl = FooMod2(a)
        bl.response()
        self.assertEqual(bl.got_in1, 1.256, msg="State variable passed to _reponse function")

        bl.sensitivity()
        self.assertTrue(bl.did_sens, msg="Check if _sensitivity did run")
        self.assertEqual(a.sensitivity, 2.15, msg="After running first sensitivity")
        bl.sensitivity()
        self.assertEqual(a.sensitivity, 2.15 + 2.15, msg="After running second sensitivity")
        bl.reset()
        self.assertIsNone(a.sensitivity, msg="After resetting module")
        bl.sensitivity()
        self.assertEqual(a.sensitivity, 2.15, msg="First sensitivity run after reset")

    def test_wrong_response(self):
        class WrongResponse(pym.Module):
            """ Foobar

            """
            def _response(self, a):
                return a * 2.0, a * 3.0  # Two returns

        sa = pym.Signal('a', 2.5)
        sb = pym.Signal('b')
        m = WrongResponse(sa, sb)  # One output signal
        self.assertRaises(TypeError, m.response, msg="Number of out-signals should match number of returns in response")
        # m.response()

    def test_sensitivity_and_reset_errors(self):
        class NoSensitivity(pym.Module):
            def _response(self, a, b):
                return a * b

            def _sensitivity(self, dc):
                self.did_sensitivity = True
                b = self.sig_in[1].state
                return b * dc  # Only returns one sensitivity

            def _reset(self):
                raise RuntimeError("An error has occurred")

        sa = pym.Signal('a', 2.5)
        sb = pym.Signal('b', 3.5)
        sc = pym.Signal('c')
        m = NoSensitivity([sa, sb], sc)  # Two inputs -> expects two sensitivities returned

        m.response()
        m.sensitivity()  # First test with None as sensitivity
        self.assertTrue(not hasattr(m, "did_sensitivity"))

        sc.sensitivity = 1.0
        self.assertRaises(TypeError, m.sensitivity)
        # m.sensitivity()
        self.assertTrue(m.did_sensitivity)

        # m.reset()
        self.assertRaises(RuntimeError, m.reset)

        class ErrModule(pym.Module):
            def _response(self, a, b):
                return a * b

            def _sensitivity(self, dc):
                raise ValueError("some error in calculation")
        m1 = ErrModule([sa, sb], sc)
        m1.response()
        sc.sensitivity = 1.0
        self.assertRaises(ValueError, m1.sensitivity)
        # m1.sensitivity()


class TestNetwork(unittest.TestCase):
    def test_correct_network(self):
        x1 = pym.Signal('x1', 2.0)
        x2 = pym.Signal('x2', 3.0)
        y1 = pym.Signal('y1')
        y2 = pym.Signal('y2')
        z = pym.Signal('z')
        m1 = pym.MathGeneral(x1, y1, expression="x1*2.0")
        m2 = pym.MathGeneral(x2, y2, expression="x2*x2 + 2.0")
        m3 = pym.MathGeneral([y1, y2], z, expression="y1*y2")

        netw1 = pym.Network(m1, m2, m3)

        netw2 = pym.Network([m1, m2, {"type": "MathGeneral", "sig_in": [y1, y2], "sig_out": z,
                                      "expression": "y1*y2"}])  # Initalize with list

        netw1.response()
        self.assertEqual(y1.state, 4.0)
        self.assertEqual(y2.state, 11.0)
        self.assertEqual(z.state, 44.0)

        netw2.response()
        self.assertEqual(y1.state, 4.0)
        self.assertEqual(y2.state, 11.0)
        self.assertEqual(z.state, 44.0)

        z.sensitivity = 1.0
        netw1.sensitivity()
        self.assertEqual(y1.sensitivity, 11.0)
        self.assertEqual(y2.sensitivity, 4.0)
        self.assertEqual(x1.sensitivity, 22.0)
        self.assertEqual(x2.sensitivity, 24.0)

        netw1.reset()
        self.assertIsNone(x1.sensitivity)
        self.assertIsNone(x2.sensitivity)
        self.assertIsNone(y1.sensitivity)
        self.assertIsNone(y2.sensitivity)
        self.assertIsNone(z.sensitivity)

    def test_network_with_initializer_error(self):
        class ErrorModule(pym.Module):
            def _response(self, a1, a2):
                raise RuntimeError("Response error")

            def _sensitivity(self, dy):
                raise KeyError("Sensitivity error")

            def _reset(self):
                raise ValueError("Reset error")

        x1 = pym.Signal('x1', 2.0)
        x2 = pym.Signal('x2', 3.0)
        y1 = pym.Signal('y1')
        y2 = pym.Signal('y2')
        z = pym.Signal('z')
        m1 = pym.MathGeneral(x1, y1, expression="x1*2.0")
        m2 = pym.MathGeneral(x2, y2, expression="x2*x2 + 2.0")
        m3 = ErrorModule([y1, y2], z)

        self.assertRaises(KeyError, pym.Network, [m1, m2, {"sig_in": [y1, y2], "sig_out": z, "expression": "y1*y2"}])

        netw = pym.Network(m1, m2, m3)
        self.assertRaises(RuntimeError, netw.response)
        # netw.response()

        z.sensitivity = 1.0
        self.assertRaises(KeyError, netw.sensitivity)
        # netw.sensitivity()
        self.assertRaises(ValueError, netw.reset)
        # netw.reset()

        class PrepErrorModule(pym.Module):
            def _prepare(self):
                raise RuntimeError("Prepare error")

            def _response(self, a1, a2):
                raise RuntimeError("Response error")

        # pym.Network({'type': 'PrepErrorModule','sig_in': [], 'sig_out': []})
        self.assertRaises(RuntimeError, pym.Network, {'type': 'PrepErrorModule', 'sig_in': [], 'sig_out': []})


if __name__ == '__main__':
    unittest.main()
