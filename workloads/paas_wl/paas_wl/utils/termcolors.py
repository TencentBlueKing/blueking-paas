# -*- coding: utf-8 -*-
from blue_krill import termcolors
from django.conf import settings


def make_style(*args, **kwargs):
    colorful = termcolors.make_style(*args, **kwargs)

    def dynamic_style(text):
        if settings.COLORFUL_TERMINAL_OUTPUT:
            return colorful(text)
        return termcolors.no_color(text)

    return dynamic_style


class Style:
    """
    Valid colors:
        ANSI Color: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        XTerm Color: [0-256]
        Hex Color: #000000 ~ #FFFFFF

    see also: https://en.wikipedia.org/wiki/X11_color_names#Clashes_between_web_and_X11_colors_in_the_CSS_color_scheme

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal', 'noreset'
    """

    Title = make_style(fg='#c4c6cc', opts=('bold',))
    Error = make_style(fg='#e82f2f', opts=('bold',))
    Warning = make_style(fg='#ff9c01', opts=('bold',))
    Comment = make_style(fg='#3a84ff', opts=('bold',))
    NoColor = termcolors.no_color

    Black = make_style(fg='black', opts=('bold',))
    Red = make_style(fg='red', opts=('bold',))
    Green = make_style(fg='green', opts=('bold',))
    Yellow = make_style(fg='yellow', opts=('bold',))
    Blue = make_style(fg='blue', opts=('bold',))
    Magenta = make_style(fg='magenta', opts=('bold',))
    Cyan = make_style(fg='cyan', opts=('bold',))
    White = make_style(fg='white', opts=('bold',))
