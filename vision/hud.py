"""HUD em tela cheia, landmarks e guias visuais."""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from config import (
    CROUCH_DEEP_HIP_THRESHOLD,
    CROUCH_HIP_THRESHOLD,
    CROUCH_KNEE_ANGLE,
    FACE_PITCH_THRESHOLD_DEG,
    FACE_YAW_THRESHOLD_DEG,
    HAND_GESTURE_MIN_SCORE,
    HAND_HEART_CONTACT_RATIO,
    HAND_HEART_MIN_VERTICAL_GAP_RATIO,
    HUD_SIDEBAR_MAX_WIDTH,
    HUD_SIDEBAR_MIN_WIDTH,
    JUMP_THRESHOLD,
    LANDMARK_RADIUS,
    LATERAL_THRESHOLD,
    UPPER_CROUCH_CONFIRM_SECONDS,
    UPPER_CROUCH_DROP_THRESHOLD,
    UPPER_CROUCH_MAX_UPWARD_VELOCITY,
    UPPER_JUMP_LIFT_THRESHOLD,
    UPPER_JUMP_UPWARD_VELOCITY,
    UPPER_LATERAL_THRESHOLD,
    UPPER_RESTART_ARM_SPAN_THRESHOLD,
    UPPER_RESTART_MAX_VERTICAL_OFFSET,
    UPPER_RESTART_MIN_SIDE_EXTENSION,
)
from states import Estado


# BGR
BG = (20, 23, 29)
PANEL = (31, 35, 43)
PANEL_2 = (39, 44, 53)
BORDER = (62, 69, 82)
TEXT = (240, 243, 247)
MUTED = (162, 170, 184)
ACCENT = (86, 199, 122)
CYAN = (224, 183, 72)
YELLOW = (73, 208, 245)
RED = (92, 92, 232)
PURPLE = (208, 117, 187)

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def draw_pose(frame: Any, landmarks: list[Any] | None) -> None:
    if not landmarks:
        return
    h, w = frame.shape[:2]
    for a, b in POSE_CONNECTIONS:
        if a < len(landmarks) and b < len(landmarks):
            pa = (int(landmarks[a].x * w), int(landmarks[a].y * h))
            pb = (int(landmarks[b].x * w), int(landmarks[b].y * h))
            cv2.line(frame, pa, pb, ACCENT, 2, cv2.LINE_AA)
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(frame, (x, y), LANDMARK_RADIUS, YELLOW, -1, cv2.LINE_AA)


def draw_face(frame: Any, landmarks: list[Any] | None) -> None:
    if not landmarks:
        return
    h, w = frame.shape[:2]
    for i, lm in enumerate(landmarks):
        if i % 5 != 0:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(frame, (x, y), 1, YELLOW, -1, cv2.LINE_AA)


def draw_hands(frame: Any, hand_data: dict[str, Any] | None) -> None:
    if not hand_data:
        return
    h, w = frame.shape[:2]
    for hand in hand_data.get("hands", []):
        landmarks = hand.get("landmarks") or []
        for a, b in HAND_CONNECTIONS:
            if a < len(landmarks) and b < len(landmarks):
                pa = (int(landmarks[a].x * w), int(landmarks[a].y * h))
                pb = (int(landmarks[b].x * w), int(landmarks[b].y * h))
                cv2.line(frame, pa, pb, ACCENT, 2, cv2.LINE_AA)
        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            if 0 <= x < w and 0 <= y < h:
                cv2.circle(frame, (x, y), LANDMARK_RADIUS + 1, YELLOW, -1, cv2.LINE_AA)

        if landmarks:
            wrist = landmarks[0]
            x, y = int(wrist.x * w), int(wrist.y * h)
            side = hand.get("side", "?")
            gesture = hand.get("gesture", "None")
            score = float(hand.get("gesture_score", 0.0))
            label = f"{side}: {gesture} {score:.2f}"
            _shadow_text(frame, label, (max(5, x - 80), max(20, y - 15)), 0.48)


