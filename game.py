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

    # Memunculkan percikan ke segala arah dari posisi bola
    def burst(self, count, speed=6, size=4):
        x, y = self.center()
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            v = random.uniform(speed * 0.4, speed)
            item = self.canvas.create_oval(x - size, y - size,
                                           x + size, y + size,
                                           fill=self.color, outline='')
            self.particles.append({'item': item, 'x': x, 'y': y,
                                   'vx': math.cos(angle) * v,
                                   'vy': math.sin(angle) * v,
                                   'life': 10, 'max': 10,
                                   'size': size, 'color': self.color})

    # Dipanggil tiap frame: gambar ulang jejak & gerakkan percikan
    def update(self):
        # --- jejak bola: makin tua makin kecil dan makin pudar ---
        self.positions.append(self.center())
        self.positions = self.positions[-(TRAIL_LENGTH + 1):]
        for item in self.trail_items:
            self.canvas.delete(item)
        self.trail_items = []
        n = len(self.positions)
        for i, (px, py) in enumerate(self.positions[:-1]):
            t = (i + 1) / float(n)
            r = self.ball.radius * t
            item = self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                           fill=blend(BG_COLOR,
                                                      self.color, t),
                                           outline='')
            self.canvas.tag_lower(item, self.ball.item)
            self.trail_items.append(item)

        # --- percikan: bergerak, mengecil, memudar lalu hilang ---
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                self.canvas.delete(p['item'])
                self.particles.remove(p)
                continue
            frac = p['life'] / float(p['max'])
            r = max(1, p['size'] * frac)
            self.canvas.coords(p['item'], p['x'] - r, p['y'] - r,
                               p['x'] + r, p['y'] + r)
            self.canvas.itemconfig(p['item'],
                                   fill=blend(p['color'], BG_COLOR,
                                              1 - frac))

    # Hapus semua efek dari layar (dipakai saat game selesai)
    def clear(self):
        for item in self.trail_items:
            self.canvas.delete(item)
        for p in self.particles:
            self.canvas.delete(p['item'])
        self.trail_items = []
        self.particles = []


