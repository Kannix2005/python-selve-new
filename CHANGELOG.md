# Changelog

All notable changes to this project will be documented in this file.

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
