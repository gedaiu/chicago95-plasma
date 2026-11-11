from PIL import ImageFilter
from reference import MASK_COLOUR, differing_pixels

PIXELMATCH_THRESHOLD_FOR_TOLERANCE_12 = 0.05
RAW_BUDGET = 0.05
BLURRED_BUDGET = 0.02


def moving_average(samples):
    return [
        tuple(sum(channel) / len(channel) for channel in zip(*samples[max(0, index - 1) : index + 2], strict=True))
        for index in range(len(samples))
    ]


def mean_colour(image, columns, rows):
    pixels = [image.getpixel((x, y)) for x in columns for y in rows]
    return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))


def vertical_profile(image, columns, rows):
    return moving_average([mean_colour(image, columns, [y]) for y in rows])


def horizontal_profile(image, columns, rows):
    return moving_average([mean_colour(image, [x], rows) for x in columns])


def profile_excess(reference_profile, our_profile):
    return max(
        abs(a - b)
        for reference_sample, our_sample in zip(reference_profile, our_profile, strict=True)
        for a, b in zip(reference_sample, our_sample, strict=True)
    )


def masked(image, masks):
    copy = image.copy()
    for box in masks:
        copy.paste(MASK_COLOUR, box)
    return copy


def blurred(image):
    return image.filter(ImageFilter.BoxBlur(1))


def differing_fraction(reference, ours, masks, diff_path, soften=lambda image: image):
    count = differing_pixels(
        soften(masked(reference, masks)),
        soften(masked(ours, masks)),
        [],
        diff_path,
        PIXELMATCH_THRESHOLD_FOR_TOLERANCE_12,
    )
    return count / (reference.width * reference.height)


def blurred_differing_fraction(reference, ours, masks, diff_path):
    return differing_fraction(reference, ours, masks, diff_path, soften=blurred)
