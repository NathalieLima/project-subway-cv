from __future__ import annotations

import ctypes
import platform
import sys
import time
from typing import Any

import cv2

from calibration.calibrator import Calibrator
from classifiers.body_classifier import BodyClassifier
from classifiers.face_classifier import FaceClassifier
from classifiers.hand_classifier import HandClassifier
from classifiers.stabilizer import StateStabilizer
from classifiers.upper_body_classifier import UpperBodyClassifier
from config import (
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_CENTER_CROP_ENABLED,
    CAMERA_CENTER_CROP_WIDTH_RATIO,
    CAMERA_CENTER_CROP_HEIGHT_RATIO,
    CAMERA_CENTER_CROP_OFFSET_X,
    CAMERA_CENTER_CROP_OFFSET_Y,
    FACE_MODEL_PATH,
    FULLSCREEN,
    GESTURE_MODEL_PATH,
    HAND_MIN_STATE_VOTES,
    HAND_SMOOTHING_WINDOW,
    POSE_MODEL_PATH,
)
from controllers.game_controller import GameController
from controllers.hand_gesture_manager import HandGestureManager
from controllers.hotkeys import GlobalHotkeys
from controllers.transition_manager import TransitionManager
from states import Estado
from vision.face_detector import FaceDetector
from vision.hand_detector import HandDetector
from vision.hud import draw_face, draw_guides, draw_hands, draw_hud, draw_pose
from vision.pose_detector import PoseDetector


MODES = {"1": "CORPO", "2": "PEITORAL", "3": "ROSTO", "4": "MAOS"}


def choose_mode() -> str:
    print("\nEscolha o modo de controle:\n")
    print("1 - CORPO")
    print("2 - PEITORAL")
    print("3 - ROSTO")
    print("4 - MAOS")
    while True:
        option = input("\nModo: ").strip()
        if option in MODES:
            return MODES[option]
        print("Opcao invalida. Digite 1, 2, 3 ou 4.")


