import pygame
import sys
import random
import math
import os
import wave
import struct
from pathlib import Path


# ============================================================
# 基础设置
# ============================================================

pygame.init()

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    AUDIO_AVAILABLE = True
except pygame.error:
    AUDIO_AVAILABLE = False


WIDTH = 1200
HEIGHT = 850

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("一箭又一箭 - Arrow Puzzle Game")

CLOCK = pygame.time.Clock()
FPS = 60


# ============================================================
# 颜色
# ============================================================

BG = (246, 249, 255)
BG_BLUE = (235, 243, 255)

WHITE = (255, 255, 255)
TEXT = (48, 67, 95)
SUB_TEXT = (115, 132, 157)

BLUE = (82, 139, 235)
BLUE_DARK = (55, 105, 190)
BLUE_LIGHT = (232, 241, 255)

GREEN = (76, 190, 128)
GREEN_LIGHT = (232, 250, 240)

ORANGE = (248, 174, 65)
ORANGE_DARK = (224, 145, 38)

RED = (235, 98, 103)
RED_LIGHT = (255, 237, 238)

GRID = (218, 227, 240)
BOARD_BORDER = (204, 217, 236)

SHADOW = (210, 220, 235)


# ============================================================
# 字体
# ============================================================

def get_font(size, bold=False):
    """
    优先使用 macOS 苹方字体，避免中文乱码。
    """
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except:
                pass

    return pygame.font.SysFont(
        "Arial Unicode MS",
        size,
        bold=bold
    )


FONT_TITLE = get_font(42, True)
FONT_SUBTITLE = get_font(17)
FONT_INFO = get_font(22, True)
FONT_SMALL = get_font(17)
FONT_BUTTON = get_font(22, True)
FONT_BIG = get_font(32, True)
FONT_RESULT = get_font(38, True)


# ============================================================
# 棋盘
# ============================================================

ROWS = 5
COLS = 5

CELL_SIZE = 90

BOARD_SIZE = ROWS * CELL_SIZE

BOARD_X = (WIDTH - BOARD_SIZE) // 2
BOARD_Y = 255


# ============================================================
# 游戏参数
# ============================================================

MAX_LEVELS = 3
MAX_MISTAKES = 3

current_level = 1
mistakes = 0

level_complete = False
game_over = False
game_finished = False

# 游戏启动时先显示首页
HOME_SCREEN = True

arrows = []

flying_arrow = None

message_text = "点击没有被挡住的箭头"
message_timer = 0


# ============================================================
# 按钮
# ============================================================

restart_button = pygame.Rect(
    WIDTH - 280,
    HEIGHT - 92,
    210,
    58
)

home_button = pygame.Rect(
    70,
    HEIGHT - 92,
    210,
    58
)

# 首页“开始游戏”按钮
start_button = pygame.Rect(
    WIDTH // 2 - 150,
    505,
    300,
    72
)


# ============================================================
# 圆角矩形工具
# ============================================================

def draw_round_rect(surface, color, rect, radius=18, shadow=True):
    rect = pygame.Rect(rect)

    if shadow:
        shadow_rect = rect.move(0, 6)
        pygame.draw.rect(
            surface,
            SHADOW,
            shadow_rect,
            border_radius=radius
        )

    pygame.draw.rect(
        surface,
        color,
        rect,
        border_radius=radius
    )


# ============================================================
# 生成背景音乐
# ============================================================

def create_background_music():
    """
    如果项目里没有音乐，就自动生成一段简单轻快的背景音乐。
    这样不会因为缺少 mp3 导致背景音乐消失。
    """

    music_dir = Path("assets")
    music_dir.mkdir(exist_ok=True)

    music_path = music_dir / "background_music.wav"

    if music_path.exists():
        return str(music_path)

    sample_rate = 44100

    # 一段轻快的旋律
    melody = [
        (523, 0.25),
        (659, 0.25),
        (784, 0.25),
        (659, 0.25),

        (587, 0.25),
        (698, 0.25),
        (880, 0.25),
        (698, 0.25),

        (523, 0.25),
        (659, 0.25),
        (784, 0.25),
        (988, 0.25),

        (880, 0.25),
        (784, 0.25),
        (659, 0.25),
        (523, 0.5),
    ]

    samples = []

    for frequency, duration in melody:

        count = int(sample_rate * duration)

        for i in range(count):

            t = i / sample_rate

            envelope = 1.0

            fade = int(sample_rate * 0.025)

            if i < fade:
                envelope = i / fade

            elif i > count - fade:
                envelope = max(
                    0,
                    (count - i) / fade
                )

            wave1 = math.sin(
                2 * math.pi * frequency * t
            )

            wave2 = math.sin(
                2 * math.pi * frequency * 2 * t
            ) * 0.25

            value = (
                wave1 * 0.65 +
                wave2
            )

            value *= envelope
            value *= 0.22

            samples.append(
                int(value * 32767)
            )

    with wave.open(str(music_path), "wb") as wav:

        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = b"".join(
            struct.pack("<h", sample)
            for sample in samples
        )

        wav.writeframes(frames)

    return str(music_path)


