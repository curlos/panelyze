import numpy


def drawn_page(height=100, width=100):
    """
    A fake page with lines drawn all over it (black and white stripes), so its panels aren't left out as blank or as having nothing new.
    """
    row = ((numpy.arange(width) // 4) % 2 * 255).astype(numpy.uint8)
    return numpy.repeat(numpy.tile(row, (height, 1))[:, :, None], 3, axis=2)
