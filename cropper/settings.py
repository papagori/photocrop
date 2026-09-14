"""Immutable processing options and the ratio-specific output catalog."""
from dataclasses import dataclass


ASPECT_RATIOS = {
    'Original': None,
    '1:1': (1, 1),
    '3:2': (3, 2),
    '4:3': (4, 3),
    '5:4': (5, 4),
    '16:9': (16, 9),
    '2:1': (2, 1),
}


@dataclass(frozen=True)
class OutputPreset:
    key: str
    label: str
    long_edge: int | None = None
    dimensions: tuple[int, int] | None = None


MAXIMUM = OutputPreset('maximum', 'Maximum Resolution — Keep Maximum Pixels')
ORIGINAL = OutputPreset('original', 'Original Resolution')

_STANDARD_DIMENSIONS = {
    '1:1': ((1024, 1024), (2048, 2048), (4096, 4096), (8192, 8192)),
    '3:2': ((2400, 1600), (3000, 2000), (3600, 2400), (4500, 3000),
            (6000, 4000), (7500, 5000)),
    '4:3': ((2400, 1800), (3200, 2400), (4000, 3000), (4800, 3600),
            (6000, 4500), (8000, 6000)),
    '5:4': ((2500, 2000), (3000, 2400), (4000, 3200), (5000, 4000), (6000, 4800)),
    '16:9': ((1920, 1080), (2560, 1440), (3840, 2160), (5120, 2880), (7680, 4320)),
    '2:1': ((2000, 1000), (3000, 1500), (4000, 2000), (5000, 2500),
            (6000, 3000), (8000, 4000)),
}


def _exact_preset(width, height):
    return OutputPreset(f'exact_{width}_{height}', f'{width} × {height}', dimensions=(width, height))


OUTPUT_PRESETS = {
    'Original': (ORIGINAL,) + tuple(
        OutputPreset(f'edge_{edge}', f'{edge} px long edge', long_edge=edge)
        for edge in (2000, 3000, 4000, 5000, 6000, 8000)
    )
}
for _ratio_label, _dimensions in _STANDARD_DIMENSIONS.items():
    OUTPUT_PRESETS[_ratio_label] = (MAXIMUM,) + tuple(_exact_preset(*size) for size in _dimensions)

# Flat views remain useful to non-UI callers. The UI presents only the list
# belonging to the selected ratio.
PRESETS = tuple(dict.fromkeys(preset for choices in OUTPUT_PRESETS.values() for preset in choices))
PRESET_BY_KEY = {preset.key: preset for preset in PRESETS}


def presets_for_ratio(label):
    return OUTPUT_PRESETS[label]


@dataclass(frozen=True)
class ProcessingOptions:
    aspect_ratio: tuple[int, int] | None = (4, 3)
    output: OutputPreset = MAXIMUM
    allow_upscaling: bool = False
    output_format: str = 'JPEG'
    language: str = 'en'

    @property
    def effective_ratio(self):
        return self.aspect_ratio
