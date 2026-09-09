"""Immutable processing options and shared UI preset catalog."""
from dataclasses import dataclass
from math import gcd

ASPECT_RATIOS = {
    'Original / No Crop': None, '1:1': (1, 1), '4:3': (4, 3),
    '3:2': (3, 2), '5:4': (5, 4), '16:9': (16, 9),
    '16:10': (16, 10), '21:9': (21, 9),
}


@dataclass(frozen=True)
class OutputPreset:
    key: str
    label: str
    group: str = ''
    long_edge: int | None = None
    dimensions: tuple[int, int] | None = None
    aspect_label: str | None = None
    approximate: bool = False

    @property
    def ratio(self):
        if self.dimensions is None:
            return None
        a, b = self.dimensions
        divisor = gcd(a, b)
        return a // divisor, b // divisor


ORIGINAL = OutputPreset('original', 'Original Resolution')
PRESETS = [ORIGINAL]
PRESETS += [OutputPreset(f'edge_{k * 1024}', f'{k}K / {k * 1024} px long edge',
                        'Long Edge', long_edge=k * 1024) for k in (1, 2, 3, 4, 5, 6, 8)]
for width, height, aspect, approx in (
    (1200, 800, '3:2', False), (1500, 1000, '3:2', False),
    (2048, 1365, '2048:1365 (approx. 3:2)', True), (2400, 1600, '3:2', False),
    (3000, 2000, '3:2', False), (4000, 3000, '4:3', False),
    (4500, 3000, '3:2', False), (5000, 3333, '5000:3333 (approx. 3:2)', True),
    (6000, 4000, '3:2', False), (6000, 4500, '4:3', False),
):
    PRESETS.append(OutputPreset(f'exact_{width}_{height}',
        f'{width} × {height} px / {"approx. 3:2" if approx else aspect}', 'Photo Presets',
        dimensions=(width, height), aspect_label=aspect, approximate=approx))
for width, height in ((1920, 1080), (2560, 1440), (3840, 2160), (7680, 4320)):
    PRESETS.append(OutputPreset(f'exact_{width}_{height}',
        f'{width} × {height} px / 16:9' + (' / UHD 8K' if width == 7680 else ''),
        'Video / Screen Presets', dimensions=(width, height), aspect_label='16:9'))
PRESET_BY_KEY = {preset.key: preset for preset in PRESETS}


@dataclass(frozen=True)
class ProcessingOptions:
    aspect_ratio: tuple[int, int] | None = (4, 3)
    output: OutputPreset = ORIGINAL
    allow_upscaling: bool = False

    @property
    def effective_ratio(self):
        return self.output.ratio if self.output.dimensions else self.aspect_ratio
