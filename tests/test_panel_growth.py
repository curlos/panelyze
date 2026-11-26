from magi import get_grown_panels

# Two 100x100 panels, one above the other, with a 10 px gutter.
TOP_PANEL = [0, 0, 100, 100]
BOTTOM_PANEL = [0, 110, 100, 210]


def test_a_speech_bubble_sticking_out_of_its_panel_is_kept_whole():
    # Mostly in the top panel, sticking 15 px out to the right.
    bubble = [70, 20, 115, 40]

    grown = get_grown_panels([TOP_PANEL, BOTTOM_PANEL], [bubble], [])

    # The panel grows to fit it, plus a margin for the bubble's outline.
    assert grown == [[0, 0, 127, 100], BOTTOM_PANEL]


def test_text_that_would_pull_in_most_of_another_panel_is_left_out():
    # Like a Japanese caption in the margin: it touches the top panel but runs down past the bottom one.
    caption = [95, 50, 110, 210]

    grown = get_grown_panels([TOP_PANEL, BOTTOM_PANEL], [caption], [])

    assert grown == [TOP_PANEL, BOTTOM_PANEL]


def test_a_character_sticking_out_is_kept_whole_if_it_takes_little_of_another_panel():
    # Mostly in the top panel, reaching 20 px into the bottom one (20% of it).
    character = [20, 10, 80, 130]

    grown = get_grown_panels([TOP_PANEL, BOTTOM_PANEL], [], [character])

    assert grown == [[0, 0, 100, 130], BOTTOM_PANEL]


def test_a_character_that_would_take_too_much_of_another_panel_is_left_out():
    # Reaching 50 px into the bottom panel (50% of it).
    character = [20, 10, 80, 160]

    assert get_grown_panels([TOP_PANEL, BOTTOM_PANEL], [], [character]) == [
        TOP_PANEL,
        BOTTOM_PANEL,
    ]


def test_show_full_characters_always_fits_the_whole_character():
    character = [20, 10, 80, 160]

    grown = get_grown_panels(
        [TOP_PANEL, BOTTOM_PANEL], [], [character], character_growth_limit=None
    )

    assert grown == [[0, 0, 100, 160], BOTTOM_PANEL]


def test_text_and_characters_inside_their_panel_change_nothing():
    grown = get_grown_panels(
        [TOP_PANEL, BOTTOM_PANEL], [[10, 10, 50, 30]], [[10, 120, 60, 200]]
    )

    assert grown == [TOP_PANEL, BOTTOM_PANEL]


def test_a_speech_bubble_split_between_two_panels_is_shown_whole_in_one_of_them():
    left_panel, right_panel = [0, 0, 100, 200], [110, 0, 210, 200]
    # Half in each panel. Fitting it into either one takes about half of the other, more than the limit.
    bubble = [60, 50, 150, 150]

    grown = get_grown_panels([left_panel, right_panel], [bubble], [])

    # The reader needs the words, so one panel shows it whole anyway.
    assert grown == [[0, 0, 162, 200], right_panel]


def test_a_speech_bubble_its_own_panel_cant_fit_goes_to_the_other_panel_it_is_in():
    # A narrow panel on the left and a wide one on the right.
    narrow_panel, wide_panel = [0, 0, 60, 200], [70, 0, 400, 200]
    # Mostly in the wide panel, but fitting it there would take most of the narrow one.
    bubble = [20, 50, 120, 150]

    grown = get_grown_panels([narrow_panel, wide_panel], [bubble], [])

    # The narrow panel grows a little into the wide one instead.
    assert grown == [[0, 0, 132, 200], wide_panel]


def test_a_title_running_down_several_panels_is_left_out():
    panels = [[0, 0, 100, 100], [0, 110, 100, 210], [0, 220, 100, 320]]
    # Like a chapter title printed down the side of the page, over the edge of 3 panels.
    title = [80, 10, 110, 310]

    assert get_grown_panels(panels, [title], []) == panels


def test_a_split_speech_bubble_goes_to_the_first_panel_in_reading_order():
    # Manga order: the wide panel on the right is read first, then the narrow one on the left.
    wide_first_panel, narrow_second_panel = [70, 0, 400, 200], [0, 0, 60, 200]
    # Mostly in the first panel. Fitting it there takes most of the second, but the reader reaches it there first.
    bubble = [20, 50, 120, 150]

    grown = get_grown_panels([wide_first_panel, narrow_second_panel], [bubble], [])

    assert grown == [[8, 0, 400, 200], narrow_second_panel]


def test_a_split_speech_bubble_follows_the_reading_direction():
    left_panel, right_panel = [0, 0, 100, 200], [110, 0, 210, 200]
    # Half in each panel. Panels come in manga order: the right one first.
    bubble = [60, 50, 150, 150]
    manga_order = [right_panel, left_panel]

    # Manga: the right panel is read first, so it shows the bubble.
    assert get_grown_panels(manga_order, [bubble], [], reading_direction="rtl") == [
        [48, 0, 210, 200],
        left_panel,
    ]
    # Comics: the left panel is read first.
    assert get_grown_panels(manga_order, [bubble], [], reading_direction="ltr") == [
        right_panel,
        [0, 0, 162, 200],
    ]