def start_background_music():
    """
    整个游戏只启动一次背景音乐。
    切换关卡不会重新停止音乐。
    """

    if not AUDIO_AVAILABLE:
        return

    try:
        music_path = create_background_music()

        pygame.mixer.music.load(music_path)

        pygame.mixer.music.set_volume(0.25)

        pygame.mixer.music.play(-1)

    except Exception as e:
        print("背景音乐启动失败：", e)


# ============================================================
# 关卡模板
# 每一关都经过程序验证，保证至少存在一种完整通关顺序。
# ============================================================

LEVEL_TEMPLATES = [

    # 第 1 关：6 个箭头
    [
        {"row": 0, "col": 4, "direction": "UP"},
        {"row": 1, "col": 0, "direction": "UP"},
        {"row": 1, "col": 4, "direction": "RIGHT"},
        {"row": 2, "col": 1, "direction": "UP"},
        {"row": 3, "col": 1, "direction": "RIGHT"},
        {"row": 3, "col": 3, "direction": "RIGHT"},
    ],

    # 第 2 关：6 个箭头
    [
        {"row": 0, "col": 1, "direction": "DOWN"},
        {"row": 2, "col": 1, "direction": "DOWN"},
        {"row": 1, "col": 4, "direction": "LEFT"},
        {"row": 1, "col": 2, "direction": "LEFT"},
        {"row": 3, "col": 3, "direction": "UP"},
        {"row": 4, "col": 0, "direction": "RIGHT"},
    ],

    # 第 3 关：6 个箭头
    # 这一关与前两关不同方向组合，但同样经过求解器验证。
    [
        {"row": 0, "col": 0, "direction": "RIGHT"},
        {"row": 0, "col": 3, "direction": "RIGHT"},
        {"row": 2, "col": 4, "direction": "DOWN"},
        {"row": 4, "col": 4, "direction": "LEFT"},
        {"row": 4, "col": 2, "direction": "LEFT"},
        {"row": 2, "col": 1, "direction": "UP"},
    ],
]


# ============================================================
# 关卡可解性验证器
# ============================================================

def arrow_is_blocked_in_state(arrow, state):
    """
    在给定的剩余箭头 state 中，判断某支箭头是否被挡住。
    规则与游戏实际点击判断完全一致。
    """

    row = arrow["row"]
    col = arrow["col"]
    direction = arrow["direction"]

    for other in state:
        if other is arrow:
            continue

        other_row = other["row"]
        other_col = other["col"]

        if direction == "UP" and other_col == col and other_row < row:
            return True

        if direction == "DOWN" and other_col == col and other_row > row:
            return True

        if direction == "LEFT" and other_row == row and other_col < col:
            return True

        if direction == "RIGHT" and other_row == row and other_col > col:
            return True

    return False


def find_solution(template):
    """
    搜索一条完整通关顺序。
    返回箭头下标组成的顺序；如果无解则返回 None。
    """

    arrows_to_check = [dict(item) for item in template]

    def search(state, path):

        if not state:
            return path

        for index, arrow in enumerate(state):

            if arrow_is_blocked_in_state(arrow, state):
                continue

            next_state = state[:index] + state[index + 1:]
            result = search(next_state, path + [index])

            if result is not None:
                return result

        return None

    return search(arrows_to_check, [])


