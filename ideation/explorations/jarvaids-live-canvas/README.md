# Jarvaids live canvas prototype

This folder preserves the interactive prototype published at
`https://jarvaids-live-canvas.julievanveelen6.chatgpt.site/`, updated on 20 October
2026.

Open `index.html` to inspect the prototype. It includes the project picker,
search and board creation, live-transcript layout, draggable canvas items,
editable notes and text, connectors, undo, uploads, PDF previews and the
project-home navigation.

The current snapshot includes provisional local image analysis, multi-region
sticky-note selection, browser speech recognition, teammate attribution and
wake-phrase canvas commands. A new session starts with an empty transcript and
an explicit Start recording control. Generated notes remain provisional until
a person accepts them.

The localhost version also connects its recording control to the current audio
capture and optional local `Hey Jarvaids` detector in `app/server`. The same
microphone stream feeds both paths. Detection gives a visible state and chime;
it does not interpret or execute a canvas command because that pipeline is not
implemented yet. The default transcript adapter is synthetic unless the local
Whisper configuration described in `app/server/README.md` is available.

## Status and costs

- This is an ideation prototype, not a design-system exemplar and not the
  production client.
- State is held in the browser session. Reloading the page does not persist
  created projects or canvas changes.
- PDF page rendering loads PDF.js 6.3.289 from jsDelivr when a PDF is uploaded.
  That interaction therefore needs a network connection. The rest of the page
  opens as a local single file.
- The prototype uses visual choices that predate the current canonical design
  system. Do not copy its colours, shadows, gradients, radii or typography into
  production without reconciling them with `app/design-system/`.
- AI-labelled controls are interaction demonstrations only. They do not call a
  model. Model-created content remains provisional until a person accepts it.

## Verification

The checked-in file is an exact copy of the latest deployed source at the time
of import. Its SHA-256 digest is
`D998FA0F984C5A163EB99DFDCD957D6E3E0C9D10883429CF668F1303FF832E95`.
