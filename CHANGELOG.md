# Changelog

All notable changes to this project will be documented in this file.

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
