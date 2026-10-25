"""`pythonx.compose.material3` -- the Pythonic view of `androidx.compose.material3`.

Every Material 3 composable (`Text`, `Button`, `Card`, `TextField`, `Checkbox`, ...) is served by
the one rule in `pythonx/compose/_reexport.py`: Kotlin's own declaration, upper-case names kept,
keyword arguments in snake_case (`on_click=`). There is no per-widget file here, on purpose
(AGENTS.md section 13). The notebook's `Column`, `Row` and `Spacer` are answered from
`pythonx.compose.layout` by the manifest's `[aliases]` (INTENT section 5.2).

## `light_color_scheme` and `dark_color_scheme`

Compose's `lightColorScheme` and `darkColorScheme` each have 48 `Color` parameters with defaults,
including `surfaceTint: Color = primary`, whose default refers to the `primary` parameter. The
binder caps default-mask bitmasks at 6 omittable parameters (`MAX_OMITTABLE_PARAMETERS = 6`,
python-multiplatform #309) and cannot express an inter-parameter default in a flat bitmask, so the
walker binds `lightColorScheme` and `darkColorScheme` with all 48 parameters required and binds
`ColorScheme`'s 48-argument primary constructor (`SPEC.md` S5.3, issue #135).

`light_color_scheme` and `dark_color_scheme` are defined here in Python: they accept all 48
snake_case parameters (`primary`, `on_primary`, ...) with `None` meaning the Material 3 token
default (`ColorLightTokens` / `ColorDarkTokens`, `PaletteTokens`), resolve `surface_tint` to the
resolved `primary` when `surface_tint` is `None`, and call `androidx.compose.material3.ColorScheme`
with the 48 `Color` values in constructor order (`surfaceDim` is slot 30 of `ColorScheme` and slot
35 of `lightColorScheme` / `darkColorScheme`).

## What used to be here

Per-widget wrappers from 2024 (`text.py`, `buttons.py`, `cards.py`, `icon_button.py`,
`text_field.py`, ...), each a copy of one template that looked a Kotlin function up by a
mangled-name prefix (`name.startswith("Button-")`), which Kotlin's value-class mangling makes
impossible. They were deleted as the binder rendered each declaration with no wrapper
(python-multiplatform `c60bcfeb`, `a6742a1c`, `3fde8bd6`, `cac8243f`). `icon.py` and
`color_scheme.py` were kept as records of two declarations that cannot be called yet, and 29
sibling files had always been empty; all were deleted in pythonx-compose #31. What `icon.py`
recorded -- `Icon` needs an `ImageVector` nothing bound produces -- is SPEC S5.3. `git log` on this
directory has the rest.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from pythonx.compose._reexport import reexport


class _KotlinColorScheme(Protocol):
    """Opaque protocol for the `ColorScheme` proxy the binder returns."""


if TYPE_CHECKING:
    # For the checker only: at run time `ColorScheme` is Kotlin's class, read through `__getattr__`,
    # and the stub declares `class ColorScheme` from the Kotlin-named stub.
    ColorScheme = _KotlinColorScheme


# Constructor slot order of `androidx.compose.material3.ColorScheme` (48 `Color` parameters).
# `surface_tint` (index 19) is `None` here and defaults to the resolved `primary` (index 0).
# Material 3 token values from `ColorLightTokens`, `ColorDarkTokens` and `PaletteTokens`
# (`org.thisisthepy.compose.material3:material3:1.11.1-ext.2`).
_LIGHT_DEFAULTS: tuple[int | None, ...] = (
    0xFF6750A4,  # primary (Primary40)
    0xFFFFFFFF,  # on_primary (Primary100)
    0xFFEADDFF,  # primary_container (Primary90)
    0xFF21005D,  # on_primary_container (Primary10)
    0xFFD0BCFF,  # inverse_primary (Primary80)
    0xFF625B71,  # secondary (Secondary40)
    0xFFFFFFFF,  # on_secondary (Secondary100)
    0xFFE8DEF8,  # secondary_container (Secondary90)
    0xFF1D192B,  # on_secondary_container (Secondary10)
    0xFF7D5260,  # tertiary (Tertiary40)
    0xFFFFFFFF,  # on_tertiary (Tertiary100)
    0xFFFFD8E4,  # tertiary_container (Tertiary90)
    0xFF31111D,  # on_tertiary_container (Tertiary10)
    0xFFFEF7FF,  # background (Neutral98)
    0xFF1D1B20,  # on_background (Neutral10)
    0xFFFEF7FF,  # surface (Neutral98)
    0xFF1D1B20,  # on_surface (Neutral10)
    0xFFE7E0EC,  # surface_variant (NeutralVariant90)
    0xFF49454F,  # on_surface_variant (NeutralVariant30)
    None,        # surface_tint (defaults to primary)
    0xFF322F35,  # inverse_surface (Neutral20)
    0xFFF5EFF7,  # inverse_on_surface (Neutral95)
    0xFFB3261E,  # error (Error40)
    0xFFFFFFFF,  # on_error (Error100)
    0xFFF9DEDC,  # error_container (Error90)
    0xFF410E0B,  # on_error_container (Error10)
    0xFF79747E,  # outline (NeutralVariant50)
    0xFFCAC4D0,  # outline_variant (NeutralVariant80)
    0xFF000000,  # scrim (Neutral0)
    0xFFFEF7FF,  # surface_bright (Neutral98)
    0xFFDED8E1,  # surface_dim (Neutral87)
    0xFFF3EDF7,  # surface_container (Neutral94)
    0xFFECE6F0,  # surface_container_high (Neutral92)
    0xFFE6E0E9,  # surface_container_highest (Neutral90)
    0xFFF7F2FA,  # surface_container_low (Neutral96)
    0xFFFFFFFF,  # surface_container_lowest (Neutral100)
    0xFFEADDFF,  # primary_fixed (Primary90)
    0xFFD0BCFF,  # primary_fixed_dim (Primary80)
    0xFF21005D,  # on_primary_fixed (Primary10)
    0xFF4F378B,  # on_primary_fixed_variant (Primary30)
    0xFFE8DEF8,  # secondary_fixed (Secondary90)
    0xFFCCC2DC,  # secondary_fixed_dim (Secondary80)
    0xFF1D192B,  # on_secondary_fixed (Secondary10)
    0xFF4A4458,  # on_secondary_fixed_variant (Secondary30)
    0xFFFFD8E4,  # tertiary_fixed (Tertiary90)
    0xFFEFB8C8,  # tertiary_fixed_dim (Tertiary80)
    0xFF31111D,  # on_tertiary_fixed (Tertiary10)
    0xFF633B48,  # on_tertiary_fixed_variant (Tertiary30)
)

_DARK_DEFAULTS: tuple[int | None, ...] = (
    0xFFD0BCFF,  # primary (Primary80)
    0xFF381E72,  # on_primary (Primary20)
    0xFF4F378B,  # primary_container (Primary30)
    0xFFEADDFF,  # on_primary_container (Primary90)
    0xFF6750A4,  # inverse_primary (Primary40)
    0xFFCCC2DC,  # secondary (Secondary80)
    0xFF332D41,  # on_secondary (Secondary20)
    0xFF4A4458,  # secondary_container (Secondary30)
    0xFFE8DEF8,  # on_secondary_container (Secondary90)
    0xFFEFB8C8,  # tertiary (Tertiary80)
    0xFF492532,  # on_tertiary (Tertiary20)
    0xFF633B48,  # tertiary_container (Tertiary30)
    0xFFFFD8E4,  # on_tertiary_container (Tertiary90)
    0xFF141218,  # background (Neutral6)
    0xFFE6E0E9,  # on_background (Neutral90)
    0xFF141218,  # surface (Neutral6)
    0xFFE6E0E9,  # on_surface (Neutral90)
    0xFF49454F,  # surface_variant (NeutralVariant30)
    0xFFCAC4D0,  # on_surface_variant (NeutralVariant80)
    None,        # surface_tint (defaults to primary)
    0xFFE6E0E9,  # inverse_surface (Neutral90)
    0xFF322F35,  # inverse_on_surface (Neutral20)
    0xFFF2B8B5,  # error (Error80)
    0xFF601410,  # on_error (Error20)
    0xFF8C1D18,  # error_container (Error30)
    0xFFF9DEDC,  # on_error_container (Error90)
    0xFF938F99,  # outline (NeutralVariant60)
    0xFF49454F,  # outline_variant (NeutralVariant30)
    0xFF000000,  # scrim (Neutral0)
    0xFF3B383E,  # surface_bright (Neutral24)
    0xFF141218,  # surface_dim (Neutral6)
    0xFF211F26,  # surface_container (Neutral12)
    0xFF2B2930,  # surface_container_high (Neutral17)
    0xFF36343B,  # surface_container_highest (Neutral22)
    0xFF1D1B20,  # surface_container_low (Neutral10)
    0xFF0F0D13,  # surface_container_lowest (Neutral4)
    0xFFEADDFF,  # primary_fixed (Primary90)
    0xFFD0BCFF,  # primary_fixed_dim (Primary80)
    0xFF21005D,  # on_primary_fixed (Primary10)
    0xFF4F378B,  # on_primary_fixed_variant (Primary30)
    0xFFE8DEF8,  # secondary_fixed (Secondary90)
    0xFFCCC2DC,  # secondary_fixed_dim (Secondary80)
    0xFF1D192B,  # on_secondary_fixed (Secondary10)
    0xFF4A4458,  # on_secondary_fixed_variant (Secondary30)
    0xFFFFD8E4,  # tertiary_fixed (Tertiary90)
    0xFFEFB8C8,  # tertiary_fixed_dim (Tertiary80)
    0xFF31111D,  # on_tertiary_fixed (Tertiary10)
    0xFF633B48,  # on_tertiary_fixed_variant (Tertiary30)
)


def _build_color_scheme(
    values: tuple[object | None, ...],
    defaults: tuple[int | None, ...],
) -> ColorScheme:
    """Resolve `None` slots from `defaults` (`surface_tint` from `primary`) and call `ColorScheme`."""
    make_color = cast(
        "Callable[[int], object]",
        importlib.import_module("pythonx.compose.ui.graphics").Color,
    )
    make_scheme = cast(
        "Callable[..., ColorScheme]",
        importlib.import_module("androidx.compose.material3").ColorScheme,
    )
    resolved: list[object] = []
    for index, (value, default_argb) in enumerate(zip(values, defaults)):
        if value is not None:
            resolved.append(value)
        elif index == 19:
            # `surfaceTint: Color = primary` in Compose's `lightColorScheme` / `darkColorScheme`.
            resolved.append(resolved[0])
        else:
            assert default_argb is not None
            resolved.append(make_color(default_argb))
    return make_scheme(*resolved)


def light_color_scheme(
    primary: object | None = None,
    on_primary: object | None = None,
    primary_container: object | None = None,
    on_primary_container: object | None = None,
    inverse_primary: object | None = None,
    secondary: object | None = None,
    on_secondary: object | None = None,
    secondary_container: object | None = None,
    on_secondary_container: object | None = None,
    tertiary: object | None = None,
    on_tertiary: object | None = None,
    tertiary_container: object | None = None,
    on_tertiary_container: object | None = None,
    background: object | None = None,
    on_background: object | None = None,
    surface: object | None = None,
    on_surface: object | None = None,
    surface_variant: object | None = None,
    on_surface_variant: object | None = None,
    surface_tint: object | None = None,
    inverse_surface: object | None = None,
    inverse_on_surface: object | None = None,
    error: object | None = None,
    on_error: object | None = None,
    error_container: object | None = None,
    on_error_container: object | None = None,
    outline: object | None = None,
    outline_variant: object | None = None,
    scrim: object | None = None,
    surface_bright: object | None = None,
    surface_container: object | None = None,
    surface_container_high: object | None = None,
    surface_container_highest: object | None = None,
    surface_container_low: object | None = None,
    surface_container_lowest: object | None = None,
    surface_dim: object | None = None,
    primary_fixed: object | None = None,
    primary_fixed_dim: object | None = None,
    on_primary_fixed: object | None = None,
    on_primary_fixed_variant: object | None = None,
    secondary_fixed: object | None = None,
    secondary_fixed_dim: object | None = None,
    on_secondary_fixed: object | None = None,
    on_secondary_fixed_variant: object | None = None,
    tertiary_fixed: object | None = None,
    tertiary_fixed_dim: object | None = None,
    on_tertiary_fixed: object | None = None,
    on_tertiary_fixed_variant: object | None = None,
) -> ColorScheme:
    """Material 3 light `ColorScheme`, with `ColorLightTokens` defaults and `surface_tint = primary`."""
    return _build_color_scheme(
        (
            primary, on_primary, primary_container, on_primary_container, inverse_primary,
            secondary, on_secondary, secondary_container, on_secondary_container,
            tertiary, on_tertiary, tertiary_container, on_tertiary_container,
            background, on_background, surface, on_surface, surface_variant, on_surface_variant,
            surface_tint, inverse_surface, inverse_on_surface,
            error, on_error, error_container, on_error_container,
            outline, outline_variant, scrim,
            surface_bright, surface_dim, surface_container, surface_container_high,
            surface_container_highest, surface_container_low, surface_container_lowest,
            primary_fixed, primary_fixed_dim, on_primary_fixed, on_primary_fixed_variant,
            secondary_fixed, secondary_fixed_dim, on_secondary_fixed, on_secondary_fixed_variant,
            tertiary_fixed, tertiary_fixed_dim, on_tertiary_fixed, on_tertiary_fixed_variant,
        ),
        _LIGHT_DEFAULTS,
    )


def dark_color_scheme(
    primary: object | None = None,
    on_primary: object | None = None,
    primary_container: object | None = None,
    on_primary_container: object | None = None,
    inverse_primary: object | None = None,
    secondary: object | None = None,
    on_secondary: object | None = None,
    secondary_container: object | None = None,
    on_secondary_container: object | None = None,
    tertiary: object | None = None,
    on_tertiary: object | None = None,
    tertiary_container: object | None = None,
    on_tertiary_container: object | None = None,
    background: object | None = None,
    on_background: object | None = None,
    surface: object | None = None,
    on_surface: object | None = None,
    surface_variant: object | None = None,
    on_surface_variant: object | None = None,
    surface_tint: object | None = None,
    inverse_surface: object | None = None,
    inverse_on_surface: object | None = None,
    error: object | None = None,
    on_error: object | None = None,
    error_container: object | None = None,
    on_error_container: object | None = None,
    outline: object | None = None,
    outline_variant: object | None = None,
    scrim: object | None = None,
    surface_bright: object | None = None,
    surface_container: object | None = None,
    surface_container_high: object | None = None,
    surface_container_highest: object | None = None,
    surface_container_low: object | None = None,
    surface_container_lowest: object | None = None,
    surface_dim: object | None = None,
    primary_fixed: object | None = None,
    primary_fixed_dim: object | None = None,
    on_primary_fixed: object | None = None,
    on_primary_fixed_variant: object | None = None,
    secondary_fixed: object | None = None,
    secondary_fixed_dim: object | None = None,
    on_secondary_fixed: object | None = None,
    on_secondary_fixed_variant: object | None = None,
    tertiary_fixed: object | None = None,
    tertiary_fixed_dim: object | None = None,
    on_tertiary_fixed: object | None = None,
    on_tertiary_fixed_variant: object | None = None,
) -> ColorScheme:
    """Material 3 dark `ColorScheme`, with `ColorDarkTokens` defaults and `surface_tint = primary`."""
    return _build_color_scheme(
        (
            primary, on_primary, primary_container, on_primary_container, inverse_primary,
            secondary, on_secondary, secondary_container, on_secondary_container,
            tertiary, on_tertiary, tertiary_container, on_tertiary_container,
            background, on_background, surface, on_surface, surface_variant, on_surface_variant,
            surface_tint, inverse_surface, inverse_on_surface,
            error, on_error, error_container, on_error_container,
            outline, outline_variant, scrim,
            surface_bright, surface_dim, surface_container, surface_container_high,
            surface_container_highest, surface_container_low, surface_container_lowest,
            primary_fixed, primary_fixed_dim, on_primary_fixed, on_primary_fixed_variant,
            secondary_fixed, secondary_fixed_dim, on_secondary_fixed, on_secondary_fixed_variant,
            tertiary_fixed, tertiary_fixed_dim, on_tertiary_fixed, on_tertiary_fixed_variant,
        ),
        _DARK_DEFAULTS,
    )


__getattr__, __dir__ = reexport(__name__)
