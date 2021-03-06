from sympy import SYMPY_DEBUG
from sympy.core import Basic, S, oo, Symbol, C, I, Dummy, Wild
from sympy.functions import log, exp
from sympy.series.order import Order
from sympy.simplify import powsimp
"""
Limits
======

Implemented according to the PhD thesis
http://www.cybertester.com/data/gruntz.pdf, which contains very thorough
descriptions of the algorithm including many examples.  We summarize here the
gist of it.


All functions are sorted according to how rapidly varying they are at infinity
using the following rules. Any two functions f and g can be compared using the
properties of L:

L=lim  log|f(x)| / log|g(x)|           (for x -> oo)

We define >, < ~ according to::

    1. f > g .... L=+-oo

        we say that:
        - f is greater than any power of g
        - f is more rapidly varying than g
        - f goes to infinity/zero faster than g


    2. f < g .... L=0

        we say that:
        - f is lower than any power of g

    3. f ~ g .... L!=0, +-oo

        we say that:
        - both f and g are bounded from above and below by suitable integral
          powers of the other


Examples
========
::
    2 < x < exp(x) < exp(x**2) < exp(exp(x))
    2 ~ 3 ~ -5
    x ~ x**2 ~ x**3 ~ 1/x ~ x**m ~ -x
    exp(x) ~ exp(-x) ~ exp(2x) ~ exp(x)**2 ~ exp(x+exp(-x))
    f ~ 1/f

So we can divide all the functions into comparability classes (x and x^2 belong
to one class, exp(x) and exp(-x) belong to some other class). In principle, we
could compare any two functions, but in our algorithm, we don't compare
anything below the class 2~3~-5 (for example log(x) is below this), so we set
2~3~-5 as the lowest comparability class.

Given the function f, we find the list of most rapidly varying (mrv set)
subexpressions of it. This list belongs to the same comparability class. Let's
say it is {exp(x), exp(2x)}. Using the rule f ~ 1/f we find an element "w"
(either from the list or a new one) from the same comparability class which
goes to zero at infinity. In our example we set w=exp(-x) (but we could also
set w=exp(-2x) or w=exp(-3x) ...). We rewrite the mrv set using w, in our case
{1/w, 1/w^2}, and substitute it into f. Then we expand f into a series in w::

    f = c0*w^e0 + c1*w^e1 + ... + O(w^en),       where e0<e1<...<en, c0!=0

but for x->oo, lim f = lim c0*w^e0, because all the other terms go to zero,
because w goes to zero faster than the ci and ei. So::

    for e0>0, lim f = 0
    for e0<0, lim f = +-oo   (the sign depends on the sign of c0)
    for e0=0, lim f = lim c0

We need to recursively compute limits at several places of the algorithm, but
as is shown in the PhD thesis, it always finishes.

Important functions from the implementation:

compare(a, b, x) compares "a" and "b" by computing the limit L.
mrv(e, x) returns the list of most rapidly varying (mrv) subexpressions of "e"
rewrite(e, Omega, x, wsym) rewrites "e" in terms of w
leadterm(f, x) returns the lowest power term in the series of f
mrv_leadterm(e, x) returns the lead term (c0, e0) for e
limitinf(e, x) computes lim e  (for x->oo)
limit(e, z, z0) computes any limit by converting it to the case x->oo

All the functions are really simple and straightforward except rewrite(), which
is the most difficult/complex part of the algorithm. When the algorithm fails,
the bugs are usually in the series expansion (i.e. in SymPy) or in rewrite.

This code is almost exact rewrite of the Maple code inside the Gruntz thesis.

Debugging
---------

Because the gruntz algorithm is highly recursive, it's difficult to figure out
what went wrong inside a debugger. Instead, turn on nice debug prints by
defining the environment variable SYMPY_DEBUG. For example:

[user@localhost]: SYMPY_DEBUG=True ./bin/isympy

In [1]: limit(sin(x)/x, x, 0)
limitinf(_x*sin(1/_x), _x) = 1
+-mrv_leadterm(_x*sin(1/_x), _x) = (1, 0)
| +-mrv(_x*sin(1/_x), _x) = set([_x])
| | +-mrv(_x, _x) = set([_x])
| | +-mrv(sin(1/_x), _x) = set([_x])
| |   +-mrv(1/_x, _x) = set([_x])
| |     +-mrv(_x, _x) = set([_x])
| +-mrv_leadterm(exp(_x)*sin(exp(-_x)), _x, set([exp(_x)])) = (1, 0)
|   +-rewrite(exp(_x)*sin(exp(-_x)), set([exp(_x)]), _x, _w) = (1/_w*sin(_w), -_x)
|     +-sign(_x, _x) = 1
|     +-mrv_leadterm(1, _x) = (1, 0)
+-sign(0, _x) = 0
+-limitinf(1, _x) = 1

And check manually which line is wrong. Then go to the source code and debug
this function to figure out the exact problem.

"""
O = Order