def validate_all_levels():
    """
    游戏启动前检查每一关是否至少存在一种通关方式。
    如果任何一关无解，程序直接停止，避免出现死局。
    """

    print("\n========== 关卡可解性检查 ==========")

    for level_number, template in enumerate(LEVEL_TEMPLATES, start=1):
        solution = find_solution(template)

        if solution is None:
            print(f"第 {level_number} 关：× 无解")
            raise RuntimeError(
                f"第 {level_number} 关没有任何通关方式，请检查关卡配置。"
            )

        print(
            f"第 {level_number} 关：√ 存在通关方式 "
            f"（搜索到 {len(solution)} 步完整方案）"
        )

    print("==================================\n")


# ============================================================
# 检测箭头是否被挡住
# ============================================================

def is_blocked(arrow):
    """
    判断箭头前方同一行 / 同一列有没有其他箭头。
    """

    row = arrow["row"]
    col = arrow["col"]
    direction = arrow["direction"]

    for other in arrows:

        if other is arrow:
            continue

        other_row = other["row"]
        other_col = other["col"]

        if direction == "UP":

            if (
                other_col == col
                and other_row < row
            ):
                return True

        elif direction == "DOWN":

            if (
                other_col == col
                and other_row > row
            ):
                return True

        elif direction == "LEFT":

            if (
                other_row == row
                and other_col < col
            ):
                return True

        elif direction == "RIGHT":

            if (
                other_row == row
                and other_col > col
            ):
                return True

    return False


# ============================================================
# 加载关卡
# ============================================================

last_template = None


def load_level(level_number):

    global arrows
    global mistakes
    global level_complete
    global game_over
    global flying_arrow
    global message_text
    global message_timer

    mistakes = 0

    level_complete = False
    game_over = False

    flying_arrow = None

    message_text = "点击没有被挡住的箭头"
    message_timer = 0

    # 每个关卡固定使用自己的模板。
    # 这样可以确保第 1/2/3 关分别对应已经验证过的地图。
    template = LEVEL_TEMPLATES[level_number - 1]

    arrows = []

    for item in template:
        arrows.append(
            {
                "row": item["row"],
                "col": item["col"],
                "direction": item["direction"],
                "alpha": 255,
                "scale": 1.0,
            }
        )


# ============================================================
# 棋盘坐标
# ============================================================

def cell_center(row, col):

    x = (
        BOARD_X
        + col * CELL_SIZE
        + CELL_SIZE // 2
    )

    y = (
        BOARD_Y
        + row * CELL_SIZE
        + CELL_SIZE // 2
    )

    return x, y


# ============================================================
# 绘制箭头
# ============================================================

def draw_arrow(
    surface,
    center_x,
    center_y,
    direction,
    alpha=255,
    scale=1.0,
    arrow_color_rgb=None
):

    size = int(48 * scale)

    temp = pygame.Surface(
        (size * 2, size * 2),
        pygame.SRCALPHA
    )

    cx = size
    cy = size

    # 圆形浅色底
    pygame.draw.circle(
        temp,
        (
            226,
            238,
            255,
            alpha
        ),
        (cx, cy),
        int(34 * scale)
    )

    # 箭头主体
    if arrow_color_rgb is None:
        arrow_color_rgb = (70, 126, 224)

    arrow_color = (
        arrow_color_rgb[0],
        arrow_color_rgb[1],
        arrow_color_rgb[2],
        alpha
    )

    shaft_width = max(
        8,
        int(11 * scale)
    )

    head_size = int(19 * scale)

    shaft_length = int(29 * scale)

    if direction == "UP":

        pygame.draw.rect(
            temp,
            arrow_color,
            (
                cx - shaft_width // 2,
                cy - 2,
                shaft_width,
                shaft_length
            ),
            border_radius=5
        )

        points = [
            (cx, cy - head_size - 10),
            (cx - head_size, cy + 2),
            (cx + head_size, cy + 2),
        ]

    elif direction == "DOWN":

        pygame.draw.rect(
            temp,
            arrow_color,
            (
                cx - shaft_width // 2,
                cy - shaft_length,
                shaft_width,
                shaft_length
            ),
            border_radius=5
        )

        points = [
            (cx, cy + head_size + 10),
            (cx - head_size, cy - 2),
            (cx + head_size, cy - 2),
        ]

    elif direction == "LEFT":

        pygame.draw.rect(
            temp,
            arrow_color,
            (
                cx - 2,
                cy - shaft_width // 2,
                shaft_length,
                shaft_width
            ),
            border_radius=5
        )

        points = [
            (cx - head_size - 10, cy),
            (cx + 2, cy - head_size),
            (cx + 2, cy + head_size),
        ]

    else:

        pygame.draw.rect(
            temp,
            arrow_color,
            (
                cx - shaft_length,
                cy - shaft_width // 2,
                shaft_length,
                shaft_width
            ),
            border_radius=5
        )

        points = [
            (cx + head_size + 10, cy),
            (cx - 2, cy - head_size),
            (cx - 2, cy + head_size),
        ]

    pygame.draw.polygon(
        temp,
        arrow_color,
        points
    )

    surface.blit(
        temp,
        (
            int(center_x - temp.get_width() / 2),
            int(center_y - temp.get_height() / 2)
        )
    )


