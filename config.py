"""Configuracoes centralizadas do projeto.

Ajuste os thresholds deste arquivo durante os testes de camera.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
POSE_MODEL_PATH = MODELS_DIR / "pose_landmarker_lite.task"
FACE_MODEL_PATH = MODELS_DIR / "face_landmarker.task"
GESTURE_MODEL_PATH = MODELS_DIR / "gesture_recognizer.task"

# Camera
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

# Recorte central da webcam. O MediaPipe recebe apenas esta regiao, o que ajuda
# a ignorar pessoas nas laterais e manter o foco em quem esta no centro.
CAMERA_CENTER_CROP_ENABLED = True
# 0.55 = mantem 55% da largura original (corta 22.5% de cada lado).
# Diminua para fechar mais o campo; aumente para mostrar mais da cena.
CAMERA_CENTER_CROP_WIDTH_RATIO = 0.55
# Para CORPO, deixe 1.0 para nao cortar cabeca/pes.
CAMERA_CENTER_CROP_HEIGHT_RATIO = 1.00
# Permite deslocar o centro do recorte sem mover a camera.
# 0.0 = exatamente central; valores positivos movem o recorte para direita/baixo.
CAMERA_CENTER_CROP_OFFSET_X = 0.0
CAMERA_CENTER_CROP_OFFSET_Y = 0.0

# MediaPipe
MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
POSE_MIN_VISIBILITY = 0.35

# Calibracao
CALIBRATION_COUNTDOWN_SECONDS = 3.0
CALIBRATION_SAMPLES = 30

# Estabilizacao de estado
SMOOTHING_WINDOW = 5
MIN_STATE_VOTES = 3

# Modo MAOS: janela menor para responder rapido aos gestos.
HAND_SMOOTHING_WINDOW = 3
HAND_MIN_STATE_VOTES = 2

# Controle do jogo
COMMAND_COOLDOWN = 0.22
DOUBLE_LANE_COMMAND_INTERVAL = 0.12
REQUIRE_GAME_FOCUS = False
GAME_WINDOW_KEYWORDS = ("Subway Surfers", "Google Play Games")

# Modo CORPO
LATERAL_THRESHOLD = 0.45
JUMP_THRESHOLD = 0.18
CROUCH_HIP_THRESHOLD = 0.12
CROUCH_KNEE_ANGLE = 165.0
CROUCH_DEEP_HIP_THRESHOLD = 0.22

# Modo PEITORAL
UPPER_LATERAL_THRESHOLD = 0.45
UPPER_JUMP_LIFT_THRESHOLD = 0.25
UPPER_JUMP_MIN_LIFT_WITH_VELOCITY = 0.10
UPPER_JUMP_UPWARD_VELOCITY = 0.85
UPPER_CROUCH_DROP_THRESHOLD = 0.18
# Durante o agachamento, velocidade negativa significa que os ombros ainda estao
# descendo. Isso deve ser aceito. Apenas uma SUBIDA rapida cancela a confirmacao.
UPPER_CROUCH_MAX_UPWARD_VELOCITY = 0.45
UPPER_CROUCH_CONFIRM_SECONDS = 0.18

# Reinicio no modo PEITORAL: abrir os dois bracos aproximadamente na horizontal.
# ARM_SPAN = distancia entre pulsos / largura dos ombros.
UPPER_RESTART_ARM_SPAN_THRESHOLD = 3.00
# Cada pulso precisa ultrapassar lateralmente o ombro correspondente.
UPPER_RESTART_MIN_SIDE_EXTENSION = 0.60
# Tolerancia vertical dos pulsos em relacao a linha dos ombros.
UPPER_RESTART_MAX_VERTICAL_OFFSET = 0.95

# Modo ROSTO
FACE_YAW_DIRECTION = -1.0
FACE_PITCH_DIRECTION = -1.0
FACE_YAW_THRESHOLD_DEG = 20.0
FACE_PITCH_THRESHOLD_DEG = 15.0
FACE_ANGLE_SMOOTHING_ALPHA = 0.25

# Modo MAOS
# O Gesture Recognizer retorna Open_Palm e Closed_Fist com um score de 0 a 1.
HAND_GESTURE_MIN_SCORE = 0.55
HAND_HANDEDNESS_MIN_SCORE = 0.50
# Se a sua camera/driver fizer a lateralidade aparecer invertida no HUD,
# altere para True.
HAND_SWAP_SIDES = True

# Coracao com duas maos. O MediaPipe nao possui "Heart" entre os gestos prontos,
# portanto o projeto detecta a geometria usando os landmarks das duas maos.
# Distancias sao normalizadas pelo tamanho medio das maos.
HAND_HEART_CONTACT_RATIO = 0.75
HAND_HEART_MIN_OPENING_RATIO = 0.65
HAND_HEART_MIN_VERTICAL_GAP_RATIO = 0.35

# HUD / tela cheia
HUD_FONT_SCALE = 0.62
HUD_LINE_HEIGHT = 27
LANDMARK_RADIUS = 2
FULLSCREEN = True
HUD_SIDEBAR_MIN_WIDTH = 350
HUD_SIDEBAR_MAX_WIDTH = 455