def debug(func):
    """Only for debugging purposes: prints a tree

    It will print a nice execution tree with arguments and results
    of all decorated functions.
    """
    if not SYMPY_DEBUG:
        #normal mode - do nothing
        return func

    #debug mode
    def decorated(*args, **kwargs):
        #r = func(*args, **kwargs)
        r = maketree(func, *args, **kwargs)
        #print "%s = %s(%s, %s)" % (r, func.__name__, args, kwargs)
        return r

    return decorated

def tree(subtrees):
    "Only debugging purposes: prints a tree"
    def indent(s, type=1):
        x = s.split("\n")
        r = "+-%s\n"%x[0]
        for a in x[1:]:
            if a == "":
                continue
            if type == 1:
                r += "| %s\n"%a
            else:
                r += "  %s\n"%a
        return r
    if len(subtrees) == 0:
        return ""
    f = []
    for a in subtrees[:-1]:
        f.append(indent(a))
    f.append(indent(subtrees[-1], 2))
    return ''.join(f)

tmp = []
iter = 0
def maketree(f, *args, **kw):
    "Only debugging purposes: prints a tree"
    global tmp
    global iter
    oldtmp = tmp
    tmp = []
    iter += 1

    r = f(*args, **kw)

    iter -= 1
    s = "%s%s = %s\n" % (f.func_name, args, r)
    if tmp != []:
        s += tree(tmp)
    tmp = oldtmp
    tmp.append(s)
    if iter == 0:
        print tmp[0]
        tmp = []
    return r

def compare(a, b, x):
    """Returns "<" if a<b, "=" for a == b, ">" for a>b"""
    c = limitinf(log(a)/log(b), x)
    if c == 0:
        return "<"
    elif c in [oo, -oo]:
        return ">"
    else:
        return "="

@debug
def mrv(e, x):
    "Returns a python set of  most rapidly varying (mrv) subexpressions of 'e'"
    e = powsimp(e, deep=True, combine='exp')
    assert isinstance(e, Basic)
    if not e.has(x):
        return set([])
    elif e == x:
        return set([x])
    elif e.is_Mul or e.is_Add:
        while 1:
            i, d = e.as_independent(x) # throw away x-independent terms
            if d.func != e.func and (d.is_Add or d.is_Mul):
                e = d
                continue
            break
        if d.func != e.func:
            return mrv(d, x)
        a, b = d.as_two_terms()
        return mrv_max(mrv(a, x), mrv(b, x), x)
    elif e.is_Pow:
        b, e = e.as_base_exp()
        if e.has(x):
            return mrv(exp(e * log(b)), x)
        else:
            return mrv(b, x)
    elif e.func is log:
        return mrv(e.args[0], x)
    elif e.func is exp:
        if limitinf(e.args[0], x).is_unbounded:
            return mrv_max(set([e]), mrv(e.args[0], x), x)
        else:
            return mrv(e.args[0], x)
    elif e.is_Function:
        return reduce(lambda a, b: mrv_max(a, b, x), [mrv(a, x) for a in e.args])
    elif e.is_Derivative:
        return mrv(e.args[0], x)
    raise NotImplementedError("Don't know how to calculate the mrv of '%s'" % e)

