"""Channel name mapping and parsing utilities."""

from typing import Optional


# Channel name mapping
CHANNEL_NAMES = {
    0: "General/Public",
    1: "Channel 1",
    2: "Channel 2",
    3: "Channel 3",
    4: "Channel 4",
    5: "Channel 5",
    6: "Channel 6",
    7: "Channel 7"
}

CHANNEL_NAME_MAP = {
    "general": 0,
    "public": 0,
    "main": 0,
    "default": 0
}


def parse_channel_input(channel_input: Optional[str | int]) -> tuple[Optional[int], Optional[str]]:
    """
    Parse channel input which can be either a channel number (int) or a channel name (str).

    Args:
        channel_input: Channel number (0-7) or common name like "general", "public", "main"

    Returns:
        Tuple of (channel_number, error_message). If error_message is not None, channel_number will be None.

    Examples:
        - parse_channel_input(0) -> (0, None)
        - parse_channel_input("general") -> (0, None)
        - parse_channel_input("public") -> (0, None)
        - parse_channel_input(5) -> (5, None)
        - parse_channel_input("invalid") -> (None, "Error: Unknown channel name...")
    """
    if channel_input is None:
        return (None, None)

    # If it's already an integer, validate it
    if isinstance(channel_input, int):
        if 0 <= channel_input <= 7:
            return (channel_input, None)
        else:
            return (None, f"Error: Channel number must be between 0 and 7, got {channel_input}")

    # If it's a string, try to parse it
    if isinstance(channel_input, str):
        # Try to parse as integer first
        try:
            channel_num = int(channel_input)
            if 0 <= channel_num <= 7:
                return (channel_num, None)
            else:
                return (None, f"Error: Channel number must be between 0 and 7, got {channel_num}")
        except ValueError:
            # Not a number, try to map from name
            channel_name_lower = channel_input.lower().strip()
            if channel_name_lower in CHANNEL_NAME_MAP:
                return (CHANNEL_NAME_MAP[channel_name_lower], None)
            else:
                available_names = ", ".join(f"'{name}'" for name in sorted(CHANNEL_NAME_MAP.keys()))
                return (None, f"Error: Unknown channel name '{channel_input}'. Use {available_names} or channel number 0-7")

    return (None, f"Error: Invalid channel input type: {type(channel_input)}")


def get_channel_display_name(channel_num: int) -> str:
    """
    Get a friendly display name for a channel number.

    Args:
        channel_num: Channel number (0-7)

    Returns:
        Friendly name like "0 (General/Public)" or "5 (Channel 5)"
    """
    if channel_num in CHANNEL_NAMES:
        return f"{channel_num} ({CHANNEL_NAMES[channel_num]})"
    return str(channel_num)
