"""The Windows 7 aero.msstyles part table, read from its binary property map."""

from aero_sprites import part, requires_sprites, sprite_dir
from PIL import Image

pytestmark = requires_sprites


def test_active_window_caption_names_an_extracted_image_with_its_state_count_and_sizing_margins():
    caption = part("WINDOW", "CAPTION")

    assert (
        (sprite_dir() / caption.image_file).is_file(),
        caption.image_count > 1,
        all(margin >= 0 for margin in caption.margins),
        sum(caption.margins) > 0,
    ) == (True, True, True, True)


def test_glass_close_button_is_a_four_state_rectangle_inside_the_dwm_atlas():
    close = part("DWMWindow", "BUTTONACTIVECLOSE")
    left, top, right, bottom = close.atlas_rect
    atlas = Image.open(sprite_dir() / close.image_file)

    assert (close.image_count, 0 <= left < right <= atlas.width, 0 <= top < bottom <= atlas.height) == (4, True, True)
