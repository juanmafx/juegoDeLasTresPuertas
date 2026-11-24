# Decision guide: using the model on real choices

**Status: interpretation.** This guide applies the model in [THEORY.md](THEORY.md) to everyday
decisions by analogy. The analogies are the author's reading of the model, not results proven by
it. Real situations rarely match a host policy exactly, and nothing here has been tested on
real-world decisions. Where a statement is a proven property of the model, it links to the
section of THEORY.md that proves it; everything else is a heuristic.

## The core question

Before updating on any piece of revealed information, ask:

> How did this information reach me, and would I have seen something different if my current
> choice were wrong?

In the model, everything the information can tell you about your current choice is in the
likelihood ratio (THEORY.md, section 3): how much more or less likely the observation was if your
choice is right than if it is wrong. The questions below are ways of estimating that ratio when
nobody hands you a formula.

## Six questions

### 1. Did the source know the answer?

- **Yes, and it only removed options it knew were wrong** (informed host): the surviving options
  you did not choose gain the probability that was removed. Averaged over what the source could
  have removed, your own choice gains nothing; when the options started equally likely, it gains
  nothing whatever was removed. *Proven in the model: THEORY.md 4.1.*
- **No, it removed options blindly** (random host): your choice was exposed too, and its survival
  counts in its favour. When the options started equally likely, the survivors, your choice
  included, end up equally likely, so the observation gives no reason to switch. *Proven in the
  model: THEORY.md 4.2.*

Example reading: an expert who rules out vendors they know to be unsuitable, leaving yours and one
other, behaves like an informed host. A filter that drops vendors at random because of a
scheduling conflict behaves like a random host.

### 2. Could the source have eliminated your current choice?

If your choice was protected by the rules, its survival is not evidence. If it was exposed and
survived, its survival is evidence in its favour, in the model by the factor
`(N - M) / (N - M - K)` for blind removal (THEORY.md 4.2).

Example reading: if a candidate you shortlisted yourself was excluded from a screening round, the
round tells you nothing about them. A candidate who went through the same screening as everyone else
and passed has earned some credit.

### 3. Did the source have preferences among the options it could remove?

A preference turns the choice of what to remove into evidence. Seeing the source do what it
usually does is weak evidence; seeing it do what it usually avoids is strong evidence
(THEORY.md 4.3: switching wins `1 / (1 + p)` or `1 / (2 - p)` with three doors). Averaged over
what it might have done, the preference changes nothing, so it only helps if you know the
preference.

Example reading: an advisor who usually recommends dropping the cheapest option and this time
drops the most expensive one is telling you more than usual.

### 4. Would you have been offered this choice at all if you were wrong?

If the offer itself depends on whether your current choice is right, the offer is the
information. The adversarial host in the model offers a switch only when you are right, and
switching after an offer then never helps (THEORY.md 4.4).

Example reading: an unsolicited offer to swap something you hold for something the other party
holds deserves the question "why is this offered to me now?" before any comparison of the two
items.

### 5. Are you looking only at survivors?

Conditional rates computed on survivors can rise without any decision being better. In the model,
staying against the random host rises from `1/3` to `1/2` given no prize was revealed, only
because the other games were discarded (THEORY.md 6). Ask what fraction of cases was discarded and
whether you would have been able to act in them.

### 6. What does each further check cost, and do the returns grow or shrink?

In the model, informed reveals have **increasing** returns: each one concentrates the remaining
probability on fewer options, and the best plan is to buy no checks or all of them, depending on
whether the price per check is below a critical cost such as `1 / N` (THEORY.md 7). If, in your
situation, each extra check is less informative than the last, the model does not apply directly,
and an interior optimum is plausible; the model neither predicts nor verifies that case
(THEORY.md 8.4).

## Using the hypothetical optimum parabola

The parabola is a way to summarise a value-against-effort curve. In the model:

- no fit in the committed sweep was concave, which matches the increasing returns proven in
  THEORY.md 7.1; whether a concave fit would reliably signal diminishing returns is not tested
  here;
- its vertex is a **minimum** whenever the fit is convex, and acting on it was wrong in every
  convex case of the committed sweep (THEORY.md 8.2);
- the end it rates higher matched the exact optimum in 3,559 of 3,600 cases; in the other 41 it
  chose the wrong end and lost the whole gap between the two ends of the curve, at most `7/50` of
  a prize (THEORY.md 8.3).

As a working habit: compute or estimate the value at the extremes and at a few interior points,
check which kind of extremum a smooth fit suggests, and never act on a vertex without that check.

## A worksheet

| What you observe | Closest host | Model it with |
| --- | --- | --- |
| Options removed by someone who knew and never touched your choice | informed | `monty-lab exact --doors N --reveals K` |
| Options removed blindly; you would have been told if the prize was removed | random | `--host random` |
| Options removed by someone with known habits | biased | `--host biased --host-weights ... --observed ...` |
| An offer that appears only in some situations | adversarial | `--host adversarial` |
| Several good outcomes, not one | any | `--prizes M` |
| Some options are more likely from the start | any | `--prior w0,w1,...` (exact up to 10 options) |
| Checks cost something | any | `monty-lab optimum --strategy switch --cost c` |

The model's outputs are exact for the model. Whether a real situation is close enough to one of
these hosts is a judgement the tools cannot make for you.