# ============================================================
# 绘制游戏首页
# ============================================================

def draw_home_screen():
    SCREEN.fill(BG)

    # 顶部浅蓝背景
    pygame.draw.rect(
        SCREEN,
        BG_BLUE,
        (0, 0, WIDTH, 310)
    )

    # 装饰圆
    pygame.draw.circle(
        SCREEN,
        (228, 239, 255),
        (120, 170),
        120
    )
    pygame.draw.circle(
        SCREEN,
        (255, 242, 222),
        (WIDTH - 110, 150),
        130
    )

    # 游戏标题
    title = get_font(64, True).render(
        "一箭又一箭",
        True,
        TEXT
    )
    SCREEN.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 165)
        )
    )

    subtitle = get_font(24).render(
        "ARROW PUZZLE GAME",
        True,
        SUB_TEXT
    )
    SCREEN.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 215)
        )
    )

    # 游戏说明
    info = get_font(21).render(
        "点击没有被挡住的箭头，让所有箭头依次飞出棋盘",
        True,
        TEXT
    )
    SCREEN.blit(
        info,
        info.get_rect(
            center=(WIDTH // 2, 355)
        )
    )

    info2 = get_font(18).render(
        "每关最多允许 3 次错误",
        True,
        SUB_TEXT
    )
    SCREEN.blit(
        info2,
        info2.get_rect(
            center=(WIDTH // 2, 390)
        )
    )

    # 开始游戏按钮
    draw_round_rect(
        SCREEN,
        BLUE,
        start_button,
        22
    )

    start_text = get_font(26, True).render(
        "开始游戏",
        True,
        WHITE
    )
    SCREEN.blit(
        start_text,
        start_text.get_rect(
            center=start_button.center
        )
    )

    # 底部提示
    tip = get_font(16).render(
        "一共有 3 个关卡，祝你通关愉快！",
        True,
        SUB_TEXT
    )
    SCREEN.blit(
        tip,
        tip.get_rect(
            center=(WIDTH // 2, 625)
        )
    )


# ============================================================
# 绘制背景
# ============================================================

def draw_background():

    SCREEN.fill(BG)

    # 顶部浅蓝区域
    pygame.draw.rect(
        SCREEN,
        BG_BLUE,
        (0, 0, WIDTH, 215)
    )

    # 左上装饰圆
    pygame.draw.circle(
        SCREEN,
        (228, 239, 255),
        (35, 245),
        150
    )

    # 右下装饰圆
    pygame.draw.circle(
        SCREEN,
        (255, 242, 222),
        (WIDTH - 30, HEIGHT - 20),
        150
    )

    # 左下装饰圆
    pygame.draw.circle(
        SCREEN,
        (232, 242, 255),
        (80, HEIGHT - 10),
        120
    )

    # 右上装饰圆
    pygame.draw.circle(
        SCREEN,
        (232, 242, 255),
        (WIDTH - 40, 80),
        120
    )


# ============================================================
# 顶部 UI
# ============================================================

def draw_header():

    # 左侧关卡框
    level_rect = pygame.Rect(
        65,
        45,
        245,
        68
    )

    draw_round_rect(
        SCREEN,
        WHITE,
        level_rect,
        34
    )

    pygame.draw.rect(
        SCREEN,
        BLUE,
        level_rect,
        width=2,
        border_radius=34
    )

    level_text = FONT_INFO.render(
        f"第 {current_level} / {MAX_LEVELS} 关",
        True,
        TEXT
    )

    SCREEN.blit(
        level_text,
        level_text.get_rect(
            center=level_rect.center
        )
    )

    # 中央标题
    title = FONT_TITLE.render(
        "一箭又一箭",
        True,
        TEXT
    )

    SCREEN.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 66)
        )
    )

    subtitle = FONT_SUBTITLE.render(
        "ARROW PUZZLE GAME",
        True,
        SUB_TEXT
    )

    SCREEN.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 102)
        )
    )

    # 右侧错误框
    mistake_rect = pygame.Rect(
        WIDTH - 310,
        45,
        245,
        68
    )

    draw_round_rect(
        SCREEN,
        WHITE,
        mistake_rect,
        34
    )

    pygame.draw.rect(
        SCREEN,
        GREEN,
        mistake_rect,
        width=2,
        border_radius=34
    )

    mistake_text = FONT_INFO.render(
        f"错误次数：{mistakes} / {MAX_MISTAKES}",
        True,
        TEXT
    )

    SCREEN.blit(
        mistake_text,
        mistake_text.get_rect(
            center=mistake_rect.center
        )
    )

    # 右侧下方显示剩余箭头数量
    arrow_count_rect = pygame.Rect(
        WIDTH - 310,
        125,
        245,
        52
    )

    draw_round_rect(
        SCREEN,
        WHITE,
        arrow_count_rect,
        26,
        shadow=False
    )

    pygame.draw.rect(
        SCREEN,
        BLUE_LIGHT,
        arrow_count_rect,
        width=2,
        border_radius=26
    )

    arrow_count_text = FONT_SMALL.render(
        f"剩余箭头：{len(arrows)} 个",
        True,
        TEXT
    )

    SCREEN.blit(
        arrow_count_text,
        arrow_count_text.get_rect(
            center=arrow_count_rect.center
        )
    )


