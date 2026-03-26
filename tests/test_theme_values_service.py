from types import SimpleNamespace

from app.services.theme_values import (
    normalize_button_style,
    normalize_gradient_direction,
    normalize_gradient_style,
    resolve_effective_theme,
)


def test_theme_values_prefer_custom_over_theme():
    custom = SimpleNamespace(
        BackgroundColour="#111111",
        TextColour="#eeeeee",
        ButtonColour1="#123456",
        ButtonColour2="#654321",
        AccentColour="#222222",
        FontFamily="Lato, sans-serif",
        InputBackgroundColour="#101010",
        DropzoneBackgroundColour="#202020",
        CoverPhotoPath="/custom-banner.jpg",
        ButtonStyle="SOLID",
        ButtonGradientStyle="RADIAL",
        ButtonGradientDirection="45DEG",
        HeadingSize="L",
        CornerRadius="SHARP",
    )
    theme = SimpleNamespace(
        BackgroundColour="#aaaaaa",
        TextColour="#111111",
        ButtonColour1="#ff0000",
        ButtonColour2="#00ff00",
        AccentColour="#bbbbbb",
        FontFamily="Inter",
        InputBackgroundColour="#0b0b0b",
        DropzoneBackgroundColour="#0c0c0c",
        CoverPhotoPath="/theme-banner.jpg",
        ButtonStyle="gradient",
    )

    out = resolve_effective_theme(custom, theme)

    assert out["bg"] == "#111111"
    assert out["btn1"] == "#123456"
    assert out["button_style"] == "solid"
    assert out["button_gradient_style"] == "radial"
    assert out["button_gradient_direction"] == "45deg"
    assert out["heading_size"] == "l"
    assert out["corner_radius"] == "sharp"


def test_theme_values_fall_back_to_theme_and_defaults():
    custom = SimpleNamespace(
        BackgroundColour=None,
        TextColour=None,
        ButtonColour1=None,
        ButtonColour2=None,
        AccentColour=None,
        FontFamily=None,
        InputBackgroundColour=None,
        DropzoneBackgroundColour=None,
        CoverPhotoPath=None,
        ButtonStyle=None,
        ButtonGradientStyle=None,
        ButtonGradientDirection=None,
        HeadingSize=None,
        CornerRadius=None,
    )
    theme = SimpleNamespace(
        BackgroundColour="#fefefe",
        TextColour="#121212",
        ButtonColour1="#112233",
        ButtonColour2="#334455",
        AccentColour="#123123",
        FontFamily="Poppins",
        InputBackgroundColour="#090909",
        DropzoneBackgroundColour="#080808",
        CoverPhotoPath="/theme.jpg",
        ButtonStyle="gradient",
    )

    out = resolve_effective_theme(custom, theme)

    assert out["bg"] == "#fefefe"
    assert out["text"] == "#121212"
    assert out["button_style"] == "gradient"
    assert out["button_gradient_style"] == "linear"
    assert out["button_gradient_direction"] == "90deg"


def test_normalizers_reject_invalid_values():
    assert normalize_button_style("bad") == "gradient"
    assert normalize_gradient_style("zigzag") == "linear"
    assert normalize_gradient_direction("left-right") == "90deg"
