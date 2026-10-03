# Vendored models

`observer-model.js` is copied unchanged from
[Gratheon/entrance-observer](https://github.com/Gratheon/entrance-observer) `3d-model/observer-model.js`,
so this repo builds on its own. The Robotic Beehive mounts it on the cabinet front with
`buildObserver({ context: 'robot', ... })`.

Refresh it after the Entrance Observer model changes:

```bash
npm run sync-observer   # needs ../../entrance-observer next to this repo
```

`tests/test_sequences.py` fails if the copy drifts from a sibling checkout.
