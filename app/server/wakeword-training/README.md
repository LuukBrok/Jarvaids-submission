# Custom Hey Jarvaids model

**Status: not trained.** The integration must remain unavailable without the
custom model. A reference Hey Jarvis asset tests installation only and must
never be relabelled as Hey Jarvaids. The notebook here has not been executed;
current hosted-runtime compatibility and pronunciation remain unverified.

## Hosted training

Open [the project notebook in Colab](https://colab.research.google.com/github/ptborst/GenAI/blob/feature/hey-jarvaids-wakeword/app/server/wakeword-training/hey_jarvaids.ipynb).
For this private repository, upload the notebook manually if the link cannot
authenticate. Use a Linux GPU runtime. Run one cell at a time, not Run all.

The notebook derives from openWakeWord commit
`c8ef6912c5feccf1037b852d9bc6c7ed644135ba` (v0.6.0),
[automatic_model_training.ipynb](https://github.com/dscripka/openWakeWord/blob/c8ef6912c5feccf1037b852d9bc6c7ed644135ba/notebooks/automatic_model_training.ipynb).
The upstream Apache-2.0 licence is retained in `UPSTREAM-LICENSE`.
Changes: fixed engine checkout, custom phrase/configuration, seeded Python,
NumPy and Torch, explicit audition gate, and environment/checksum export.

The inherited TensorFlow 2.8.1 training pins may not install on a current Colab
Python runtime. Do not silently upgrade packages and claim the original run is
reproduced. Choose a compatible Linux runtime or resolve the training environment
and save its exact Python version, package lock, notebook and upstream commits.
Seeds do not promise bit-identical GPU training. Piper, datasets and downloads
in the upstream workflow are not all immutable: pin their actual revisions and
hashes in the completed run record before declaring training reproducible.

1. Install the environment and obtain the public synthetic-generation assets and
   background datasets named in the notebook. Review each dataset/voice licence.
   No teammate audio is uploaded. Downloads and a GPU session have time/storage
   costs; free hosted GPU availability is not guaranteed.
2. Start with `config.json`: 5,000 synthetic training examples, 1,000 synthetic
   validation examples, 10,000 steps and an untuned detection threshold of 0.5.
   These are candidate settings, not measured accuracy claims. The phonetic
   generation text is `hey jar vaydz`, while the visible phrase is Hey Jarvaids.
3. Generate clips. Select target clips across distinct synthetic voices and
   listen for **Hey Jar-vaydz**. The audition cell lists paths and hashes; make
   sure they are target clips, not adversarial examples. Record at least 30
   audited target examples and the voice IDs. Regenerate if the pronunciation
   is wrong. Only then set `pronunciation_reviewed = True`.
4. Augment and train. Export `hey_jarvaids.onnx`, the resolved YAML, complete
   package versions, Python version, source commits, dataset/voice versions and
   hashes, training metrics, seed and audition notes. Keep separate synthetic
   validation data. Do not tune against the held-out human pilot.
5. Download the matching supporting assets from release v0.5.1:

   | Asset | SHA-256 |
   | --- | --- |
   | [melspectrogram.onnx](https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx) | `ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f` |
   | [embedding_model.onnx](https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx) | `70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f` |

   Recalculate SHA-256 after downloading. The backend never downloads assets.
   Consult [upstream licensing](https://github.com/dscripka/openWakeWord/tree/v0.6.0#license):
   code is Apache-2.0; included pretrained models are CC BY-NC-SA 4.0.
   Do not assume code licensing grants commercial rights to weights, voices or
   training datasets. Record the actual licence and attribution for every input
   and the resulting custom weights; redistribution clearance is still pending.

## Import the completed model

Copy `training-record.example.json` to a local run record. Replace every pending
field with actual evidence. Set status to `trained` only after training, and
pronunciation review to true only after listening. Put assets and evaluation
recordings outside Git, for example under `.local/wakeword/` and
`../../evidence/raw/wakeword/`. Commit only non-identifying run metadata.

From `app/server`, with Python available:

```sh
python wakeword-training/package_model.py --keyword /path/hey_jarvaids.onnx --melspectrogram /path/melspectrogram.onnx --embedding /path/embedding_model.onnx --training-record /path/training-record.json --output .local/wakeword/model
```

The importer checks declared hashes and provenance, copies to a new directory
and produces `manifest.json`. It cannot establish what a model recognises:
that requires the real microphone pilot in [PILOT.md](PILOT.md).
