# Figgie Trading Arena

A simplified four-player trading game for testing information-based pricing and majority incentives.

## Overview

The question is whether information about a player's opening hand and the payoff from holding a majority of the goal suit improve trading decisions. The simulator is inspired by [Figgie](https://www.figgie.com/how-to-play), with a deliberately simplified turn-based market.

## Method

- Generate candidate 40-card deck compositions and infer the probability of each goal suit using combinatorial likelihoods of the opening hand.
- Estimate marginal card value from the goal probability and a heuristic for the majority bonus.
- Compare four bots: baseline, hand information only, majority bonus only, and both signals together.
- Rotate quoting roles, randomize seats across rounds and record net game-chip P&L.

## Run

```bash
python figgie_arena.py simulate --rounds 1000 --seed 42
python figgie_arena.py play --seed 42
```

Use `--turns` to change the number of quote opportunities per round. The simulation reports the mean and standard error of P&L.

## Reproduced results

Seed 42, 1,000 rounds, default 60 quote opportunities per round; mean 27.9 completed trades per round.

| Bot | Mean chips/round | Standard error |
|---|---:|---:|
| Baseline | −15.71 | 0.43 |
| Hand only | −8.42 | 1.15 |
| Bonus only | +7.61 | 1.74 |
| Hand + bonus | +16.52 | 1.94 |

The combined bot led in this particular simulated population. This is evidence about the heuristic in the arena, not proof of an optimal strategy or an advantage over real Figgie players.

## Limitations and next steps

The arena uses simplified quoting and a fixed majority heuristic. It is not the full real-time game and is not affiliated with its creators. Future work: update beliefs from observed trades, vary opponents, and repeat experiments over multiple seeds.

## Requirements and files

Python 3.9+; no third-party dependencies are required.

- `figgie_arena.py` — original project implementation.
- `requirements.txt` — dependency notes.
- `results/` — outputs from the example run, including [terminal output](results/example_run.txt).

The example was rerun using the bundled source. This is a research/educational project; it is not a production system.
