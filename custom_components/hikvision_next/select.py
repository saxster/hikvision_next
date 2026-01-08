"""Platform for PTZ preset select entity."""

from __future__ import annotations

from homeassistant.components.select import ENTITY_ID_FORMAT, SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from . import HikvisionConfigEntry
from .isapi import AnalogCamera, IPCamera


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HikvisionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add PTZ preset select entities from a config entry."""

    device = entry.runtime_data

    entities = []

    # PTZ preset select for each camera with PTZ support
    for camera in device.cameras:
        if camera.ptz_info.is_supported and camera.ptz_info.presets:
            entities.append(PTZPresetSelect(device, camera))

    async_add_entities(entities)


class PTZPresetSelect(SelectEntity):
    """PTZ Preset select entity."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:camera-marker"
    _attr_translation_key = "ptz_preset"

    def __init__(self, device, camera: IPCamera | AnalogCamera) -> None:
        """Initialize."""
        self._device = device
        self._camera = camera
        self._attr_unique_id = f"{slugify(camera.serial_no.lower())}_ptz_preset"
        self.entity_id = ENTITY_ID_FORMAT.format(self._attr_unique_id)
        self._attr_device_info = device.hass_device_info(camera.id)
        self._current_option: str | None = None

        # Build options from presets
        self._preset_map: dict[str, int] = {}
        options = []
        for preset in camera.ptz_info.presets:
            option_name = f"{preset.id}: {preset.name}"
            options.append(option_name)
            self._preset_map[option_name] = preset.id
        self._attr_options = options

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        preset_id = self._preset_map.get(option)
        if preset_id is not None:
            await self._device.goto_ptz_preset(self._camera.id, preset_id)
            self._current_option = option
            self.async_write_ha_state()