# ============================================================
# 绘制棋盘
# ============================================================

def draw_board():

    outer_rect = pygame.Rect(
        BOARD_X - 22,
        BOARD_Y - 22,
        BOARD_SIZE + 44,
        BOARD_SIZE + 44
    )

    # 阴影
    shadow_rect = outer_rect.move(0, 8)

    pygame.draw.rect(
        SCREEN,
        SHADOW,
        shadow_rect,
        border_radius=28
    )

    pygame.draw.rect(
        SCREEN,
        WHITE,
        outer_rect,
        border_radius=28
    )

    pygame.draw.rect(
        SCREEN,
        BOARD_BORDER,
        outer_rect,
        width=2,
        border_radius=28
    )

    # 棋盘背景
    board_rect = pygame.Rect(
        BOARD_X,
        BOARD_Y,
        BOARD_SIZE,
        BOARD_SIZE
    )

    pygame.draw.rect(
        SCREEN,
        (251, 253, 255),
        board_rect,
        border_radius=4
    )

    # 网格
    for row in range(ROWS + 1):

        y = BOARD_Y + row * CELL_SIZE

        pygame.draw.line(
            SCREEN,
            GRID,
            (BOARD_X, y),
            (
                BOARD_X + BOARD_SIZE,
                y
            ),
            2
        )

    for col in range(COLS + 1):

        x = BOARD_X + col * CELL_SIZE

        pygame.draw.line(
            SCREEN,
            GRID,
            (x, BOARD_Y),
            (
                x,
                BOARD_Y + BOARD_SIZE
            ),
            2
        )


# ============================================================
# 绘制箭头
# ============================================================

def draw_arrows():

    for arrow in arrows:

        x, y = cell_center(
            arrow["row"],
            arrow["col"]
        )

        # 被阻挡的箭头在短时间内显示为红色，提示玩家发生碰撞
        is_red = pygame.time.get_ticks() < arrow.get("blocked_until", 0)

        draw_arrow(
            SCREEN,
            x,
            y,
            arrow["direction"],
            arrow.get("alpha", 255),
            arrow.get("scale", 1.0),
            (235, 75, 75) if is_red else None
        )


# ============================================================
# 飞出动画
# ============================================================