def _shadow_text(
    image: np.ndarray,
    text: str,
    org: tuple[int, int],
    scale: float,
    color: tuple[int, int, int] = TEXT,
    thickness: int = 1,
) -> None:
    cv2.putText(image, text, (org[0] + 1, org[1] + 1), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def _rounded_rect(
    image: np.ndarray,
    p1: tuple[int, int],
    p2: tuple[int, int],
    color: tuple[int, int, int],
    radius: int = 18,
    thickness: int = -1,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    radius = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if thickness != -1:
        cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, thickness, cv2.LINE_AA)
        cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness, cv2.LINE_AA)
        return

    cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    cv2.circle(image, (x1 + radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x2 - radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x1 + radius, y2 - radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x2 - radius, y2 - radius), radius, color, -1, cv2.LINE_AA)


def _vline(frame: Any, x_norm: float, label: str) -> None:
    h, w = frame.shape[:2]
    x = int(x_norm * w)
    cv2.line(frame, (x, 0), (x, h), CYAN, 1, cv2.LINE_AA)
    _shadow_text(frame, label, (max(5, x - 45), h - 18), 0.5)


def _hline(frame: Any, y_norm: float, label: str) -> None:
    h, w = frame.shape[:2]
    y = int(y_norm * h)
    cv2.line(frame, (0, y), (w, y), YELLOW, 1, cv2.LINE_AA)
    _shadow_text(frame, label, (w - 185, max(20, y - 6)), 0.5)


