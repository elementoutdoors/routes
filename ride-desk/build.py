"""Builds the Ride Desk page (ride-desk/ride-desk.html) from its parts in ride-desk/page.

The Ride Desk is a claude.ai artifact: https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18. This folder is its source.
To change the page: edit the parts, run `python3 ride-desk/build.py`, then publish ride-desk/ride-desk.html to that
artifact (Claude does this with its Artifact tool; the page's data lives in the artifact's own database, not here).
The nightly build also uses the built page, with made-up data (ride-desk/mock.js), for the manual's screenshots.

Usage: python3 ride-desk/build.py   (prints the size; exits 1 if a part is missing)
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'page')


def part(name):
    return open(os.path.join(P, name), encoding='utf-8').read()


def build():
    css = part('old.css') + part('new.css')
    code = ''.join(part(n) for n in ['p_head.js', 'main.js', 'p_offers.js', 'p_status.js', 'p_tail.js'])
    body = part('body.html').replace('/*GROUPS*/', part('groups.js')).replace('/*BRANDS*/', part('brands.js')).replace('/*CODE*/', code)
    return '<title>Ride Desk</title>\n<style>\n' + css + '</style>\n' + body


if __name__ == '__main__':
    html = build()
    open(os.path.join(HERE, 'ride-desk.html'), 'w', encoding='utf-8').write(html)
    print(f'ride-desk/ride-desk.html: {len(html)} bytes')
