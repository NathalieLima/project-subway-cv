import unittest
from types import SimpleNamespace

from classifiers.hand_classifier import HandClassifier
from controllers.hand_gesture_manager import HandGestureManager
from states import Estado


def lm(x=0.0, y=0.0):
    return SimpleNamespace(x=x, y=y)


def plain_landmarks(cx: float):
    points = [lm(cx, 0.60) for _ in range(21)]
    points[0] = lm(cx, 0.60)
    points[5] = lm(cx - 0.03, 0.52)
    points[9] = lm(cx, 0.50)
    points[17] = lm(cx + 0.03, 0.52)
    return points


def heart_landmarks(side: str):
    cx = 0.33 if side == "LEFT" else 0.67
    points = plain_landmarks(cx)
    if side == "LEFT":
        points[8] = lm(0.49, 0.40)  # indicador toca o da outra mao
        points[4] = lm(0.48, 0.50)  # polegar toca o da outra mao
    else:
        points[8] = lm(0.51, 0.40)
        points[4] = lm(0.52, 0.50)
    return points


def hand(side: str, gesture: str, score: float = 0.95, landmarks=None):
    return {
        "side": side,
        "gesture": gesture,
        "gesture_score": score,
        "side_score": 0.99,
        "landmarks": landmarks if landmarks is not None else plain_landmarks(0.35 if side == "LEFT" else 0.65),
    }


class HandClassifierTests(unittest.TestCase):
    def setUp(self):
        self.c = HandClassifier()

    def classify(self, *hands):
        return self.c.classificar({"hands": list(hands)})

    def test_left_open(self):
        self.assertEqual(self.classify(hand("LEFT", "Open_Palm")), Estado.ESQUERDA)

    def test_right_open(self):
        self.assertEqual(self.classify(hand("RIGHT", "Open_Palm")), Estado.DIREITA)

    def test_both_open_jump(self):
        self.assertEqual(
            self.classify(hand("LEFT", "Open_Palm"), hand("RIGHT", "Open_Palm")),
            Estado.PULO,
        )

    def test_both_closed_crouch(self):
        self.assertEqual(
            self.classify(hand("LEFT", "Closed_Fist"), hand("RIGHT", "Closed_Fist")),
            Estado.AGACHADO,
        )

    def test_heart_restarts(self):
        self.assertEqual(
            self.classify(
                hand("LEFT", "None", landmarks=heart_landmarks("LEFT")),
                hand("RIGHT", "None", landmarks=heart_landmarks("RIGHT")),
            ),
            Estado.REINICIAR,
        )
        self.assertEqual(self.c.debug["heart_detected"], 1.0)

    def test_one_closed_is_neutral(self):
        self.assertEqual(self.classify(hand("LEFT", "Closed_Fist")), Estado.CENTRO)

    def test_no_hands_is_sem_pose(self):
        self.assertEqual(self.classify(), Estado.SEM_POSE)

    def test_low_score_is_not_action(self):
        self.assertEqual(self.classify(hand("LEFT", "Open_Palm", 0.2)), Estado.CENTRO)


class HandGestureManagerTests(unittest.TestCase):
    def test_holding_does_not_repeat(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(m.process(Estado.ESQUERDA), [])

    def test_release_rearms_same_gesture(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.PULO), [Estado.PULO])
        self.assertEqual(m.process(Estado.CENTRO), [])
        self.assertEqual(m.process(Estado.PULO), [Estado.PULO])

    def test_restart_is_edge_triggered(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.REINICIAR), [Estado.REINICIAR])
        self.assertEqual(m.process(Estado.REINICIAR), [])
        self.assertEqual(m.process(Estado.CENTRO), [])
        self.assertEqual(m.process(Estado.REINICIAR), [Estado.REINICIAR])

    def test_switch_gesture_sends_one_each(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(m.process(Estado.DIREITA), [Estado.DIREITA])


if __name__ == "__main__":
    unittest.main()
