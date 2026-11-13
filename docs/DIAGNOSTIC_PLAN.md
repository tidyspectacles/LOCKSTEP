# LOCKSTEP diagnostic prototype plan

**Purpose:** determine whether MPC Live III pad events are visible to an add-in, without changing playback, while separately investigating external MIDI as a practical fallback.

**Current state:** research and design only. No diagnostic source code, MIDI processor, binary or installer has been created. Nothing should be installed on the MPC yet.

**Confirmed target:** Akai MPC Live III running MPC OS 3.10.1 (confirmed by the user on 2026-11-13). Treat this as the baseline for compatibility research; re-check the version before any future device test.

## Safety rules

- Read-only observation: no MIDI writes, note suppression, note injection, audio processing, transport control or filesystem changes on the MPC beyond an explicitly selected diagnostic log.
- Every intercepted API call must call the original function with the original arguments and return its original result unchanged.
- If a hook cannot resolve the original function, initialization fails safely and the hook must not interfere with MPC.
- Diagnostic logging must be bounded, rate-limited and performed away from real-time audio callbacks.
- The add-in must be disabled by default unless an explicit diagnostic enable flag is present.
- Include a documented uninstall/recovery path before any device test.
- Do not test during a performance or on a device containing the only copy of important projects.

## Internal-pad investigation

**New research lead (2026-11-13):** Akai's official port documentation lists dedicated **MPC Pads** and **MPC Keyboard** ports on all standalone MPCs. Akai describes these as the ports for controlling the MPC pads and keyboard. Its multi-MIDI guide says the MPC Pads port is an example of a port with Global enabled, meaning its MIDI data always goes to the currently selected program. This is a much more specific target than the controller-button Private port used by Skipback. See [MPC_PAD_PORT_RESEARCH.md](MPC_PAD_PORT_RESEARCH.md).

This still does not prove the pad performance events are ordinary note messages on an ALSA raw-MIDI handle, nor that they can be intercepted/reinjected safely. First identify the OS-level device corresponding to the named MPC Pads port. Do not change its Global/Control/Track settings as an experiment.

The original goal remains transparent quantisation of the MPC's own performance pads. The diagnostic questions are:

1. Which ALSA raw-MIDI input handle (if any) corresponds to Akai's named MPC Pads port?
2. Do performance pad presses produce data on that handle, rather than only hardware-button/control messages?
3. Can we distinguish pad note-on, pad note-off, velocity, channel, repeated hits and simultaneous pads?
4. Are events timestamped at the input boundary, or can sufficiently accurate monotonic timestamps be captured in the read hook?
5. Does observing the port leave normal pad playing completely unchanged?

Test matrix: idle baseline; non-performance hardware buttons; single pad at several strengths; hold/release; repeated hits; simultaneous pads; and bypass comparison. Record model, OS, selected track/program, port identity and test conditions. Do not publish logs containing personal device identifiers or unrelated MIDI controller data.

**Go/no-go:** proceed only if pad events are positively identified, release semantics and velocity are understood, simultaneous events are preserved, observation has no side effects, and a credible safe suppression/reinjection path exists. If not, retain built-in-pad support as unproven and focus on external MIDI.

## MPC MIDI Clock output

Akai documents that an MPC output port can have Sync enabled and then send the configured sync type under MIDI / Sync > Sync Send. The Live III's physical 5-pin MIDI outputs are MPC A and MPC B. This offers a possible external clock reference for a Windows-based or standalone processor. It is not assumed to be enabled and must be verified separately; no settings should be changed during the initial read-only pad-port inspection. The offline MIDI Clock follower is a model only, not connected to the MPC.

## External MIDI fallback

A separate feasibility route is now documented in [EXTERNAL_MIDI_FALLBACK.md](EXTERNAL_MIDI_FALLBACK.md). This is not merely theoretical MIDI routing: Akai documents external DIN and direct USB MIDI input ports on the Live III, and normal tracks can select a MIDI input port and channel. However, normal routing does not quantise notes. LOCKSTEP would still need to prove it can safely process one selected incoming port and feed the corrected stream into a normal MPC track without duplicates or stuck notes.

