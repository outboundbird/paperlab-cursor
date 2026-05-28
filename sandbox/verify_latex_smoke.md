Some prose with inline $x = 1$.

$$
\int_0^1 f(x)\,dx
$$

A block with align:

$$
\begin{align}
  a &= b \\
  c &= d
\end{align}
$$

Bad braces: $x + {y$ inline.

Mismatched env:

$$
\begin{align}
  x = y
\end{matrix}
$$

Unicode math: $\theta + θ = 0$.

Stray newline outside tabular:

$$
x \\ y
$$

Forbidden delim: \(x+y\) and \[a=b\].

\left( without close: $ \left( x + y $
