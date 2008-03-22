from sympy import Symbol, Matrix, Integral, log, Rational, Derivative, exp, \
        sqrt, pi, Function, sin, cos, pprint_use_unicode, oo, Eq
from sympy.printing.pretty import pretty as xpretty
from sympy.utilities.pytest import XFAIL

x = Symbol('x')
y = Symbol('y')
th  = Symbol('theta')
ph  = Symbol('phi')

def pretty(expr):
    # ascii-pretty by default
    return xpretty(expr, False)

def test_pretty_basic():
    # Simple numbers/symbols
    assert pretty( -Rational(1)/2 ) == '-1/2'
    assert pretty( -Rational(13)/22 ) == '  13\n- --\n  22'
    assert pretty( oo ) == 'oo'

    # Powers
    assert pretty( (x**2) ) == ' 2\nx '
    assert pretty( 1/x ) == '1\n-\nx'
    assert pretty( y*x**-2 ) == 'y \n--\n 2\nx '
    assert pretty( x**Rational(-5,2) ) == ' 1  \n----\n 5/2\nx   '

    # Sums of terms
    assert pretty( (x**2 + x + 1))  in [
                '         2\n1 + x + x ',
                '     2    \nx + x  + 1',
                ' 2        \nx  + x + 1']
    assert pretty( 1-x ) in ['1 - x', '-x + 1']
    assert pretty( 1-2*x ) in ['1 - 2*x', '-2*x + 1']
    assert pretty( 1-Rational(3,2)*y/x ) in [
            '    3*y\n1 - ---\n    2*x',
            '  3*y    \n- --- + 1\n  2*x    ']

    # Multiplication
    assert pretty( x/y ) == 'x\n-\ny'
    assert pretty( -x/y ) == '-x\n--\ny '
    assert pretty( (x+2)/y ) in ['2 + x\n-----\n  y  ', 'x + 2\n-----\n  y  ']
    assert pretty( (1+x)*y ) in ['(1 + x)*y', 'y*(1 + x)', 'y*(x + 1)']

    # Check for proper placement of negative sign
    assert pretty( -5*x/(x+10) ) == ' -5*x \n------\n10 + x'
    assert pretty( 1 - Rational(3,2)*(x+1) ) == '       3*x\n-1/2 - ---\n        2 '

def test_pretty_relational():
    assert pretty(Eq(x, '==', y)) == 'x = y'
    assert pretty(Eq(x, '<=', y)) == 'x <= y'
    assert pretty(Eq(x, '>',  y)) == 'y < x'
    assert pretty(Eq(x/(y+1), '!=', y**2)) in [
            '  x       2\n----- != y \n1 + y      ',
            '  x       2\n----- != y \ny + 1      ']


def test_pretty_unicode():
    assert xpretty( oo, True ) == u'\u221e'
    assert xpretty( pi, True ) == u'\u03c0'
    assert xpretty( pi+2*x, True ) in [u'\u03c0 + 2*x', u'2*x + \u03c0']
    assert xpretty( pi**2+exp(x), True ) == u' 2    x\n\u03c0  + \u212f '
    assert xpretty( Eq(x, '!=', y), True ) == u'x \u2260 y'

def test_pretty_unicode_defaults():
    use_unicode = pprint_use_unicode(True)
    assert xpretty(Symbol('alpha')) == u'\u03b1'
    pprint_use_unicode(False)
    assert xpretty(Symbol('alpha')) == 'alpha'

    pprint_use_unicode(use_unicode)


def test_pretty_functions():
    # Simple
    assert pretty( (2*x + exp(x)) ) in [' x      \ne  + 2*x', '       x\n2*x + e ']
    assert pretty( sqrt(2) ) == '  ___\n\\/ 2 '
    assert pretty( sqrt(2+pi) ) == '  ________\n\\/ 2 + pi '
    assert pretty(abs(x)) == '|x|'
    assert pretty(abs(x/(x**2+1))) in [
            '|  x   |\n|------|\n|     2|\n|1 + x |',
            '|  x   |\n|------|\n| 2    |\n|x  + 1|']

    # Univariate/Multivariate functions
    f = Function('f')
    assert pretty(f(x)) == 'f(x)'
    assert pretty(f(x, y)) == 'f(x, y)'
    assert pretty(f(x/(y+1), y)) in [
            '    x      \nf(-----, y)\n  1 + y    ',
            '    x      \nf(-----, y)\n  y + 1    ']

    # Nesting of square roots
    assert pretty( sqrt((sqrt(x+1))+1) ) in [
            '   _______________\n  /       _______ \n\\/  1 + \\/ 1 + x  ',
            '   _______________\n  /   _______     \n\\/  \\/ x + 1  + 1 ']
    # Function powers
    assert pretty( sin(x)**2 ) == '   2   \nsin (x)'

    # Conjugates
    a,b = map(Symbol, 'ab')
    #assert pretty( conjugate(a+b*I) ) == '_     _\na - I*b'
    #assert pretty( conjugate(exp(a+b*I)) ) == ' _     _\n a - I*b\ne       '

