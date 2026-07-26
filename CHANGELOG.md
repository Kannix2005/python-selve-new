# Changelog

All notable changes to this project will be documented in this file.

## [2.5.16] - 2026-07-26

### Fixed
- **Every "did it work?" check was broken**: response parameters arrive as raw strings, and `bool("0")` is `True` in Python — so `executed` and friends were always `True`, no matter what the gateway answered (55 call sites across all command modules). They now go through `Util.toBool()`. This also gives 2.5.15's IVEO confirmation gating its teeth: it could previously only detect a timeout, never a gateway that refused to transmit.
- **Responses could be handed to the wrong caller**: futures were matched to responses purely by arrival order, so one late (post-timeout) or dropped response shifted every following assignment by one — devices silently showed other devices' values. Responses are now matched by method name, a timed-out request removes its own future, and an unmatched response is dropped instead of resolving an unrelated one.
- `updateCommeoDeviceValuesFromResponse()` no longer raises on values for an unknown device id (the exception aborted response processing and stranded the waiting caller).
- `discover()` now also resets `txQ` — a command queued just before discovery was injected into the middle of the discovery sequence.
- `SerialTransport.ensure_open()` is guarded by a lock: reader (idle/error reconnect) and writer could open the port twice and leak a handle.
- The device discovery loop no longer turns an unknown position into a definite 0 — the 2.5.15 sentinel handling was missing here.
- `stopDevice()` for IVEO now respects the send confirmation and reports the position as unknown instead of inventing "50%".

### Added
- Everything that rebuilds transport, queues or workers (`setup`, `discover`, `check_port`, keepalive recovery) is serialized by one lock. A reload landing inside a running recovery could otherwise reintroduce exactly the race 2.5.15 fixed.
- Link-state changes are pushed to registered callbacks. `connected` alone was not enough: consumers only re-evaluate on a callback, so a dead gateway never reached Home Assistant unless a device happened to report in. `connected` now also turns `False` once the keepalive declares the link dead (detection takes up to ~90s) and `True` again as soon as data flows.

## [2.5.15] - 2026-07-26

### Fixed
- **Gateway hang no longer freezes everything forever** (the 2026-07-25 incident: 12+ hours of covers stuck in "opening" while commands vanished silently):
  - `startWorker()` health-checked only the TX task. A dead **dispatch task** (the one that processes every gateway response) was never noticed and never restarted — TX kept "working", nothing ever came back. All three workers are checked now.
  - `setup()` replaced `rxQ`/`txQ` while workers were running; a dispatch task still awaiting the old queue instance hung on it forever. Workers are stopped before the queues are swapped.
  - The idle **keepalive ping discarded its result** — even hours of unanswered pings triggered nothing. Three consecutive failures now escalate into a full worker+transport rebuild with fresh queues (and back off while the library is shutting down).
  - Movement polling gave up **silently** after its 60s budget, leaving the optimistic `UP_ON`/`DOWN_ON` standing forever. On timeout it now logs a warning and marks the movement state `UNKOWN`.
- **Phantom 50% positions**: the gateway's `0x8000` "position unknown" sentinel converted to exactly 50 and overwrote correct, newer positions (visible after stops and late poll responses). `Util.valueToPercentage()` returns `None` for the sentinel and consumers keep the last known value.
- **IVEO positions are only claimed when confirmed**: drive commands updated value/targetValue even when the gateway never acknowledged a single transmission (shutter never moved, library said it did). The position now only updates when `_send_iveo_command()` reports a confirmed send.

### Added
- `Selve.connected` property — True while transport and worker pipeline are up (False during recovery), so integrations can bind entity availability to the real gateway state.

## [2.5.14] - 2026-06-17

### Added
- **IVEO reliability**: IVEO is a one-way protocol — the motor never acknowledges, so a single lost RF telegram is a silent failure (shutter stays put while HA shows it moved). Drive commands for IVEO devices now:
  - **repeat the telegram** like a physical handsender (`iveoRepeat`, default 3, spaced by `iveoRepeatDelay`=0.7s; both tunable via `updateOptions()`). The spacing is deliberately wider than the gateway's RF send window — a too-tight repeat overwrites the still-in-progress telegram (gateway logs "IVEO: Command overwritten") and collapses the retries into one burst instead of discrete attempts; verified against hardware that 0.15s overwrites and ≥0.3s is clean,
  - **evaluate the gateway's `executed` acknowledgement** (previously discarded by the fire-and-forget path) and log a warning when the gateway could not transmit, and
  - **guard against the 868 MHz duty cycle**: before each send the worker waits up to 5s for `sendingBlocked` to clear instead of firing into an exhausted duty cycle that the gateway would silently drop. `sendingBlocked`/`utilization` were tracked but never checked before.

  COMMEO drive commands are unchanged — COMMEO has a return channel (`CommandResultResponse` + movement polling) that already surfaces failures.