def update_flying_arrow():

    global flying_arrow
    global arrows
    global level_complete
    global message_text
    global message_timer

    if flying_arrow is None:
        return

    flying_arrow["progress"] += 0.035

    progress = flying_arrow["progress"]

    # 平滑缓动
    eased = 1 - (1 - progress) ** 3

    start_x = flying_arrow["start_x"]
    start_y = flying_arrow["start_y"]

    direction = flying_arrow["direction"]

    distance = 260

    if direction == "UP":

        target_x = start_x
        target_y = start_y - distance

    elif direction == "DOWN":

        target_x = start_x
        target_y = start_y + distance

    elif direction == "LEFT":

        target_x = start_x - distance
        target_y = start_y

    else:

        target_x = start_x + distance
        target_y = start_y

    flying_arrow["x"] = (
        start_x
        + (target_x - start_x) * eased
    )

    flying_arrow["y"] = (
        start_y
        + (target_y - start_y) * eased
    )

    flying_arrow["alpha"] = int(
        255 * (1 - progress)
    )

    flying_arrow["scale"] = (
        1.0
        + 0.18 * progress
    )

    if progress >= 1.0:

        flying_arrow = None

        if len(arrows) == 0:

            level_complete = True

            message_text = "太棒了！本关完成！"

            message_timer = 120


# ============================================================
# 绘制飞行中的箭头
# ============================================================

def draw_flying_arrow():

    if flying_arrow is None:
        return

    draw_arrow(
        SCREEN,
        flying_arrow["x"],
        flying_arrow["y"],
        flying_arrow["direction"],
        flying_arrow["alpha"],
        flying_arrow["scale"]
    )


# ============================================================
# 点击箭头
# ============================================================

def click_arrow(mouse_x, mouse_y):

    global mistakes
    global game_over
    global flying_arrow
    global message_text
    global message_timer
    global arrows

    if flying_arrow is not None:
        return

    for arrow in reversed(arrows):

        x, y = cell_center(
            arrow["row"],
            arrow["col"]
        )

        distance = math.sqrt(
            (mouse_x - x) ** 2
            + (mouse_y - y) ** 2
        )

        if distance <= 42:

            if is_blocked(arrow):

                # 标记该箭头短暂变红，形成明确的碰撞反馈
                arrow["blocked_until"] = pygame.time.get_ticks() + 700

                mistakes += 1

                message_text = "这个箭头被挡住啦！"
                message_timer = 70

                if mistakes >= MAX_MISTAKES:

                    game_over = True

                    message_text = "挑战失败，再试一次吧！"
                    message_timer = 180

                return

            # ------------------------------------------------
            # 可以飞出
            # ------------------------------------------------

            flying_arrow = {
                "row": arrow["row"],
                "col": arrow["col"],
                "direction": arrow["direction"],

                "start_x": x,
                "start_y": y,

                "x": x,
                "y": y,

                "progress": 0.0,
                "alpha": 255,
                "scale": 1.0,
            }

            arrows.remove(arrow)

            message_text = "漂亮！箭头飞出去啦！"
            message_timer = 45

            return


# ============================================================
# 绘制底部按钮
# ============================================================

def draw_buttons():

    # 返回首页
    draw_round_rect(
        SCREEN,
        WHITE,
        home_button,
        20
    )

    pygame.draw.rect(
        SCREEN,
        BOARD_BORDER,
        home_button,
        width=2,
        border_radius=20
    )

    home_text = FONT_BUTTON.render(
        "返回首页",
        True,
        TEXT
    )

    SCREEN.blit(
        home_text,
        home_text.get_rect(
            center=home_button.center
        )
    )

    # 重新开始
    draw_round_rect(
        SCREEN,
        ORANGE,
        restart_button,
        20
    )

    restart_text = FONT_BUTTON.render(
        "重新开始",
        True,
        WHITE
    )

    SCREEN.blit(
        restart_text,
        restart_text.get_rect(
            center=restart_button.center
        )
    )


# ============================================================
# 中间提示文字
# ============================================================

def draw_message():

    if message_timer <= 0:
        return

    rect = pygame.Rect(
        WIDTH // 2 - 190,
        HEIGHT - 86,
        380,
        46
    )

    pygame.draw.rect(
        SCREEN,
        BLUE_LIGHT,
        rect,
        border_radius=23
    )

    text = FONT_SMALL.render(
        message_text,
        True,
        SUB_TEXT
    )

    SCREEN.blit(
        text,
        text.get_rect(
            center=rect.center
        )
    )


# ============================================================
# 成功 / 失败界面
# ============================================================