def draw_guides(frame: Any, mode: str, classifier: Any) -> None:
    guides = classifier.limites_guias() if hasattr(classifier, "limites_guias") else None
    if mode in {"CORPO", "PEITORAL"} and guides:
        _vline(frame, guides["left_x"], "ESQUERDA")
        _vline(frame, guides["right_x"], "DIREITA")
        h, w = frame.shape[:2]
        _shadow_text(frame, "CENTRO", (w // 2 - 40, h - 18), 0.5)

    if mode == "PEITORAL" and guides:
        _hline(frame, guides["jump_y"], "PULO")
        _hline(frame, guides["neutral_y"], "NEUTRO")
        _hline(frame, guides["crouch_y"], "AGACHADO")

    if mode == "ROSTO":
        h, w = frame.shape[:2]
        cx, cy = w - 155, 150
        cv2.rectangle(frame, (cx - 110, cy - 58), (cx + 110, cy + 58), CYAN, 1)
        _shadow_text(frame, "CENTRO", (cx - 35, cy + 5), 0.5)
        _shadow_text(frame, "ESQUERDA", (cx - 108, cy - 72), 0.45)
        _shadow_text(frame, "DIREITA", (cx + 44, cy - 72), 0.45)
        _shadow_text(frame, "PULO", (cx - 22, cy - 74), 0.45)
        _shadow_text(frame, "AGACHADO", (cx - 40, cy + 80), 0.45)


def _state_color(state: Estado) -> tuple[int, int, int]:
    return {
        Estado.CENTRO: CYAN,
        Estado.ESQUERDA: YELLOW,
        Estado.DIREITA: YELLOW,
        Estado.PULO: ACCENT,
        Estado.AGACHADO: PURPLE,
        Estado.REINICIAR: (68, 165, 245),
        Estado.SEM_POSE: RED,
    }.get(state, TEXT)


def _fit_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(width / max(w, 1), height / max(h, 1))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)


def _draw_card_title(canvas: np.ndarray, x: int, y: int, title: str) -> None:
    _shadow_text(canvas, title, (x, y), 0.55, MUTED, 1)


def _draw_lines(
    canvas: np.ndarray,
    lines: list[str],
    x: int,
    y: int,
    max_width: int,
    line_height: int = 28,
    scale: float = 0.52,
) -> int:
    yy = y
    for line in lines:
        # Quebra simples para evitar estourar o painel em resolucoes menores.
        pieces = [line]
        if cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > max_width:
            words = line.split()
            pieces = []
            current = ""
            for word in words:
                candidate = (current + " " + word).strip()
                if current and cv2.getTextSize(candidate, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > max_width:
                    pieces.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                pieces.append(current)
        for piece in pieces:
            _shadow_text(canvas, piece, (x, yy), scale, TEXT, 1)
            yy += line_height
    return yy


def _mode_help(mode: str) -> list[str]:
    if mode == "CORPO":
        return [
            "Mover corpo: esquerda / direita",
            "Pular: subir corpo",
            "Agachar: abaixar quadril",
        ]
    if mode == "PEITORAL":
        return [
            "Mover tronco: esquerda / direita",
            "Subir ombros: pular",
            "Descer ombros: agachar",
            "Abrir os 2 bracos: F5 / reiniciar",
        ]
    if mode == "ROSTO":
        return [
            "Virar cabeca: esquerda / direita",
            "Olhar para cima: pular",
            "Olhar para baixo: agachar",
        ]
    return [
        "Palma esquerda: esquerda",
        "Palma direita: direita",
        "2 palmas abertas: pular",
        "2 punhos fechados: agachar",
        "Coracao com 2 maos: F5 / reiniciar",
    ]


def _debug_lines(mode: str, classifier: Any) -> list[str]:
    d = getattr(classifier, "debug", {}) or {}
    if not d:
        return ["Aguardando dados..."]

    if mode == "CORPO":
        return [
            f"Lateral  {d.get('lateral', 0):+.2f} / {LATERAL_THRESHOLD:.2f}",
            f"Pulo     {d.get('jump_score', 0):+.2f} / {JUMP_THRESHOLD:.2f}",
            f"Quadril  {d.get('hip_drop', 0):+.2f} / {CROUCH_HIP_THRESHOLD:.2f}",
            f"Joelho   {d.get('knee_angle', 0):.1f} / {CROUCH_KNEE_ANGLE:.0f}",
            f"Profundo {d.get('hip_drop', 0):+.2f} / {CROUCH_DEEP_HIP_THRESHOLD:.2f}",
        ]
    if mode == "PEITORAL":
        arms = "ABERTOS" if d.get("arms_open", 0) >= 0.5 else "normal"
        if d.get("arms_visible", 0) < 0.5:
            arms = "pulsos nao visiveis"
        return [
            f"Lateral     {d.get('lateral', 0):+.2f} / {UPPER_LATERAL_THRESHOLD:.2f}",
            f"Subida      {d.get('lift', 0):+.2f} / {UPPER_JUMP_LIFT_THRESHOLD:.2f}",
            f"Descida     {d.get('drop', 0):+.2f} / {UPPER_CROUCH_DROP_THRESHOLD:.2f}",
            f"Velocidade  {d.get('velocity', 0):+.2f} / {UPPER_JUMP_UPWARD_VELOCITY:.2f}",
            f"Agachado    {d.get('crouch_time', 0):.2f}s / {UPPER_CROUCH_CONFIRM_SECONDS:.2f}s",
            f"Bracos      {arms}",
            f"Span        {d.get('arm_span', 0):.2f} / {UPPER_RESTART_ARM_SPAN_THRESHOLD:.2f}",
            f"Ext. lateral {d.get('arm_min_side_extension', 0):.2f} / {UPPER_RESTART_MIN_SIDE_EXTENSION:.2f}",
            f"Altura braco {d.get('arm_vertical_offset', 0):.2f} <= {UPPER_RESTART_MAX_VERTICAL_OFFSET:.2f}",
        ]
    if mode == "ROSTO":
        return [
            f"Yaw    {d.get('yaw', 0):+.1f} / {FACE_YAW_THRESHOLD_DEG:.0f}",
            f"Pitch  {d.get('pitch', 0):+.1f} / {FACE_PITCH_THRESHOLD_DEG:.0f}",
        ]

    heart = "DETECTADO" if d.get("heart_detected", 0) >= 0.5 else "nao"
    return [
        f"Mao esq.  {d.get('left_gesture', 'AUSENTE')}  {d.get('left_score', 0):.2f}",
        f"Mao dir.  {d.get('right_gesture', 'AUSENTE')}  {d.get('right_score', 0):.2f}",
        f"Score min {HAND_GESTURE_MIN_SCORE:.2f}",
        f"Coracao   {heart}",
        f"Indicadores {d.get('heart_index_contact', 99):.2f} <= {HAND_HEART_CONTACT_RATIO:.2f}",
        f"Polegares   {d.get('heart_thumb_contact', 99):.2f} <= {HAND_HEART_CONTACT_RATIO:.2f}",
        f"Gap vertical {d.get('heart_vertical_gap', 0):.2f} >= {HAND_HEART_MIN_VERTICAL_GAP_RATIO:.2f}",
    ]


def draw_hud(
    frame: Any,
    mode: str,
    state: Estado,
    fps: float,
    game_enabled: bool,
    calibrated: bool,
    calibration_message: str,
    classifier: Any,
    display_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Monta um dashboard em tela cheia e retorna a imagem final para cv2.imshow."""
    src_h, src_w = frame.shape[:2]
    if display_size is None:
        screen_w, screen_h = src_w, src_h
    else:
        screen_w = max(1024, int(display_size[0]))
        screen_h = max(640, int(display_size[1]))

    canvas = np.full((screen_h, screen_w, 3), BG, dtype=np.uint8)

    margin = max(16, int(screen_w * 0.012))
    top_h = max(76, int(screen_h * 0.075))
    bottom_h = max(52, int(screen_h * 0.055))
    sidebar_w = int(screen_w * 0.235)
    sidebar_w = max(HUD_SIDEBAR_MIN_WIDTH, min(HUD_SIDEBAR_MAX_WIDTH, sidebar_w))

    # Header
    _shadow_text(canvas, "SUBWAY VISION CONTROLLER", (margin, int(top_h * 0.62)), 0.82, TEXT, 2)

    mode_x = max(360, int(screen_w * 0.28))
    _rounded_rect(canvas, (mode_x, 20), (mode_x + 155, top_h - 17), PANEL_2, 14)
    _shadow_text(canvas, f"MODO  {mode}", (mode_x + 16, top_h // 2 + 7), 0.52, CYAN, 1)

    state_color = _state_color(state)
    state_x = mode_x + 170
    _rounded_rect(canvas, (state_x, 20), (state_x + 215, top_h - 17), state_color, 14)
    _shadow_text(canvas, state.value, (state_x + 18, top_h // 2 + 8), 0.62, (20, 22, 26), 2)

    fps_text = f"{fps:4.1f} FPS"
    active_text = "CONTROLE ATIVO" if game_enabled else "CONTROLE PAUSADO"
    active_color = ACCENT if game_enabled else RED
    right_header_x = screen_w - margin - 305
    _shadow_text(canvas, fps_text, (right_header_x, top_h // 2 + 7), 0.55, MUTED, 1)
    cv2.circle(canvas, (right_header_x + 130, top_h // 2), 7, active_color, -1, cv2.LINE_AA)
    _shadow_text(canvas, active_text, (right_header_x + 145, top_h // 2 + 7), 0.48, TEXT, 1)

    content_top = top_h + 4
    content_bottom = screen_h - bottom_h - margin
    sidebar_x = screen_w - margin - sidebar_w
    camera_x1 = margin
    camera_y1 = content_top
    camera_x2 = sidebar_x - margin
    camera_y2 = content_bottom

    # Camera card
    _rounded_rect(canvas, (camera_x1, camera_y1), (camera_x2, camera_y2), PANEL, 20)
    inner_pad = 10
    avail_w = camera_x2 - camera_x1 - inner_pad * 2
    avail_h = camera_y2 - camera_y1 - inner_pad * 2
    fitted = _fit_image(frame, avail_w, avail_h)
    fh, fw = fitted.shape[:2]
    fx = camera_x1 + inner_pad + (avail_w - fw) // 2
    fy = camera_y1 + inner_pad + (avail_h - fh) // 2
    canvas[fy:fy + fh, fx:fx + fw] = fitted
    cv2.rectangle(canvas, (fx, fy), (fx + fw, fy + fh), BORDER, 1, cv2.LINE_AA)

    # Badge dentro da camera.
    badge = "CALIBRADO" if calibrated else "CALIBRANDO"
    badge_color = ACCENT if calibrated else YELLOW
    _rounded_rect(canvas, (fx + 16, fy + 16), (fx + 150, fy + 54), PANEL, 12)
    cv2.circle(canvas, (fx + 34, fy + 35), 6, badge_color, -1, cv2.LINE_AA)
    _shadow_text(canvas, badge, (fx + 48, fy + 41), 0.43, TEXT, 1)

    if state == Estado.SEM_POSE:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (fx, fy), (fx + fw, fy + fh), (28, 28, 95), -1)
        cv2.addWeighted(overlay, 0.34, canvas, 0.66, 0, canvas)
        text = "SEM_POSE"
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3)[0]
        _shadow_text(canvas, text, (fx + (fw - size[0]) // 2, fy + fh // 2), 1.6, RED, 3)

    # Sidebar
    side_top = content_top
    gap = 12
    status_h = 110
    help_h = 190 if mode in {"PEITORAL", "MAOS"} else 160
    debug_y = side_top + status_h + gap + help_h + gap
    debug_h = max(180, content_bottom - debug_y)

    # Status card
    _rounded_rect(canvas, (sidebar_x, side_top), (sidebar_x + sidebar_w, side_top + status_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, side_top + 28, "ESTADO ATUAL")
    _shadow_text(canvas, state.value, (sidebar_x + 18, side_top + 72), 0.82, state_color, 2)
    subtitle = "F5 enviado ao jogo" if state == Estado.REINICIAR else calibration_message
    _shadow_text(canvas, subtitle[:45], (sidebar_x + 18, side_top + 98), 0.40, MUTED, 1)

    # Gestos card
    help_y = side_top + status_h + gap
    _rounded_rect(canvas, (sidebar_x, help_y), (sidebar_x + sidebar_w, help_y + help_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, help_y + 28, "COMANDOS DO MODO")
    _draw_lines(canvas, _mode_help(mode), sidebar_x + 18, help_y + 58, sidebar_w - 36, 28, 0.48)

    # Debug card
    _rounded_rect(canvas, (sidebar_x, debug_y), (sidebar_x + sidebar_w, debug_y + debug_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, debug_y + 28, "DEBUG / AJUSTE FINO")
    _draw_lines(canvas, _debug_lines(mode, classifier), sidebar_x + 18, debug_y + 58,
                sidebar_w - 36, 25, 0.45)

    # Footer
    footer_y = screen_h - bottom_h + 5
    _shadow_text(canvas, "F8", (margin, footer_y + 24), 0.52, CYAN, 2)
    f8_text = "reiniciar gestos" if mode == "MAOS" else "recalibrar"
    _shadow_text(canvas, f8_text, (margin + 42, footer_y + 24), 0.46, MUTED, 1)
    _shadow_text(canvas, "F10", (margin + 190, footer_y + 24), 0.52, CYAN, 2)
    _shadow_text(canvas, "sair", (margin + 244, footer_y + 24), 0.46, MUTED, 1)
    _shadow_text(canvas, "ESC", (margin + 330, footer_y + 24), 0.52, CYAN, 2)
    _shadow_text(canvas, "sair da interface", (margin + 382, footer_y + 24), 0.46, MUTED, 1)

    return canvas