class Game(tk.Frame):
    def __init__(self, master):
        super(Game, self).__init__(master)
        self.width = 610
        self.height = 400
        self.canvas = tk.Canvas(self, bg=BG_COLOR,
                                width=self.width,
                                height=self.height,
                                highlightthickness=0)
        self.canvas.pack()
        self.pack()

        self.restart_btn = None
        self.high_score = self.load_high_score()
        self.build_level()
        self.canvas.focus_set()
        self.canvas.bind('<Left>',
                         lambda _: self.paddle.move(-20))
        self.canvas.bind('<Right>',
                         lambda _: self.paddle.move(20))
        # Papan mengikuti kursor mouse
        self.canvas.bind('<Motion>',
                         lambda e: self.paddle.move_to(e.x))

    # Membuat semua isi permainan dari awal (papan, blok, bola, skor).
    # Dipanggil saat game pertama kali dibuka dan saat restart.
    def build_level(self):
        self.canvas.delete('all')
        self.score = 0
        self.score_hud = None
        self.best_hud = None
        self.record_at_start = self.high_score
        self.items = {}
        self.ball = None
        self.paddle = Paddle(self.canvas, self.width/2, 326)
        self.items[self.paddle.item] = self.paddle
        for x in range(5, self.width - 5, 75):
            self.add_brick(x + 37.5, 50, 3)   # baris atas: 3x pukul
            self.add_brick(x + 37.5, 70, 2)   # baris tengah: 2x pukul
            self.add_brick(x + 37.5, 90, 1)   # baris bawah: 1x pukul
        self.setup_game()

    # FITUR BARU: tombol "Main Lagi" -> reset semuanya dan langsung main
    def restart_game(self):
        if self.restart_btn is not None:
            self.restart_btn.destroy()
            self.restart_btn = None
        self.build_level()
        self.canvas.focus_set()
        self.start_game()

    # Menampilkan pesan akhir (menang/kalah) beserta tombol Main Lagi
    def show_end(self, message, color, size=28):
        self.effects.clear()
        self.draw_text(300, 200, message, size, color)

        # Simpan rekor dan tampilkan ringkasan skor
        self.save_high_score()
        stats = 'Score: %s   Best: %s' % (self.score, self.high_score)
        new_record = self.score > self.record_at_start
        if new_record:
            stats += '   REKOR BARU!'
        self.draw_text(300, 238, stats, 14,
                       WIN_COLOR if new_record else TEXT_COLOR)
        self.restart_btn = tk.Button(self.canvas, text='Main Lagi',
                                     font=('Arial', 14, 'bold'),
                                     bg=PADDLE_COLOR, fg=BG_COLOR,
                                     activebackground=BALL_COLOR,
                                     relief='flat', padx=20, pady=6,
                                     cursor='hand2',
                                     command=self.restart_game)
        self.canvas.create_window(300, 290, window=self.restart_btn)

    def setup_game(self):
        self.add_ball()
        self.update_score_text()
        self.text = self.draw_text(300, 200,
                                   'Press Space or Click to start', 24)
        self.canvas.bind('<space>', lambda _: self.start_game())
        self.canvas.bind('<Button-1>', lambda _: self.start_game())

    def add_ball(self):
        if self.ball is not None:
            self.ball.delete()
        paddle_coords = self.paddle.get_position()
        x = (paddle_coords[0] + paddle_coords[2]) * 0.5
        self.ball = Ball(self.canvas, x, 310)
        self.paddle.set_ball(self.ball)
        self.effects = BallEffects(self.canvas, self.ball)

    def add_brick(self, x, y, hits):
        brick = Brick(self.canvas, x, y, hits)
        self.items[brick.item] = brick

    def draw_text(self, x, y, text, size=30, color=TEXT_COLOR):
        font = ('Arial', size, 'bold')
        return self.canvas.create_text(x, y, text=text,
                                       font=font, fill=color)

    def update_score_text(self):
        text = 'Score: %s' % self.score
        if self.score_hud is None:
            self.score_hud = self.draw_text(50, 20, text, 13)
        else:
            self.canvas.itemconfig(self.score_hud, text=text)

        # FITUR BARU: tampilan skor terbaik (best record) di pojok kanan atas
        best = 'Best: %s' % self.high_score
        if self.best_hud is None:
            self.best_hud = self.draw_text(self.width - 60, 20, best, 13,
                                           WIN_COLOR)
        else:
            self.canvas.itemconfig(self.best_hud, text=best)

    # Membaca skor terbaik dari file (0 kalau file belum ada)
    def load_high_score(self):
        try:
            with open(SCORE_FILE) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return 0

    # Menyimpan skor terbaik ke file supaya tidak hilang saat game ditutup
    def save_high_score(self):
        try:
            with open(SCORE_FILE, 'w') as f:
                f.write(str(self.high_score))
        except OSError:
            pass

    def start_game(self):
        self.canvas.unbind('<space>')
        self.canvas.unbind('<Button-1>')
        self.canvas.delete(self.text)
        self.paddle.ball = None
        self.game_loop()

    def game_loop(self):
        self.check_collisions()
        num_bricks = len(self.canvas.find_withtag('brick'))
        if num_bricks == 0:
            self.ball.speed = None
            self.show_end('You win!', WIN_COLOR, 36)
        elif self.ball.get_position()[3] >= self.height:
            # Bola jatuh = langsung kalah
            self.ball.speed = None
            self.show_end('You Lose!!! Game Over!', LOSE_COLOR)
        else:
            self.ball.update()
            self.effects.update()
            self.after(50, self.game_loop)

    def check_collisions(self):
        ball_coords = self.ball.get_position()
        items = self.canvas.find_overlapping(*ball_coords)
        objects = [self.items[x] for x in items if x in self.items]
        points = self.ball.collide(objects)
        # Percikan kecil saat bola mengenai papan
        if any(isinstance(o, Paddle) for o in objects):
            self.effects.burst(5, 5, 3)
        if points:
            self.score += points
            if self.score > self.high_score:
                self.high_score = self.score
            self.update_score_text()
            self.effects.set_score(self.score)   # cek ganti warna efek
            self.effects.burst(8, 7, 4)          # percikan saat kena blok


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Brick Breaker')
    game = Game(root)
    game.mainloop()