def open_camera() -> cv2.VideoCapture:
    if platform.system() == "Windows":
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(CAMERA_INDEX)
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError(
            f"Nao foi possivel abrir a camera CAMERA_INDEX={CAMERA_INDEX}. "
            "Altere CAMERA_INDEX em config.py."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap




def crop_center(frame: Any) -> Any:
    """Recorta uma ROI central antes da inferencia e do HUD.

    Isso reduz a chance de o MediaPipe escolher pessoas que estejam nas
    laterais. Como deteccao, landmarks e exibicao usam o MESMO frame recortado,
    as coordenadas normalizadas continuam coerentes com o HUD.
    """
    if not CAMERA_CENTER_CROP_ENABLED:
        return frame

    height, width = frame.shape[:2]
    width_ratio = max(0.20, min(float(CAMERA_CENTER_CROP_WIDTH_RATIO), 1.0))
    height_ratio = max(0.20, min(float(CAMERA_CENTER_CROP_HEIGHT_RATIO), 1.0))

    crop_w = max(1, int(round(width * width_ratio)))
    crop_h = max(1, int(round(height * height_ratio)))

    # Offset e expresso como fracao da dimensao total do frame.
    center_x = width / 2.0 + float(CAMERA_CENTER_CROP_OFFSET_X) * width
    center_y = height / 2.0 + float(CAMERA_CENTER_CROP_OFFSET_Y) * height

    x1 = int(round(center_x - crop_w / 2.0))
    y1 = int(round(center_y - crop_h / 2.0))
    x1 = max(0, min(x1, width - crop_w))
    y1 = max(0, min(y1, height - crop_h))
    x2 = x1 + crop_w
    y2 = y1 + crop_h

    return frame[y1:y2, x1:x2].copy()

def get_display_size() -> tuple[int, int]:
    """Retorna a resolucao principal para montar o dashboard em tela cheia."""
    if platform.system() == "Windows":
        try:
            user32 = ctypes.windll.user32
            return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
        except Exception:
            pass
    return 1600, 900


def build_mode(mode: str) -> tuple[Any, Any]:
    if mode == "CORPO":
        return PoseDetector(POSE_MODEL_PATH), BodyClassifier()
    if mode == "PEITORAL":
        return PoseDetector(POSE_MODEL_PATH), UpperBodyClassifier()
    if mode == "ROSTO":
        return FaceDetector(FACE_MODEL_PATH), FaceClassifier()
    return HandDetector(GESTURE_MODEL_PATH), HandClassifier()


def reset_for_calibration(
    classifier: Any,
    stabilizer: StateStabilizer,
    transition_manager: TransitionManager,
    game_controller: GameController,
    calibrator: Calibrator,
) -> None:
    classifier.reset()
    stabilizer.reset(Estado.CENTRO)
    transition_manager.reset()
    game_controller.reset_cooldowns()
    calibrator.start()


def reset_hand_mode(
    classifier: HandClassifier,
    stabilizer: StateStabilizer,
    hand_manager: HandGestureManager,
    game_controller: GameController,
    calibrator: Calibrator,
) -> None:
    classifier.reset()
    stabilizer.reset(Estado.CENTRO)
    hand_manager.reset()
    game_controller.reset_cooldowns()
    # O Gesture Recognizer nao precisa de baseline geometrica.
    calibrator.active = False
    calibrator.complete = True
    calibrator.baseline = {}
    calibrator.samples.clear()


def main() -> int:
    mode = choose_mode()
    hand_mode = mode == "MAOS"

    print(f"\nModo selecionado: {mode}")
    if hand_mode:
        print("O modo MAOS nao precisa de calibracao geometrica.")
        print("F8 reinicia os gestos | controle ativo automaticamente | F10 encerra\n")
    else:
        print("A calibracao inicial comecara automaticamente.")
        print("F8 recalibra | controle do jogo ativa automaticamente apos calibrar | F10 encerra\n")

    try:
        detector, classifier = build_mode(mode)
        cap = open_camera()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    if hand_mode:
        stabilizer = StateStabilizer(
            window_size=HAND_SMOOTHING_WINDOW,
            min_votes=HAND_MIN_STATE_VOTES,
        )
    else:
        stabilizer = StateStabilizer()

    transition_manager = TransitionManager()
    hand_manager = HandGestureManager()
    game_controller = GameController()
    hotkeys = GlobalHotkeys()
    calibrator = Calibrator()

    if hand_mode:
        reset_hand_mode(classifier, stabilizer, hand_manager, game_controller, calibrator)
        game_enabled = True
    else:
        game_enabled = False
        reset_for_calibration(classifier, stabilizer, transition_manager, game_controller, calibrator)

    hotkeys.start()

    last_frame_time = time.perf_counter()
    fps_smoothed = 0.0
    start_time = time.perf_counter()
    last_timestamp_ms = -1
    state = Estado.CENTRO
    window_name = "Subway Vision Controller"
    display_size = get_display_size()
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    if FULLSCREEN:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while cap.isOpened():
            if GlobalHotkeys.consume(hotkeys.exit):
                break

            if GlobalHotkeys.consume(hotkeys.calibrate):
                if hand_mode:
                    reset_hand_mode(classifier, stabilizer, hand_manager, game_controller, calibrator)
                    game_enabled = True
                else:
                    game_enabled = False
                    reset_for_calibration(
                        classifier, stabilizer, transition_manager, game_controller, calibrator
                    )

            ok, frame = cap.read()
            if not ok or frame is None:
                print("ERRO: falha ao capturar frame da webcam.")
                break

            frame = cv2.flip(frame, 1)
            frame = crop_center(frame)
            now = time.perf_counter()
            timestamp_ms = int((now - start_time) * 1000.0)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms

            detected = detector.detect(frame, timestamp_ms)

            if mode == "ROSTO":
                face_data = detected
                landmarks = face_data.get("landmarks") if face_data else None
                features = classifier.extrair_features(face_data)
                draw_face(frame, landmarks)
            elif mode == "MAOS":
                hand_data = detected
                features = None
                draw_hands(frame, hand_data)
            else:
                landmarks = detected
                features = classifier.extrair_features(landmarks)
                draw_pose(frame, landmarks)

            if hand_mode:
                raw_state = classifier.classificar(hand_data, now)
                state = stabilizer.update(raw_state)

                if game_enabled and game_controller.game_has_focus():
                    # No modo MAOS cada gesto e um comando relativo de uma etapa.
                    commands = hand_manager.process(state)
                    game_controller.send(commands)
            elif calibrator.active:
                baseline = calibrator.update(features)
                state = Estado.SEM_POSE if features is None else Estado.CENTRO
                if baseline is not None:
                    classifier.definir_baseline(baseline)
                    stabilizer.reset(Estado.CENTRO)
                    transition_manager.reset()
                    game_controller.reset_cooldowns()
                    game_enabled = True
                    state = Estado.CENTRO
            elif calibrator.complete:
                raw_state = classifier.classificar(features, now)
                state = stabilizer.update(raw_state)

                if (
                    game_enabled
                    and state != Estado.SEM_POSE
                    and game_controller.game_has_focus()
                ):
                    commands = transition_manager.process(state)
                    game_controller.send(commands)
            else:
                state = Estado.SEM_POSE if features is None else Estado.CENTRO

            if calibrator.complete and not hand_mode:
                draw_guides(frame, mode, classifier)

            dt = max(now - last_frame_time, 1e-6)
            instant_fps = 1.0 / dt
            fps_smoothed = (
                instant_fps
                if fps_smoothed == 0
                else (0.90 * fps_smoothed + 0.10 * instant_fps)
            )
            last_frame_time = now

            calibration_message = (
                "MAOS: CALIBRACAO NAO NECESSARIA"
                if hand_mode
                else calibrator.message()
            )

            display_frame = draw_hud(
                frame=frame,
                mode=mode,
                state=state,
                fps=fps_smoothed,
                game_enabled=game_enabled,
                calibrated=calibrator.complete,
                calibration_message=calibration_message,
                classifier=classifier,
                display_size=display_size,
            )

            cv2.imshow(window_name, display_frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except KeyboardInterrupt:
        pass
    finally:
        hotkeys.stop()
        cap.release()
        detector.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
