"""Offer device oriented automation."""
from __future__ import annotations

from typing import Any, Protocol, cast

import voluptuous as vol

from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from . import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    DeviceAutomationType,
    async_get_device_automation_platform,
)
from .exceptions import InvalidDeviceAutomationConfig

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({}, extra=vol.ALLOW_EXTRA)


class DeviceAutomationTriggerProtocol(Protocol):
    """Define the format of device_trigger modules.

    Each module must define either TRIGGER_SCHEMA or async_validate_trigger_config.
    """

    TRIGGER_SCHEMA: vol.Schema

    async def async_validate_trigger_config(
        self, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate config."""

    async def async_attach_trigger(
        self,
        hass: HomeAssistant,
        config: ConfigType,
        action: TriggerActionType,
        trigger_info: TriggerInfo,
    ) -> CALLBACK_TYPE:
        """Attach a trigger."""

    async def async_get_trigger_capabilities(
        self, hass: HomeAssistant, config: ConfigType
    ) -> dict[str, vol.Schema]:
        """List trigger capabilities."""

    async def async_get_triggers(
        self, hass: HomeAssistant, device_id: str
    ) -> list[dict[str, Any]]:
        """List triggers."""


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config."""
    try:
        platform = await async_get_device_automation_platform(
            hass, config[CONF_DOMAIN], DeviceAutomationType.TRIGGER
        )
        if not hasattr(platform, "async_validate_trigger_config"):
            return cast(ConfigType, platform.TRIGGER_SCHEMA(config))

        # Only call the dynamic validator if the relevant config entry is loaded
        registry = dr.async_get(hass)
        if not (device := registry.async_get(config[CONF_DEVICE_ID])):
            raise InvalidDeviceAutomationConfig

        device_config_entry = None
        for entry_id in device.config_entries:
            if not (entry := hass.config_entries.async_get_entry(entry_id)):
                continue
            if entry.domain != config[CONF_DOMAIN]:
                continue
            device_config_entry = entry
            break

        if not device_config_entry:
            raise InvalidDeviceAutomationConfig

        if not await hass.config_entries.async_wait_component(device_config_entry):
            return config

        return await platform.async_validate_trigger_config(hass, config)
    except InvalidDeviceAutomationConfig as err:
        raise vol.Invalid(str(err) or "Invalid trigger configuration") from err


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for trigger."""
    platform = await async_get_device_automation_platform(
        hass, config[CONF_DOMAIN], DeviceAutomationType.TRIGGER
    )
    return await platform.async_attach_trigger(hass, config, action, trigger_info)
