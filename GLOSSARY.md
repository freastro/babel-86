# Babel-86

A desktop app that takes one live mono speech input and plays translations of it in up to four languages at once, each sent to its own output device and channel. Its interface imitates 1980s rack gear.

## Language

### The rack

**Rack**:
The single window holding the Input Unit, every Language Unit and the Blank Panel.
_Avoid_: Dashboard, main window, mixer

**Input Unit**:
The top unit of the Rack, which captures, trims and meters the one mono speech source.
_Avoid_: Source panel, input strip

**Language Unit**:
A unit of the Rack that produces one translated output in one target language. A Rack holds zero to four.
_Avoid_: Output unit, channel strip, language row

**Blank Panel**:
The 1U panel at the bottom of the Rack that adds a Language Unit, and reads RACK FULL once four exist.
_Avoid_: Add button, empty slot

**Channel Colour**:
One of six pastels that identifies a Language Unit. The Input Unit uses brand blue instead.
_Avoid_: Theme, accent, language colour

### Speech and translation

**Source**:
The one mono speech stream, taken from one channel of one input device, that every Language Unit translates.
_Avoid_: Input stream, mic

**Source Language**:
The language spoken in the Source, set in Input Setup.
_Avoid_: Input language

**Target Language**:
The language one Language Unit translates into.
_Avoid_: Output language, destination language

**Translation Model**:
The choice made per Language Unit of what turns the Source into its Target Language: Gemini 3.5, Qwen 3.8 or Pass-thru.
_Avoid_: Engine, backend, service

**Provider**:
The company whose cloud service backs a Translation Model, either Google (Gemini) or Alibaba Cloud (Qwen). Pass-thru has none.
_Avoid_: Vendor, API

**Pass-thru**:
A Translation Model that plays the Source audio, after gain, untranslated and without involving any Provider.
_Avoid_: Bypass, original audio mode

**Transcript**:
The recognised text of the Source speech.
_Avoid_: Captions, subtitles

**Translation**:
The translated text for one Language Unit, shown alongside its translated audio.
_Avoid_: Output text

### Controls and state

**Power**:
The master switch that starts or stops capture and opens or closes every Provider session. It is always off at launch.
_Avoid_: On/off, start

**Mute Input**:
Stops new Source speech from going out but lets translations already in flight finish playing.
_Avoid_: Mute source, pause

**Mute**:
Silences one Language Unit's audio output only, while its translation continues.
_Avoid_: Mute output, solo

**Gain**:
The trim, from −24 to +24 dB, applied to the Source before metering and sending.
_Avoid_: Volume, input level

**Level**:
The trim, from −24 to +24 dB, applied to one Language Unit's output before its meter.
_Avoid_: Volume, fader

**Status**:
The word and lamp showing one Language Unit's health: TRANSLATING, IDLE, ERROR or OFF.
_Avoid_: State, health

**Drain**:
The period after Mute Input while sessions finish translating and playing speech already sent.
_Avoid_: Flush, tail

**Setup**:
The modal dialog, opened from a unit, where its device, channel and language are chosen. The Language Setup dialog is also the only place the Translation Model is chosen.
_Avoid_: Settings, preferences, config

### Display

**Display**:
A black inset window with glowing monospace text. It is the visual theme of the Rack: VFD teal by default, with red LED and amber LCD alternates.
_Avoid_: Screen, readout

**Level Meter**:
An 18-segment LED peak meter, green, amber then red, with a short peak hold.
_Avoid_: VU meter, bar graph

**Chrome**:
Fixed Latin labels on the faceplates, such as kickers, captions and meter legends. Contrast with user content, which can be in any script.
_Avoid_: Labels, UI text