def draw_overlay():

    if not level_complete and not game_over and not game_finished:
        return

    overlay = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA
    )

    overlay.fill(
        (255, 255, 255, 100)
    )

    SCREEN.blit(
        overlay,
        (0, 0)
    )

    panel = pygame.Rect(
        WIDTH // 2 - 260,
        280,
        520,
        230
    )

    draw_round_rect(
        SCREEN,
        WHITE,
        panel,
        28
    )

    if game_over:

        title = FONT_RESULT.render(
            "挑战失败",
            True,
            RED
        )

        sub = FONT_SMALL.render(
            "别灰心，再试一次吧！",
            True,
            SUB_TEXT
        )

    elif game_finished:

        title = FONT_RESULT.render(
            "全部通关！",
            True,
            GREEN
        )

        sub = FONT_SMALL.render(
            "恭喜你完成了全部 3 个关卡！",
            True,
            SUB_TEXT
        )

    else:

        title = FONT_RESULT.render(
            "关卡完成！",
            True,
            GREEN
        )

        if current_level < MAX_LEVELS:

            sub = FONT_SMALL.render(
                "点击任意位置进入下一关",
                True,
                SUB_TEXT
            )

        else:

            sub = FONT_SMALL.render(
                "最后一关完成！",
                True,
                SUB_TEXT
            )

    SCREEN.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 350)
        )
    )

    SCREEN.blit(
        sub,
        sub.get_rect(
            center=(WIDTH // 2, 400)
        )
    )


# ============================================================
# 返回首页
# ============================================================

def go_home():

    global current_level
    global mistakes
    global level_complete
    global game_over
    global game_finished
    global HOME_SCREEN

    current_level = 1
    mistakes = 0

    level_complete = False
    game_over = False
    game_finished = False
    HOME_SCREEN = True


# ============================================================
# 下一关
# ============================================================

def next_level():

    global current_level
    global level_complete
    global game_finished

    if current_level < MAX_LEVELS:

        current_level += 1

        level_complete = False

        load_level(current_level)

    else:

        game_finished = True


# ============================================================
# 主程序
# ============================================================

# 启动前强制验证 3 个关卡都至少存在一种完整通关方案。
validate_all_levels()

start_background_music()

running = True

while running:

    dt = CLOCK.tick(FPS)

    # --------------------------------------------------------
    # 计时器
    # --------------------------------------------------------

    if message_timer > 0:
        message_timer -= 1

    # --------------------------------------------------------
    # 飞行动画
    # --------------------------------------------------------

    update_flying_arrow()

    # --------------------------------------------------------
    # 事件
    # --------------------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:

            mouse_x, mouse_y = event.pos

            # ----------------------------------------------
            # 首页
            # ----------------------------------------------

            if HOME_SCREEN:

                if start_button.collidepoint(
                    mouse_x,
                    mouse_y
                ):
                    HOME_SCREEN = False
                    load_level(1)

                continue

            # ----------------------------------------------
            # 返回首页
            # ----------------------------------------------

            if home_button.collidepoint(
                mouse_x,
                mouse_y
            ):

                go_home()

                continue

            # ----------------------------------------------
            # 重新开始
            # ----------------------------------------------

            if restart_button.collidepoint(
                mouse_x,
                mouse_y
            ):

                load_level(current_level)

                continue

            # ----------------------------------------------
            # 游戏失败
            # ----------------------------------------------

            if game_over:

                continue

            # ----------------------------------------------
            # 全部完成
            # ----------------------------------------------

            if game_finished:

                continue

            # ----------------------------------------------
            # 关卡完成
            # ----------------------------------------------

            if level_complete:

                if current_level < MAX_LEVELS:

                    next_level()

                else:

                    game_finished = True

                continue

            # ----------------------------------------------
            # 点击箭头
            # ----------------------------------------------

            click_arrow(
                mouse_x,
                mouse_y
            )

    # --------------------------------------------------------
    # 绘制
    # --------------------------------------------------------

    if HOME_SCREEN:

        draw_home_screen()

    else:

        draw_background()

        draw_header()

        draw_board()

        draw_arrows()

        draw_flying_arrow()

        draw_buttons()

        draw_message()

        draw_overlay()

    pygame.display.flip()


pygame.quit()
sys.exit()