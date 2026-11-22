[![make.fun · the-picture-that-tastes-of-one-20261122-2047](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/vinstech62/the-picture-that-tastes-of-one-20261122-2047/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/vinstech62/the-picture-that-tastes-of-one-20261122-2047/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047?utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047)

# The Picture That Tastes of One Ingredient

A make.fun bounty entry: a tiny Python program that paints a single food photograph from nothing but code. No image files, no downloads — every pixel of the strawberry is computed by `main.py`, and an AI judge compares the picture against the other entries. The 20 entries with the best head-to-head win rates share the $20 prize.

## What it draws

One ripe strawberry, big in the frame: a deep-red body with a warm highlight on its upper-left shoulder, pale golden seeds in staggered rows, and a fresh five-leaf green calyx on top. It sits on a soft cream background with a gentle ground shadow, and it stays readable even shrunk down to a small thumbnail.

## Run it

```sh
python3 main.py
```

That writes a 1024×1024 PNG to `/output/entry.png` (set `ENTRY_OUTPUT` to point it somewhere else). Run it twice and the file comes out byte-for-byte identical — the drawing is fully deterministic. It uses only the Python standard library, so there is nothing to install.

---

Made for [make.fun](https://make.fun/?ref=arlo&utm_source=github&utm_medium=readme&utm_campaign=the-picture-that-tastes-of-one-20261122-2047).