def mrv_max(f, g, x):
    """Computes the maximum of two sets of expressions f and g, which
    are in the same comparability class, i.e. max() compares (two elements of)
    f and g and returns the set, which is in the higher comparability class
    of the union of both, if they have the same order of variation.
    """
    assert isinstance(f, set)
    assert isinstance(g, set)
    if f == set([]):
        return g
    elif g == set([]):
        return f
    elif f.intersection(g) != set([]):
        return f.union(g)
    elif x in f:
        return g
    elif x in g:
        return f

    c = compare(list(f)[0], list(g)[0], x)
    if c == ">":
        return f
    elif c == "<":
        return g
    else:
        assert c == "="
        return f.union(g)

@debug
def sign(e, x):
    """Returns a sign of an expression e(x) for x->oo.

        e >  0 ...  1
        e == 0 ...  0
        e <  0 ... -1
    """
    ## from sympy import sign as _sign
    assert isinstance(e, Basic)
    if e.is_Rational or e.is_Real:
        if e == 0:
            return 0
        elif e.evalf() > 0:
            return 1
        else:
            return -1
    elif not e.has(x):
        if e.is_positive:
            return 1
        elif e.is_negative:
            return -1
        else:
            # if we can't resolve the sign just return
            # the value; another option would be an
            # unevaluated sign
            ## return _sign(e)
            return e
    elif e == x:
        return 1
    elif e.is_Mul:
        a, b = e.as_two_terms()
        sa = sign(a, x)
        if not sa:
            return 0
        return sa * sign(b, x)
    elif e.func is exp:
        return 1
    elif e.is_Pow:
        if sign(e.base, x) == 1:
            return 1
    elif e.func is log:
        return sign(e.args[0] -1, x)
    elif e.is_Add:
        return sign(limitinf(e, x), x)
    elif e.is_Function and hasattr(e, 'nargs'): # XXX is this how to detect cos(x) vs f(x)?
        return sign(e.func(*[limitinf(a, x) for a in e.args]), x)
    raise ValueError("Don't know how to determine the sign of %s" % e)

@debug
def limitinf(e, x):
    """Limit e(x) for x-> oo"""
    if not e.has(x):
        return e #e is a constant
    if not x.is_positive:
        # We make sure that x.is_positive is True so we
        # get all the correct mathematical bechavior from the expression.
        # We need a fresh variable.
        p = Dummy('p', positive=True)
        e = e.subs(x, p)
        x = p
    c0, e0 = mrv_leadterm(e, x)
    sig = sign(e0, x)
    if sig == 1:
        return S.Zero # e0>0: lim f = 0
    elif sig == -1: #e0<0: lim f = +-oo (the sign depends on the sign of c0)
        if c0.match(I*Wild("a", exclude=[I])):
            return c0*oo
        s = sign(c0, x)
        #the leading term shouldn't be 0:
        assert s != 0
        return s*oo
    elif sig == 0:
        return limitinf(c0, x) #e0=0: lim f = lim c0

def moveup(l, x):
    return [e.subs(x, exp(x)) for e in l]

def movedown(l, x):
    return [e.subs(x, log(x)) for e in l]

def subexp(e, sub):
    """Is "sub" a subexpression of "e"? """
    #we substitute some symbol for the "sub", and if the
    #expression changes, the substitution was successful, thus the answer
    #is yes.
    return e.subs(sub, C.Dummy('u')) != e

@debug
def calculate_series(e, x):
    """ Calculates at least one term of the series of "e" in "x".

    This is a place that fails most often, so it is in its own function.
    """

    f = e
    for n in [2, 4, 6, 8]:
        series = f.nseries(x, n=n).removeO()
        if series:
            break
    else:
        assert ValueError('(%s).series(%s, n=8) gave no terms.' % (f, x))
    return series