The external route should be investigated independently of the internal-pad route. First identify the physical/USB input handles and prove read-only observation; then test the scheduler offline; only after that investigate controlled processing and reinjection. A Windows-based external MIDI processor remains a possible fallback if an in-MPC add-in cannot safely intercept and re-route the input. Do not choose cables or software until the user's controller and connection options are known.

## ALSA RawMIDI observation detail (2026-11-13)
## Reference add-in implementation inspected (2026-11-13)
## Observation is not quantisation (design boundary)

A passive hook can tell us whether note data crosses a particular API. It cannot, by itself, implement LOCKSTEP. A working quantiser must also prove all of the following on the same route:

1. **Original-note control:** a reliable point exists to hold or suppress the unquantised note before the target program receives it.
2. **Correct reinjection:** a corrected note can be delivered to the intended program/track without being mistaken for a new external input, duplicated, looped back, or routed to the wrong selected program.
3. **Timing:** the scheduler can release note-on and note-off events against the MPC's actual tempo/transport timeline without blocking MPC's MIDI read path or audio thread.
4. **Failure behaviour:** bypass, stop, project/track changes, overload and add-in shutdown cannot leave notes stuck or lose the original stream.

Do not attempt to quantise by sleeping inside an ALSA read hook or by holding up MPC's reader thread. The diagnostic phase must first identify the data path. A later processing design may require a separate bounded queue and a distinct supported output route; whether such a route exists for internal pads remains unproven.

This is an explicit gate: **seeing pad note bytes is necessary evidence, not proof that transparent internal-pad quantisation is feasible.**


The public `jacob-sabella/mpc-addin-usb-audio` source is a useful implementation reference for add-in engineering, but it is **not** a MIDI-note interception example. Its README and source show several practices worth carrying into LOCKSTEP:

- Check `/proc/self/exe` and activate only inside the actual `/usr/bin/MPC` process; in every other process, hooks are plain pass-through.
- Resolve the next implementation with `dlsym(RTLD_NEXT, ...)`, rather than opening a second copy of libasound. The Open MPC add-in guide further warns that hook order matters and that resolving libc's own `dlsym` may need special care if another add-in interposes it.
- Keep real-time callbacks free of locks, allocations, syscalls and logging; copy bounded data to a preallocated single-producer/single-consumer ring and let a separate worker handle it.
- Include host-side tests with fake library functions and a fake MPC process before attempting hardware.
- Treat missing symbols or uncertain device identity as a reason to stay inactive, not to guess.

These are design patterns only. The example hooks ALSA PCM audio functions, not ALSA RawMIDI or Sequencer note events; it does not establish that MPC pad notes are available through either MIDI API. Its device support claims also do not prove compatibility with this specific Live III setup.

**LOCKSTEP-specific additional guard:** even a perfectly transparent read-only hook would still be loaded into the MPC process at startup. The first build should therefore be an offline-tested, disabled-by-default diagnostic library that performs no device writes and captures nothing unless a separate explicit enable flag and an exact, positively identified MPC Pads handle are both present. No install until we have a tested recovery plan and your approval.

Reference source: https://github.com/jacob-sabella/mpc-addin-usb-audio (MIT-licensed reference project).

## Transport-identification decision tree

Do not hard-code RawMIDI as the only possible implementation. The MPC Pads UI port could be backed by ALSA RawMIDI, an ALSA Sequencer port, or an Akai-specific/internal route. The diagnostic's first job is to identify which API the MPC process actually uses for that named port.

- **If MPC opens it with ALSA RawMIDI:** record the exact device-name argument and associate the returned handle with the MPC Pads port. Observe only bytes returned by MPC's own read call.
- **If MPC uses ALSA Sequencer:** investigate the sequencer client/port and receive path instead; a RawMIDI-only interposer would miss it.
- **If neither is used:** stop and investigate the actual Akai routing layer rather than installing a hook aimed at the wrong API.

The RawMIDI API documentation confirms exclusive opens per direction. It also describes timestamped input reads as an optional facility, not a guarantee that MPC uses them. A second reader is therefore not a valid passive probe, and timestamp support cannot be assumed. Reference: ALSA RawMIDI API documentation.

**Important correction to the prototype plan:** the first implementation should not be a broad hook that logs all MIDI traffic. It should be a narrowly scoped, disabled-by-default observer for the specific MPC Pads handle/port, with a hard cap on captured records and a visible bypass/disable path. If the port cannot be identified unambiguously, it must record nothing.


