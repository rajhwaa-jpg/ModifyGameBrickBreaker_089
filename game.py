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


