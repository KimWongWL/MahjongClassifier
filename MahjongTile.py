from enum import Enum

class Tile(Enum):
    b1 = 1
    b2 = 2
    b3 = 3
    b4 = 4
    b5 = 5
    b6 = 6
    b7 = 7
    b8 = 8
    b9 = 9
    c1 = 11
    c2 = 12
    c3 = 13
    c4 = 14
    c5 = 15
    c6 = 16
    c7 = 17
    c8 = 18
    c9 = 19
    d1 = 21
    d2 = 22
    d3 = 23
    d4 = 24
    d5 = 25
    d6 = 26
    d7 = 27
    d8 = 28
    d9 = 29
    dr = 31
    dg = 32
    dw = 33
    we = 41
    ws = 42
    ww = 43
    wn = 44

class Flower(Enum):
    f1 = 1
    f1_s = 1
    f2 = 3
    f2_s = 3
    f3 = 5
    f3_s = 5
    f4 = 7
    f4_s = 7
    s1 = 2
    s1_s = 2
    s2 = 4
    s2_s = 4
    s3 = 6
    s3_s = 6
    s4 = 8
    s4_s = 8

class Meld(Enum):
    CHOW = 1
    PONG = 2
    KONG = 3