## [2.5.13] - 2026-06-12

### Added
- **Idle keepalive**: when no data has arrived for 30s, the worker now sends a `ServicePing` to the gateway. The serial reader's 60s idle-reconnect previously tore down a perfectly healthy but quiet link every minute (logging a WARNING each time and silently dropping unsolicited gateway events — e.g. covers moved via physical remote — during the ~1s close/reopen window). With the keepalive the idle-reconnect only fires when the port is actually dead, which is what it was meant for.

## [2.5.12] - 2026-06-12

### Changed
- **Response-paced command transmission**: the TX loop now waits for the previous command's response (with a 5s safety timeout) instead of sleeping a fixed 100ms after every serial write. Command round-trips drop from ~130ms to gateway speed (~30-40ms); full device discovery is roughly 3x faster. Verified against live gateway hardware.
- **Device-aware update callbacks**: `register_callback` callbacks may now accept the changed device as a single positional argument, so consumers can update only the affected entity. Parameterless callbacks keep working unchanged. Callbacks are now fired only when a device actually changed (from `addOrUpdateDevice`), no longer after every gateway response, and a failing callback no longer breaks the dispatch of the remaining ones.
- Hot-path logging now uses lazy `%s` formatting; the malformed-XML-header workaround only runs when the broken header is actually present.

### Fixed
- **Gateway error responses stalled callers for 10s**: a fault reply from the gateway never resolved the pending command future, so `executeCommandSyncWithResponse` always ran into its full 10s timeout (and another 10s on retry). Error responses now resolve the waiting future with `False` immediately.
- `updateAllDevices()` crashed with `AttributeError`: it iterated dict keys (ints) instead of device objects.
- `processTeachResponse` was called without `await`, so teach/scan result processing (including the event callback and event queue delivery) never actually ran.
- Sender events were stored into the sensor device registry (`SelveTypes.SENSOR` instead of `SelveTypes.SENDER`), overwriting sensors that shared the same id.

## [2.5.0] - 2026-02-11

### Added
- **Firmware commands**: `FirmwareGetVersion`, `FirmwareUpdate` with response classes for gateway firmware management.
- **Parameter commands**: `ParamSetDuty`, `ParamSetRf`, `ParamGetTemperature` with response classes for duty cycle, RF configuration, and temperature readout.
- **Command result**: `CommandResult` command class for retrieving pending command results.
- **Enums**: `CommeoFirmwareCommand` enum, `FIRMWARE` entry in `CommandType`, `SETDUTY`/`SETRF`/`GETTEMPERATURE` in `CommeoParamCommand`.
- **Controller methods**: `firmwareGetVersion()`, `firmwareUpdate()`, `setDuty()`, `setRF()`, `getTemperature()`, `deviceSavePos1()`, `deviceSavePos2()`, `commandResult()`, `iveoSetConfig()`, `iveoGetConfig()`.

### Fixed
- **Group name discovery bug**: During `setup(discover=True)`, groups now correctly use `config.groupName` instead of `config.name` (which returned the XML-RPC method name `selve.GW.group.read` instead of the actual group name).
- **`iveoTeach()` / `iveoFactoryReset()`**: Now correctly accept `id` parameter (was missing, causing TypeError).

### Changed
- `GroupReadResponse` attribute renamed from `name` to `groupName` to avoid collision with the inherited `MethodResponse.name` (XML method name).

## [2.4.0] - 2025-01-15

### Added
- senSim device support (simulated sensors)
- Sender teach/write/delete services
- Sensor teach/write/delete services
- Comprehensive device management (scan, save, delete, write manual)
- Group management (read, write, delete, move commands)
- IVEO teach/learn/repeater services
- Gateway parameter services (events, forwarding, LED, duty, RF)

## [2.3.6] - Previous releases

See git history for earlier changes.