The ALSA RawMIDI API opens a named device through `snd_rawmidi_open()`, and the API documentation says a device is opened exclusively for a given direction: another process generally cannot independently open the same input direction while MPC already owns it. This means a separate diagnostic program that simply tries to open MPC Pads may fail with a busy-device error and is not the right first test.

A passive interposer has a more plausible observation point: record the device-name argument passed when MPC itself calls `snd_rawmidi_open()`, then, only for the matching handle, inspect a copy of bytes returned by MPC's own `snd_rawmidi_read()` call while passing the original buffer, arguments, return value and error behaviour through unchanged. The observer must never consume data by opening a competing reader, read ahead, alter bytes, or delay the MPC read. This remains a design hypothesis until the exact Live III port is confirmed to use ALSA RawMIDI and the hook is validated against the device's loader/runtime.

ALSA also documents optional timestamped RawMIDI reads, but this is a capability of the API and must not be assumed to be enabled or used by MPC. A first diagnostic can capture a monotonic timestamp at the read boundary; precision and scheduling impact must be measured.

## Hook-interaction risk (2026-11-13)

MPC Skipback hooks ALSA raw-MIDI functions including `snd_rawmidi_close`, `snd_rawmidi_open` and `snd_rawmidi_read` to observe controller messages. MPC Remote also hooks `snd_rawmidi_open`, `snd_rawmidi_read` and `poll` for controller-button input. Its catalog entry warns it may not work alongside Skipback because the first add-in to replace a function receives the call; another add-in sees it only if the first forwards the call.

A LOCKSTEP diagnostic that interposes on the same functions could conflict with either add-in unless its hook chain is designed and tested carefully. Do not ask the user to remove existing add-ins without first checking what is installed and explaining the consequences.

Hooks must resolve and call the next implementation exactly once, preserve return values and errors, avoid blocking/allocating/logging synchronously on MPC's MIDI read path, and write bounded diagnostic records from a separate worker or similarly safe mechanism. A read-only observer is still executable code inside MPC and can crash or stall it.

## Build and device-testing constraints

The Open MPC build guide documents a Linux-style shell, Git, Python 3 and Docker; on Windows it specifically describes Ubuntu under WSL 2. The user has chosen not to install Linux, so do not ask them to set up WSL. Open MPC provides a reusable GitHub Actions workflow (`.github/workflows/addin-release.yml`) that runs on `ubuntu-latest`, uses QEMU for ARM/ARM64 builds, packages Gen2/aarch64 output and can upload a ZIP as a run artifact in dry-run mode. This is a suitable remote-build mechanism in principle, not a working LOCKSTEP build. Once source exists, any workflow must be manually triggered, pin the upstream toolchain revision, build only Gen2/aarch64, validate the package and upload an artifact only. No auto-deploy or device installation.

Open MPC's add-in guide describes a Gen2 Live III case where the loader drop-in falls back to `/run` (temporary storage) and must be recreated after reboot. A separate OS 3.10.1 writable `/etc` overlay note is evidenced on a Key 37, not the user's Live III; do not assume it resolves Live III persistence. Any future package must follow the current catalog's supported installer/uninstaller and recovery requirements.

## Immediate engineering sequence

1. Keep internal-pad support as an open research question; do not assume the controller Private port carries performance-pad notes.
2. Investigate the external DIN/USB MIDI input path separately and define exactly how a processed stream could reach a normal MPC track.
3. Build offline MIDI scheduler tests for quantisation, note pairing, chords and repeated same-pitch notes before writing an in-device processing hook.
4. Inspect current upstream hook implementations and decide whether a safe, compatible ALSA interception approach exists.
5. Only then create a minimal disabled-by-default source skeleton and manually triggered, pinned remote dry-run build.
6. No device installation until source review, package validation, recovery procedure and explicit user approval.

## Decision

LOCKSTEP now has two clearly separated feasibility targets: **A)** transparent internal-pad quantisation (a dedicated MPC Pads port is now documented, but OS-level access and safe interception remain unproven); **B)** external MIDI quantisation into an MPC track (documented input route, processing/reinjection still unproven). The external route is a sensible first implementation target if it proves safe. No source code or binary has been created yet.
