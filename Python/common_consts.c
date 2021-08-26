
#include "Python.h"
#include "pycore_code.h"
#include "pycore_interp.h"

/* Common constants which can be loaded from the interpreter's pre-initialized
   list via the LOAD_COMMON_CONST opcode
 */

static PyObject*
obj_to_key(PyObject *obj)
{
    PyObject *key = NULL;
    PyObject *obj_type = PyObject_Type(obj);
    if (!obj_type)
        return NULL;
    if (PyFloat_CheckExact(obj)) {
        double v = PyFloat_AsDouble(obj);
        if (!PyErr_Occurred()) {
            PyObject *sign = (copysign(1., v) == 1.) ? Py_True : Py_False;
            key = PyTuple_Pack(3, obj_type, obj, sign);
        }
    } else {
        key = PyTuple_Pack(2, obj_type, obj);
    }
    Py_DECREF(obj_type);
    if (! key) {
        return NULL;
    }
    return key;
}

static int
add_common_const(PyInterpreterState *interp, int index, PyObject *obj)
{
    PyObject *key = NULL, *value = NULL;
    int ret = 0;

    assert(obj);
    assert(index >= 0 && index < 256);

    /* Add to interpreter's list */
    Py_INCREF(obj);
    interp->common_consts[index] = obj;

    /* Add to the object-to-index mapping */
    key = obj_to_key(obj);
    if (!key) {
        ret = -1;
        goto done;
    }
    value = PyLong_FromLong(index);
    if (!value) {
        ret = -1;
        goto done;
    }
    ret = PyDict_SetItem(interp->common_const_to_index, key, value);

done:
    Py_XDECREF(key);
    Py_XDECREF(value);
    return ret;
}

static int
add_common_int(PyInterpreterState *interp, int index, int v)
{
    PyObject *obj = PyLong_FromLong(v);
    if (!obj)
        return -1;
    int ret = add_common_const(interp, index, obj);
    Py_DECREF(obj);
    return ret;
}

static int
add_common_float(PyInterpreterState *interp, int index, double v)
{
    PyObject *obj = PyFloat_FromDouble(v);
    if (!obj)
        return -1;
    int ret = add_common_const(interp, index, obj);
    Py_DECREF(obj);
    return ret;
}

static int
add_common_string(PyInterpreterState *interp, int index, const char *s)
{
    PyObject *obj = PyUnicode_InternFromString(s);
    if (!obj)
        return -1;
    int ret = add_common_const(interp, index, obj);
    Py_DECREF(obj);
    return ret;
}

int
_Py_InitCommonConsts(PyInterpreterState *interp)
{
    int index = 0;
    int num_ints, j;
    int ret = 0;

    interp->common_const_to_index = PyDict_New();
    if (!interp->common_const_to_index) {
        return -1;
    }

    ret += add_common_const(interp, index++, Py_None);
    ret += add_common_const(interp, index++, Py_True);
    ret += add_common_const(interp, index++, Py_False);
    ret += add_common_const(interp, index++, Py_Ellipsis);
    ret += add_common_const(interp, index++, PyExc_AssertionError);

    ret += add_common_string(interp, index++, "");
    ret += add_common_string(interp, index++, " ");
    ret += add_common_string(interp, index++, "a");
    ret += add_common_string(interp, index++, "b");
    ret += add_common_string(interp, index++, "c");
    ret += add_common_string(interp, index++, "x");
    ret += add_common_string(interp, index++, "A");
    ret += add_common_string(interp, index++, "B");
    ret += add_common_string(interp, index++, "foo");
    ret += add_common_string(interp, index++, "bar");
    ret += add_common_string(interp, index++, "data");
    ret += add_common_string(interp, index++, "id");
    ret += add_common_string(interp, index++, "name");
    ret += add_common_string(interp, index++, "return");
    ret += add_common_string(interp, index++, "utf-8");
    ret += add_common_string(interp, index++, "__main__");
    ret += add_common_string(interp, index++, "/");
    ret += add_common_string(interp, index++, ".");
    ret += add_common_string(interp, index++, "\n");

    ret += add_common_float(interp, index++, 0.0);
    ret += add_common_float(interp, index++, 0.5);
    ret += add_common_float(interp, index++, 1.0);
    ret += add_common_float(interp, index++, 2.0);

    // TODO: the tuples
    // (), ('dtype',), ('match',), (None,), ('index',), ('name',), ('axis',), ('primary_key',), (1, 2, 3),

    for(j=1; j < 6; j++) {
        ret += add_common_int(interp, index++, -j);
    }
    num_ints = 256 - index;
    assert(num_ints > 10); // ensure we don't fill it up with other consts
    for(j=0; j<num_ints; j++) {
        ret += add_common_int(interp, index++, j);
    }

    return ret < 0 ? -1: 0;
}

void
_Py_ClearCommonConsts(PyInterpreterState *interp)
{
    assert(interp->common_const_to_index);
    for (int i=0; i<256; i++) {
        Py_DECREF(interp->common_consts[i]);
        interp->common_consts[i] = NULL;
    }
    Py_CLEAR(interp->common_const_to_index);
}

/* Returns the index of obj in the common constants array.
   Returns -1 if obj is not a common constant, or if an
   error has occurred (use PyErr_Occurred() to disambiguate).
*/
Py_ssize_t
_Py_GetCommonConstIndex(PyObject* obj)
{
    Py_ssize_t index = -1;
    PyObject *value;
    PyInterpreterState *interp = PyInterpreterState_Get();
    PyObject *key = obj_to_key(obj);

    if (key) {
        value = PyDict_GetItemWithError(interp->common_const_to_index, key);
        Py_DECREF(key);
        if (value) {
            assert(PyLong_CheckExact(value));
            index = PyLong_AsLong(value);
        }
    }
    return index;
}

PyObject*
_Py_GetCommonConstValue(Py_ssize_t index)
{
    PyInterpreterState *interp = PyInterpreterState_Get();
    assert(index >= 0 && index < 256);
    PyObject *obj = interp->common_consts[index];
    assert(obj);
    Py_INCREF(obj);
    return obj;
}

