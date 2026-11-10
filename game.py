import math
import os
import random
import tkinter as tk

# --Warna
BG_COLOR = '#0f172a'        # latar belakang: biru gelap
BALL_COLOR = '#ffdd33'      # bola: kuning
PADDLE_COLOR = '#00c8ff'    # papan: biru cyan
TEXT_COLOR = '#90ee90'      # teks HUD: hijau muda
WIN_COLOR = '#ffdd33'       # teks menang: kuning
LOSE_COLOR = '#ff6363'      # teks kalah: merah muda

# File untuk menyimpan skor terbaik 
SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'best_score.txt')

#  Efek bola 
# Warna efek berganti setiap skor naik 30 poin (30, 60, 90, ...)
EFFECT_STEP = 30
EFFECT_COLORS = ['#ffdd33',   # 0-29   : kuning
                 '#00ffd5',   # 30-59  : aqua
                 '#ff4fd8',   # 60-89  : pink
                 '#7cfc00',   # 90-119 : hijau neon
                 '#ff6347',   # 120-149: merah jingga
                 '#a78bfa']   # 150-179: ungu muda (lalu berulang dari awal)
TRAIL_LENGTH = 7              # jumlah bayangan di belakang bola


class GameObject(object):
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.item = item

    def get_position(self):
        return self.canvas.coords(self.item)

    def move(self, x, y):
        self.canvas.move(self.item, x, y)

    def delete(self):
        self.canvas.delete(self.item)


class Ball(GameObject):
    def __init__(self, canvas, x, y):
        self.radius = 10
        self.direction = [1, -1]
        self.speed = 10
        item = canvas.create_oval(x-self.radius, y-self.radius,
                                  x+self.radius, y+self.radius,
                                  fill=BALL_COLOR, outline='')
        super(Ball, self).__init__(canvas, item)

    def update(self):
        coords = self.get_position()
        width = self.canvas.winfo_width()
        if coords[0] <= 0 or coords[2] >= width:
            self.direction[0] *= -1
        if coords[1] <= 0:
            self.direction[1] *= -1
        x = self.direction[0] * self.speed
        y = self.direction[1] * self.speed
        self.move(x, y)

    # Mengembalikan poin yang didapat dari tabrakan ini
    def collide(self, game_objects):
        coords = self.get_position()
        x = (coords[0] + coords[2]) * 0.5
        if len(game_objects) > 1:
            self.direction[1] *= -1
        elif len(game_objects) == 1:
            game_object = game_objects[0]
            coords = game_object.get_position()
            if x > coords[2]:
                self.direction[0] = 1
            elif x < coords[0]:
                self.direction[0] = -1
            else:
                self.direction[1] *= -1

        points = 0
        for game_object in game_objects:
            if isinstance(game_object, Brick):
                # Setiap pukulan ke blok = 5 poin,
                # blok hancur = bonus 10 poin
                points += 5
                if game_object.hit():
                    points += 10
        return points


class Paddle(GameObject):
    def __init__(self, canvas, x, y):
        self.width = 160          # papan diperpanjang: 80 -> 160
        self.height = 12
        self.ball = None
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill=PADDLE_COLOR, outline='')
        super(Paddle, self).__init__(canvas, item)

    def set_ball(self, ball):
        self.ball = ball

    def move(self, offset):
        coords = self.get_position()
        width = self.canvas.winfo_width()
        if coords[0] + offset >= 0 and coords[2] + offset <= width:
            super(Paddle, self).move(offset, 0)
            if self.ball is not None:
                self.ball.move(offset, 0)


    # FITUR BARU: pindahkan papan supaya titik tengahnya mengikuti
    # posisi x kursor, tapi tetap dibatasi supaya tidak keluar layar
    def move_to(self, x):
        coords = self.get_position()
        width = self.canvas.winfo_width()
        center = (coords[0] + coords[2]) / 2
        offset = x - center
        if coords[0] + offset < 0:
            offset = -coords[0]
        elif coords[2] + offset > width:
            offset = width - coords[2]
        super(Paddle, self).move(offset, 0)
        if self.ball is not None:
            self.ball.move(offset, 0)


class Brick(GameObject):
    # Warna blok berdasarkan sisa "nyawa" blok
    COLORS = {1: '#ff8c00', 2: '#ba55d3', 3: '#32cd32'}

    def __init__(self, canvas, x, y, hits):
        self.width = 75
        self.height = 20
        self.hits = hits
        color = Brick.COLORS[hits]
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill=color, outline=BG_COLOR,
                                       width=2, tags='brick')
        super(Brick, self).__init__(canvas, item)

    # Mengembalikan True kalau blok hancur
    def hit(self):
        self.hits -= 1
        if self.hits == 0:
            self.delete()
            return True
        self.canvas.itemconfig(self.item,
                               fill=Brick.COLORS[self.hits])
        return False


# Mencampur dua warna hex. t=0 -> warna a, t=1 -> warna b
def blend(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    mix = [int(ca[k] + (cb[k] - ca[k]) * t) for k in range(3)]
    return '#%02x%02x%02x' % tuple(mix)


class BallEffects(object):
    """Efek visual untuk bola: jejak (trail), percikan (particle),
    dan warna bola. Semuanya berubah warna tiap kelipatan 30 skor."""

    def __init__(self, canvas, ball):
        self.canvas = canvas
        self.ball = ball
        self.level = 0
        self.color = EFFECT_COLORS[0]
        self.positions = []     # riwayat posisi bola untuk jejak
        self.trail_items = []   # lingkaran-lingkaran jejak di canvas
        self.particles = []     # percikan yang sedang aktif
        self.apply_color()

    # Mewarnai bola: inti bola dibuat versi pucat/terang dari warna efek
    # (seperti api yang paling panas), sedangkan tepinya memakai warna
    # efek yang pekat. Jadi bola terlihat menyala dan tidak menyatu
    # dengan jejak/percikan yang berwarna pekat.
    def apply_color(self):
        self.canvas.itemconfig(self.ball.item,
                               fill=blend(self.color, '#ffffff', 0.65),
                               outline=self.color, width=3)

    def center(self):
        c = self.ball.get_position()
        return (c[0] + c[2]) / 2, (c[1] + c[3]) / 2

    # Dipanggil tiap skor berubah: ganti warna efek kalau naik 30 poin
    def set_score(self, score):
        level = score // EFFECT_STEP
        if level != self.level:
            self.level = level
            self.color = EFFECT_COLORS[level % len(EFFECT_COLORS)]
            self.apply_color()
            self.burst(18, 9, 6)    # ledakan besar tanda warna berganti

