# Babel-86 — Desktop App Design Document

Oct 17, 2026 · @Greg

## Overview

Babel-86 is a desktop app for Windows and macOS. It takes one mono speech input and plays live translations of it in up to four languages, each sent to its own output device and channel. The interface is styled as a 1980s effects rack: an input unit on top and one unit per language below. This document is the build spec Claude should implement from. The approved visual reference is the [Babel-86 design canvas](https://claude.ai/code/artifact/aa37d63b-264e-4c04-bf68-f2157d57a824), whose source files `Main.dc.html` (rack) and `OutputSetup.dc.html` (language setup dialog) define the look exactly.

**Goals for v1**

- Translate one live mono speech source into 1–4 target languages at the same time.
- Let each language use its own engine: Gemini 3.5, Qwen 3.8, or Pass-thru (original audio, untranslated).
- Route each language to a chosen output device and channel.
- Show the input unit and all four language units on one 1920×1080 screen, usable by mouse or touch.
- Let the operator mute the input without cutting off translations that are still playing.

**Out of scope for v1**

- Stereo or multi-channel sources, and more than four target languages.
- Automatic source-language detection (removed from the design; the source language is set in Input Setup).
- Recording, caption or subtitle outputs, and EQ or effects processing.
- Linux and mobile builds.

## Tech stack

Build Babel-86 with **Tauri 2**: a Rust core for audio and networking, and a React + TypeScript interface ported from the canvas files. Native audio in Rust is needed because the app must capture from one device channel and play into specific channels of other devices. Browser audio APIs (the Electron route) can choose an output device but not a channel within it.

| Layer | Choice | Why |
| --- | --- | --- |
| Shell and packaging | Tauri 2 (MSI or NSIS installer on Windows, signed and notarized DMG on macOS) | Small footprint; native window; the web UI can reuse the canvas markup almost unchanged |
| UI | React 18 + TypeScript, plain CSS variables for tokens | The canvas artboards are already component-shaped (unit, knob, meter, LED button) |
| Audio I/O | `cpal` (WASAPI on Windows, CoreAudio on macOS) | Device and channel enumeration, low-latency capture and playback |
| Resampling | `rubato` | Device rate (usually 48 kHz) to 16 kHz for the providers, and 24 kHz provider audio back to the device rate |
| Provider connections | `tokio` + `tokio-tungstenite` (WebSocket over TLS) | Both translation services stream over WebSockets |
| Secrets | `keyring` (Windows Credential Manager, macOS Keychain) | API keys never stored in plain config files |
| Settings | `serde` JSON in the OS app-config folder | Restores the rack exactly as it was left |

On macOS the app needs a microphone usage description (`NSMicrophoneUsageDescription`), or capture is silently denied.

## System architecture

One input stream is captured, trimmed and metered once, then copied to an independent pipeline for each language. The React UI only displays state and sends commands; all audio and network work happens in the Rust core.

&#91;embedded content: Babel-86 architecture · one input, up to four language pipelines\]

Mute Input closes the gate before the fan-out, so each pipeline finishes what it already sent. In a Pass-thru pipeline the provider adapter simply returns its input, and nothing leaves the machine.

## Translation providers

Each language unit runs its own streaming session, because both services take one target language per session. All three options sit behind one adapter interface, so the audio engine never knows which service it is talking to.

|  | Gemini 3.5 | Qwen 3.8 | Pass-thru |
| --- | --- | --- | --- |
| Model ID | `gemini-3.5-live-translate-preview` | `qwen3.8-livetranslate-flash-realtime` | none (local) |
| Endpoint | Gemini Live API, WebSocket `BidiGenerateContent` | Alibaba Cloud Model Studio (DashScope), WebSocket `/api-ws/v1/realtime`; host varies by region | n/a |
| Auth | API key | Bearer API key plus workspace ID | n/a |
| Audio in | 16-bit PCM, 16 kHz, mono, 100 ms chunks | 16-bit PCM, 16 kHz, mono | device audio as-is |
| Audio out | 16-bit PCM, 24 kHz, mono | 16-bit PCM, 24 kHz, mono | the source audio |
| Target language setting | `translationConfig.targetLanguageCode` (BCP-47) | `translation.language` | n/a |
| Text returned | source transcript and translated transcript (both opt-in) | translated text deltas; source transcript needs a separate opt-in | none |
| Languages | 70+ | 60 for text, 29 for spoken output | any |

**Adapter contract** (one Rust trait, three implementations):

1. `start(target_language)` opens the session and reports `Connected` or an error.
2. `push_audio(chunk)` sends 100 ms of 16 kHz mono PCM.
3. `end_input()` sends the service's end-of-input signal but keeps the session open, so speech already sent is still translated and played.
4. The adapter emits events: `SourceText`, `TranslatedText`, `TranslatedAudio`, `Idle`, and `Error { retryable }`.
5. `close()` ends the session.

The setup dialog must only offer languages the chosen model can speak. Qwen 3.8 speaks 29 languages, fewer than it can transcribe.

The model IDs above are preview names taken from the providers' pages on 17 October 2026. Check them against current docs before building.

## UI specification

The app is one window holding one rack: the input unit, up to four language units, then a 1U blank panel. There is no title bar, menu bar or side panel; every control lives on a rack unit. Port the layout from `Main.dc.html` exactly; the notes below are the rules that must survive the port.

**Rack frame**

- Dark rack (`#0b0b0c`) centred in the window, max 1880 px wide, 16 px window padding, 3 px gaps between units.
- Every unit has a 34 px rack ear on each side with two screw heads, and an 8 px identity stripe inside the left ear: brand blue on the input unit, the language's colour on each language unit.
- At 1920×1080 the whole rack (input unit plus four language units plus the 1U panel) must fit without scrolling: about 820 px tall.

**Shared four-column layout.** The input unit and every language unit lay out their sections in the same columns, so matching sections line up down the rack. Headers sit on the top edge of each row.

| Column | Width | Input unit | Language unit |
| --- | --- | --- | --- |
| 1 Identity | 300 px fixed | Power button, Babel-86 logo, subtitle | Language code display, label, model name, device and channel |
| 2 Control | 440 px fixed | SOURCE: source display, Mute Input and Setup buttons | STATUS: status light and word, Mute and Setup buttons |
| 3 Level | grows 1, base 400 px | INPUT: gain knob and level meter | OUTPUT: level knob and level meter |
| 4 Text | grows 1.3, base 480 px | TRANSCRIPT: recognised source speech | TRANSLATION: translated text |

Below about 1500 px wide, columns wrap onto a second line rather than shrinking or clipping.

**Components**

- **Section header:** a small coloured tag (10 px bold caps, 0.2 em tracking, 2×6 px padding) followed by a 1 px rule to the end of the column. Input unit headers use brand blue with ivory text; language unit headers use that language's colour with dark text.
- **Knob:** 46 px, rotates −135° to +135° for −24 to +24 dB, with 0 at the top. Scale labels −24 / 0 / +24 around it and a caption under it (GAIN or LEVEL). The cap takes the unit's header colour. Drag vertically, scroll, or use arrow keys (1 dB steps, Shift for 0.1 dB); double-click or double-tap resets to 0 dB.
- **Level meter:** 18 LED segments at −48, −42, −36, −30, −24, −20, −16, −12, −10, −8, −6, −5, −4, −3, −2, −1, −0.5 and 0 dBFS. Green below −6, amber from −6 to −2, red from −1. Scale labels −48, −24, −12, −6, −3 and 0 sit under their own segments. Peak meter, about 10 ms attack and 300 ms release, with a 1 s peak-hold on the red segments.
- **Glowing display:** black inset window with mono type in the display colour (VFD teal `#7df5dd` by default). Used for the source display, the language code, the transcript and the translation. Text panels hold two lines and keep the newest text, trimming from the start.
- **Latching button:** at least 44×44 px for touch, with an 8 px indicator light; `aria-pressed` reflects the state.
- **Status light:** an 18 px lamp plus a word: green TRANSLATING, yellow IDLE, red ERROR, dark OFF.

## Visual design tokens

The palette is a deep brand blue plus six soft pastels, one per language; status and meter colours are reserved for meaning and never used as decoration. Define these as CSS variables.

| Token | Value | Used for |
| --- | --- | --- |
| `--brand-blue` | `#2f5c9e` | Logo bar, input unit stripe, input headers, gain knob cap |
| `--ivory` | `#f4efe2` | Text on brand blue |
| `--lang-coral` | `#e8806a` | Language colour option |
| `--lang-saffron` | `#e9b04e` | Language colour option |
| `--lang-chartreuse` | `#bcc65a` | Language colour option |
| `--lang-jade` | `#5cb89f` | Language colour option |
| `--lang-plum` | `#ad8fd2` | Language colour option |
| `--lang-rose` | `#df84ab` | Language colour option |
| `--ink` | `#141210` | Text on pastel headers and cream buttons |
| `--face-input` | `#d6cfbd` to `#c4bca8` (top to bottom) | Brushed champagne input faceplate |
| `--face-output` | `#232325` to `#19191b` | Black anodised language faceplates |
| `--rack` | `#0b0b0c` | Rack frame |
| `--display` | `#7df5dd` with an 8 px glow | Glowing displays (VFD); red LED `#ff4b3a` and amber LCD `#ffb340` are alternate themes |
| `--ok` | `#3ddc6a` | Translating light, meter below −6 dB |
| `--warn` | `#f2c230` (lamp) / `#ffb020` (meter) | Idle light, meter −6 to −2 dB |
| `--alert` | `#ff3b2f` | Error light, mute lights, meter from −1 dB |

**Type.** All three are Google Fonts; bundle them with the app so it works offline.

- Michroma for the Babel-86 wordmark and language labels.
- Archivo Narrow 600–700 for panel captions, in capitals with wide tracking.
- Share Tech Mono for every glowing display and scale label.

**Sizes.** Touch targets are at least 44×44 px. Knobs are 46 px, status lamps 18 px and indicator lights 8 px. Corners are 2–6 px, and every unit has 14 px vertical and 22 px horizontal padding.

## Behaviour and state rules

The key rule: muting the input stops new speech going out but lets translations already in flight finish, because translation runs a few seconds behind the speaker.

| Control | What it does | Visible result |
| --- | --- | --- |
| Power | Starts or stops audio capture and opens or closes every provider session | Off: displays and lights go dark, meters empty, status OFF |
| Mute Input | Stops sending audio to every session and calls `end_input()`; sessions stay open and keep playing what they already have | Light red, source display reads MUTED, input meter empty; outputs keep playing until they drain |
| Input Gain | Digital trim, −24 to +24 dB, applied before metering and before sending | Input meter follows; pointer moves |
| Setup (input) | Opens the input setup dialog (to be designed: source device, channel and language) | Dialog |
| Mute (language) | Silences that language's audio output only; its session keeps running | Light red; that meter empties; translation text keeps updating |
| Level (language) | Output trim, −24 to +24 dB, applied before that language's meter | Meter follows |
| Setup (language) | Opens the language setup dialog prefilled with that unit's settings | Dialog |
| Add language output | Opens the setup dialog in Add mode; disabled once four languages exist | The 1U panel reads RACK FULL · 4 LANGUAGES |

**Status light for each language**

- **Green, TRANSLATING:** the session is connected and has produced translated audio or text in the last 3 s.
- **Yellow, IDLE:** the session is connected but quiet, the input is muted and drained, or the model is Pass-thru.
- **Red, ERROR:** the connection failed, authentication was rejected, or no response came for 10 s while audio was being sent. The translation panel shows a one-line reason in red, such as "ERR · Translation engine not responding. Retrying…".
- **Dark, OFF:** the power is off.

**Errors and recovery.** A retryable error reconnects automatically with backoff of 1, 2, 4, 8 and then every 15 s, while the light stays red. A non-retryable error (bad key, unsupported language) stays red until the user changes the setup. One language failing never affects the input or the other languages.

**Pass-thru** sends the input audio, after gain, straight to that language's output with no service involved. Its panel reads "\[ORIGINAL AUDIO PASSED THROUGH — NOT TRANSLATED\]".

## Language setup dialog

One modal dialog handles both adding and editing a language. It is the only place the model is chosen. Port it from `OutputSetup.dc.html`: a 560 px dark panel over a dimmed rack, with a header strip, the pastel band, five fields and a footer.

| Field | Control | Default when adding | Rules |
| --- | --- | --- | --- |
| Target language | Dropdown of `CODE · Name` | First language not already in the rack | Only languages the chosen model can speak; the 2-letter code drives the big display |
| Label | Free text, up to 24 characters | The language's native name, e.g. Español | Fills automatically when the language changes, until the user types their own |
| Translation model | Three latching buttons: Gemini 3.5, Qwen 3.8, Pass-thru | Gemini 3.5 | Pass-thru shows a line explaining that audio is sent untranslated |
| Output device | Dropdown of output devices from the OS | The device used by the last language | Lists live devices; shows a missing device as "\[name\] (disconnected)" |
| Channel | Dropdown CH 1 to CH n, where n is that device's channel count | Next channel not in use | Warn, but allow, two languages on one channel |
| Channel colour | Six 44 px swatches | First colour not in use | Colours the stripe, headers and level knob cap |

**Header:** OUTPUT nn · SETUP above ADD LANGUAGE or EDIT LANGUAGE, with a live preview of the language code and colour.

**Footer:** Cancel, and Add to rack (Add mode) or Save (Edit mode). Edit mode also shows Remove language, which asks for confirmation if that language is live. Esc cancels and Enter confirms; focus is trapped inside the dialog and returns to the button that opened it.

Saving restarts only that language's session, and only if the language, model or key changed. Changing device, channel, label or colour applies without a reconnect.

## Data model and persistence

The whole rack is one JSON file, `babel86.json`, in the OS app-config folder. It is saved 500 ms after any change and loaded at launch. API keys are never stored in it; they live in the OS keychain under the service name `babel86`, one entry per provider.

```json
{
  "version": 1,
  "display": "vfd",
  "input": {
    "deviceId": "<os device id>",
    "channel": 1,
    "sourceLanguage": "en",
    "gainDb": 4.0,
    "muted": false
  },
  "outputs": [
    {
      "id": "a1b2",
      "targetLanguage": "es",
      "label": "Español",
      "model": "gemini",
      "deviceId": "<os device id>",
      "channel": 1,
      "color": "jade",
      "levelDb": -2.0,
      "muted": false
    }
  ]
}
```

- `model` is one of `gemini`, `qwen` or `pass`. `color` is one of the six pastel names. `outputs` holds 0–4 items, in rack order.
- Store devices by OS device ID plus the last-seen name. If a device is missing at launch, keep the unit, show it as disconnected in the route line, and set its status to ERROR.
- Power always starts off at launch, so the app never streams audio to a service before the operator presses it.

**Live state** (not saved) flows from the Rust core to the UI as events: meter levels at 30 Hz per unit, status changes, transcript and translation text, and errors. The UI sends commands back: power, mute, gain or level, and setup changes.

## Non-functional requirements

Most of the delay a listener hears comes from the translation services (Qwen 3.8 reports about 2.3 s average lag), so the app's own job is to add as little as possible on top.

| Area | Requirement |
| --- | --- |
| Added latency | App-side capture, resampling, buffering and playback add no more than 150 ms per path. Pass-thru stays under 50 ms end to end. |
| Audio safety | The audio callback never allocates, locks or waits on the network; lock-free ring buffers sit between the callback and the provider tasks. Underruns play silence, never stale audio. |
| Load | Four live sessions use under 10% CPU on a 2022-era laptop (target; measure in Milestone 6). |
| Isolation | Each language runs as its own async task; a crash, error or stall in one never stops the input or the other languages. |
| Long sessions | Runs for 8 hours unattended. Provider sessions that time out reconnect on their own, and meters and text keep updating. |
| Device changes | Unplugging a device marks the affected units ERROR without crashing; replugging it recovers automatically. |
| Security | Keys only in the OS keychain; TLS for every connection; no audio or text written to disk or sent to any third party other than the chosen provider. |
| Privacy | The first launch shows which providers receive audio, and power starts off every launch. |
| Accessibility | Every control reachable by keyboard with a visible focus ring. Knobs expose `role="slider"` with their dB value. Status is always shown as a word as well as a colour. Text contrast is at least 4.5:1. |
| Platforms | Windows 10 and 11 (x64, ARM64); macOS 13 and later (Apple silicon and Intel). |

## Build plan for Claude

Build in seven milestones, each ending in something runnable. Do not start a milestone until the previous one meets its check.

1. **Scaffold.** Create the Tauri 2 + React + TypeScript project, CSS tokens and bundled fonts. Port the rack and setup dialog from the canvas as static components driven by mock state.
   - Check: at 1920×1080 the rack matches the canvas side by side, with no scrolling and all four columns aligned.
2. **Interactive UI.** Wire up the knobs (drag, scroll, keys), latching buttons, the setup dialog in Add, Edit and Remove modes, and JSON persistence.
   - Check: every control works with a mouse, by touch and from the keyboard; the rack restores after a restart.
3. **Audio engine.** Use `cpal` to list devices and channels, capture one input channel, apply gain, run the meters, and play into chosen output channels. Pass-thru works end to end.
   - Check: a Pass-thru language plays the microphone on its chosen channel with under 50 ms delay, and the meters are accurate to within 1 dB of a reference tone.
4. **Provider adapters.** Write the adapter trait, then Gemini 3.5 and Qwen 3.8 adapters with resampling, keychain-stored keys and a key entry screen.
   - Check: English speech produces spoken and written Spanish on one unit with each provider.
5. **Multi-language and states.** Run up to four sessions at once, with status lights, mute-input draining, error display and reconnection.
   - Check: four languages run together; Mute Input lets translations in progress finish; pulling the network turns lights red, and restoring it recovers them.
6. **Hardening.** Handle device hot-plug, run an 8-hour soak test, profile CPU, and complete the accessibility pass.
   - Check: the non-functional requirements table passes.
7. **Packaging.** Produce a signed Windows installer and a signed, notarized macOS DMG, and verify the microphone permission prompt.
   - Check: a clean machine installs, launches and translates.

**Working notes for Claude**

- The canvas `.dc.html` files are the visual source of truth; when this document and the canvas disagree on looks, the canvas wins. On behaviour, this document wins.
- Before writing either adapter, confirm the model IDs, message names and audio formats against the providers' current docs; the services are in preview and may change.
- Keep provider code behind the adapter trait so a third service can be added without touching the UI or the audio engine.

## Open questions

- [ ] Input setup dialog: confirm its fields (source device, channel, source language) and design it to match the language dialog.
- [ ] Source language: neither service's page shows a source-language setting. Is the Input Setup choice only a label, or should it be sent as a hint where supported?
- [ ] Transcript panel: which session supplies the source transcript? Proposal: the first Gemini session with input transcription on; if every language is Pass-thru, the panel stays empty.
- [ ] Keys and billing: does each operator bring their own Gemini and Alibaba Cloud keys, and which Alibaba Cloud region should Qwen use?
- [ ] Output level range: keep −24 to +24 dB, or change to a fader range of off to +12 dB?
- [ ] Qwen 3.8's spoken output keeps the original speaker's voice, and Gemini 3.5's page does not say whether its voice does. Is a different-sounding voice per language acceptable?
- [ ] Is Linux needed later? Tauri and `cpal` support it, so it is mostly a packaging task.

## Sources

- [Live translation with Gemini Live API](https://ai.google.dev/gemini-api/docs/live-api/live-translate) (Google AI for Developers)
- [Qwen3.8-LiveTranslate: names the speaker, carries the meaning](https://www.alibabacloud.com/blog/qwen3-8-livetranslate-names-the-speaker--carries-the-meaning-_603581) (Alibaba Cloud blog)
- [Babel-86 design canvas](https://claude.ai/code/artifact/aa37d63b-264e-4c04-bf68-f2157d57a824)