@debug
def mrv_leadterm(e, x, Omega=[]):
    """Returns (c0, e0) for e."""
    if not e.has(x):
        return (e, S.Zero)
    Omega = [t for t in Omega if subexp(e, t)]
    if Omega == []:
        Omega = mrv(e, x)
    if x in set(Omega):
        #move the whole omega up (exponentiate each term):
        Omega_up = set(moveup(Omega, x))
        e_up = moveup([e], x)[0]
        #calculate the lead term
        mrv_leadterm_up = mrv_leadterm(e_up, x, Omega_up)
        #move the result (c0, e0) down
        return tuple(movedown(mrv_leadterm_up, x))
    #
    # The positive dummy, w, is used here so log(w*2) etc. will expand;
    # a unique dummy is needed in this algorithm
    #
    # For limits of complex functions, the algorithm would have to be
    # improved, or just find limits of Re and Im components separately.
    #
    w = Dummy("w", real=True, positive=True)
    f, logw = rewrite(e, set(Omega), x, w)
    series = calculate_series(f, w)
    series = series.subs(log(w), logw)
    return series.leadterm(w)

@debug
def rewrite(e, Omega, x, wsym):
    """e(x) ... the function
    Omega ... the mrv set
    wsym ... the symbol which is going to be used for w

    Returns the rewritten e in terms of w and log(w). See test_rewrite1()
    for examples and correct results.
    """
    assert isinstance(Omega, set)
    assert len(Omega) != 0
    #all items in Omega must be exponentials
    for t in Omega:
        assert t.func is exp
    def cmpfunc(a, b):
        return -cmp(len(mrv(a, x)), len(mrv(b, x)))
    #sort Omega (mrv set) from the most complicated to the simplest ones
    #the complexity of "a" from Omega: the length of the mrv set of "a"
    Omega = list(Omega)
    Omega.sort(cmp=cmpfunc)
    g = Omega[-1] #g is going to be the "w" - the simplest one in the mrv set
    sig = (sign(g.args[0], x) == 1)
    if sig:
        wsym = 1/wsym #if g goes to oo, substitute 1/w
    #O2 is a list, which results by rewriting each item in Omega using "w"
    O2 = []
    for f in Omega:
        c = mrv_leadterm(f.args[0]/g.args[0], x)
        #the c is a constant, because both f and g are from Omega:
        assert c[1] == 0
        O2.append(exp((f.args[0] - c[0]*g.args[0]).expand())*wsym**c[0])

    #Remember that Omega contains subexpressions of "e". So now we find
    #them in "e" and substitute them for our rewriting, stored in O2

    # the following powsimp is necessary to automatically combine exponentials,
    # so that the .subs() below succeeds:
    f = powsimp(e, deep=True, combine='exp')
    for a, b in zip(Omega, O2):
        f = f.subs(a, b)

    #finally compute the logarithm of w (logw).
    logw = g.args[0]
    if sig:
        logw = -logw     #log(w)->log(1/w)=-log(w)

    return f, logw

def gruntz(e, z, z0, dir="+"):
    """
    Compute the limit of e(z) at the point z0 using the Gruntz algorithm.

    z0 can be any expression, including oo and -oo.

    For dir="+" (default) it calculates the limit from the right
    (z->z0+) and for dir="-" the limit from the left (z->z0-). For infinite z0
    (oo or -oo), the dir argument doesn't matter.

    This algorithm is fully described in the module docstring in the gruntz.py
    file. It relies heavily on the series expansion. Most frequently, gruntz()
    is only used if the faster limit() function (which uses heuristics) fails.
    """
    if not isinstance(z, Symbol):
        raise NotImplementedError("Second argument must be a Symbol")

    #convert all limits to the limit z->oo; sign of z is handled in limitinf
    if z0 == oo:
        return limitinf(e, z)
    elif z0 == -oo:
        return limitinf(e.subs(z, -z), z)
    else:
        if dir == "-":
            e0 = e.subs(z, z0 - 1/z)
        elif dir == "+":
            e0 = e.subs(z, z0 + 1/z)
        else:
            raise NotImplementedError("dir must be '+' or '-'")
        return limitinf(e0, z)