def test_pretty_derivatives():
    # Simple
    f_1 = Derivative(log(x), x, evaluate=False)
    assert pretty(f_1) == 'd         \n--(log(x))\ndx        '

    f_2 = Derivative(log(x), x, evaluate=False) + x
    assert pretty(f_2) in [
            '    d         \nx + --(log(x))\n    dx        ',
            'd             \n--(log(x)) + x\ndx            ']

    # Multiple symbols
    f_3 = Derivative(log(x) + x**2, x, y, evaluate=False)
    assert pretty(f_3) in [
            '   2              \n  d  / 2         \\\n-----\\x  + log(x)/\ndy dx             ',
            '   2              \n  d  /          2\\\n-----\\log(x) + x /\ndy dx             ']

    f_4 = Derivative(2*x*y, y, x, evaluate=False) + x**2
    assert pretty(f_4) in [
            '        2        \n 2     d         \nx  + -----(2*x*y)\n     dx dy       ',
            '   2             \n  d             2\n-----(2*x*y) + x \ndx dy            ']

def test_pretty_integrals():
    # Simple
    f_1 = Integral(log(x), x)
    assert pretty(f_1) == '  /         \n |          \n | log(x) dx\n |          \n/           '

    f_2 = Integral(x**2, x)
    assert pretty(f_2) == '  /     \n |      \n |  2   \n | x  dx\n |      \n/       '
    # Double nesting of pow
    f_3 = Integral(x**(2**x), x)
    assert pretty(f_3) == '  /        \n |         \n |  / x\\   \n |  \\2 /   \n | x     dx\n |         \n/          '

    # Definite integrals
    f_4 = Integral(x**2, (x,1,2))
    assert pretty(f_4) == '  2      \n  /      \n |       \n |   2   \n |  x  dx\n |       \n/        \n1        '

    f_5 = Integral(x**2, (x,Rational(1,2),10))
    assert pretty(f_5) == ' 10      \n  /      \n |       \n |   2   \n |  x  dx\n |       \n/        \n1/2      '

    # Nested integrals
    f_6 = Integral(x**2*y**2, x,y)
    assert pretty(f_6) == '  /  /           \n |  |            \n |  |  2  2      \n |  | x *y  dx dy\n |  |            \n/  /             '


def test_pretty_matrix():
    p = pretty( Matrix([[x**2+1, 1], [y, x+y]]) )
    s1 = \
"""\
[     2       ]
[1 + x       1]
[             ]
[     y  x + y]\
"""
    s2 = \
"""\
[ 2           ]
[x  + 1      1]
[             ]
[     y  y + x]\
"""
    assert p in [s1, s2]

def test_pretty_seq():
    assert pretty([]) == '[]'
    assert pretty(()) == '()'
    assert pretty({}) == '{}'

    e = [x**2, 1/x, x, y, sin(th)**2/cos(ph)**2]
    p = pretty(e)
    s = \
"""\
                 2        
  2  1        sin (theta) 
[x , -, x, y, -----------]
     x            2       
               cos (phi)  \
"""
    assert p == s

    e = tuple(e)
    p = pretty(e)
    s = \
"""\
                 2        
  2  1        sin (theta) 
(x , -, x, y, -----------)
     x            2       
               cos (phi)  \
"""
    assert p == s

    e = {x: sin(x)}
    p = pretty(e)
    s = \
"""\
{x: sin(x)}\
"""
    assert p == s

    e = {1/x: 1/y, x: sin(x)**2}
    p = pretty(e)
    s = \
"""\
 1  1        2    
{-: -, x: sin (x)}
 x  y             \
"""
    assert p == s



@XFAIL
def test_pretty_limits():
    assert pretty( limit(x, x, oo, evaluate=False) ) == ' lim x\nx->oo '
    assert pretty( limit(x**2, x, 0, evaluate=False) ) == '     2\nlim x \nx->0  '  