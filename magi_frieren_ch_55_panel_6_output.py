magi_frieren_ch_55_panel_6_output = [
    {
        "panels": [
            [
                2.5027098655700684,
                -0.44720542430877686,
                2955.693359375,
                2290.646728515625,
            ]
        ],
        "texts": [
            [
                1953.446533203125,
                374.7942199707031,
                2913.07958984375,
                1020.8543701171875,
            ],
            [333.09423828125, 558.58544921875, 888.7525634765625, 992.339599609375],
            [274.2110900878906, 1230.124755859375, 770.1596069335938, 2074.41455078125],
        ],
        "characters": [
            [
                846.8881225585938,
                104.71615600585938,
                1860.202880859375,
                2302.469970703125,
            ]
        ],
        "tails": [
            [914.5801391601562, 617.2416381835938, 1090.65380859375, 757.5996704101562],
            [1681.2462158203125, 551.6893920898438, 1845.33740234375, 675.193115234375],
        ],
        """
        "text_character_associations" is pretty much the same thing as "text_tail_associations" but it uses the "characters" array instead of the tails array.
        - [0, 0] = texts[0] is associated with characters[0]
        - [1, 0] = texts[1] is associated with characters[0]
        - [2, 0] = texts[2] is associated with characters[0]
        - So, for this panel, it's one character (characters[0]) associated with all of the text. This makes sense as Methode, the name of the character in this panel, is the only one talking.

        Other Notes:
        - I'll have to run some more tests but from a quick test, it doesn't seem like Magi is currently associating characters from previous panels/images. So, if you have a panel where Goku is talking to Vegeta, then Goku is associated with ID = 0 and Vegeta is associated with ID = 1 but only for that page. So, if you go to a second page where Goku is instead talking to Piccolo, then Goku will be ID = 0 but Piccolo could in theory be ID = 1 so now 2 characters have had ID = 1 (Vegeta, Piccolo). So, this might make it difficult, if not impossible to associate characters with unique IDs and use unique TTS voices.
        - However, it still might be possible if I train Magi using an array of passed in images so all hope is not lost yet.
        """
        "text_character_associations": [[0, 0], [1, 0], [2, 0]],
        # "text_tail_associations" is seemingly associating the different pieces of text from the "ocr" property to the "tails" in the speech bubbles. It looks like it's going in the order of text-index first and then tail-index.
        # - [0, 1] means that texts[0] is associated with tails[1].
        # - [1, 0] and [2, 0] means that texts[1] and texts[2] are both part of the same tail, tails[0].
        # - Also, for some reason, it appears that tails are stored from left to right whereas text is stored from right-to-left so keep that in mind. This is not an issue for the text but rather that if you have text[0], it probably won't always be associated with the first index but rather the last index because tails are stored in the opposite direction: left-to-right. This is just a theory though from this one image. Will need to investigate with a larger sample size.
        "text_tail_associations": [[0, 1], [1, 0], [2, 0]],
        "character_cluster_labels": [0],
        "is_essential_text": [True, True, True],
        "ocr": [
            "A battle between images is akin to a rock- paper-scissors match, after all.",
            "Albert a rock-paper- scissors match",
            "that is extremely complex, difficult to read and involves a myriad of moves.",
        ],
        "character_names": ["Other"],
    }
]
