import unittest
from unittest.mock import patch

from calibration.calibrator import Calibrator
from classifiers.body_classifier import BodyClassifier
from classifiers.stabilizer import StateStabilizer
from classifiers.upper_body_classifier import UpperBodyClassifier
from controllers.transition_manager import TransitionManager
from states import Estado


class TransitionManagerTests(unittest.TestCase):
    def test_center_to_left(self):
        t = TransitionManager()
        self.assertEqual(t.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(t.process(Estado.ESQUERDA), [])

    def test_left_to_center_sends_right(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.CENTRO), [Estado.DIREITA])

    def test_center_to_right(self):
        t = TransitionManager()
        self.assertEqual(t.process(Estado.DIREITA), [Estado.DIREITA])
        self.assertEqual(t.process(Estado.DIREITA), [])

    def test_right_to_center_sends_left(self):
        t = TransitionManager()
        t.process(Estado.DIREITA)
        self.assertEqual(t.process(Estado.CENTRO), [Estado.ESQUERDA])

    def test_two_lane_transition(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.DIREITA), [Estado.DIREITA, Estado.DIREITA])
        self.assertEqual(t.process(Estado.ESQUERDA), [Estado.ESQUERDA, Estado.ESQUERDA])

    def test_vertical_does_not_change_lane_and_is_edge_triggered(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.PULO), [Estado.PULO])
        self.assertEqual(t.process(Estado.PULO), [])
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.ESQUERDA), [])

    def test_sem_pose_does_not_change_lane(self):
        t = TransitionManager()
        t.process(Estado.DIREITA)
        self.assertEqual(t.process(Estado.SEM_POSE), [])
        self.assertEqual(t.faixa_lateral, Estado.DIREITA)

    def test_restart_is_edge_triggered_and_keeps_lane(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.REINICIAR), [Estado.REINICIAR])
        self.assertEqual(t.process(Estado.REINICIAR), [])
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.ESQUERDA), [])
        self.assertEqual(t.process(Estado.REINICIAR), [Estado.REINICIAR])


class StabilizerTests(unittest.TestCase):
    def test_single_outlier_does_not_change_state(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        for state in [Estado.CENTRO, Estado.CENTRO, Estado.DIREITA, Estado.CENTRO, Estado.CENTRO]:
            result = s.update(state)
        self.assertEqual(result, Estado.CENTRO)

    def test_sem_pose_is_not_added_to_history(self):
        s = StateStabilizer(window_size=3, min_votes=2)
        s.update(Estado.ESQUERDA)
        s.update(Estado.ESQUERDA)
        self.assertEqual(s.update(Estado.SEM_POSE), Estado.SEM_POSE)
        self.assertEqual(s.stable_state, Estado.ESQUERDA)

    def test_jump_is_confirmed_with_two_votes_in_three_frames(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        s.update(Estado.CENTRO)
        s.update(Estado.CENTRO)
        self.assertNotEqual(s.update(Estado.PULO), Estado.PULO)
        self.assertEqual(s.update(Estado.PULO), Estado.PULO)

    def test_single_jump_frame_is_filtered(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        s.update(Estado.CENTRO)
        s.update(Estado.CENTRO)
        self.assertNotEqual(s.update(Estado.PULO), Estado.PULO)
        self.assertNotEqual(s.update(Estado.CENTRO), Estado.PULO)


class CrouchRecognitionTests(unittest.TestCase):
    def test_upper_body_accepts_descent_and_confirms_crouch(self):
        c = UpperBodyClassifier()
        c.definir_baseline({
            "shoulder_x": 0.50,
            "shoulder_y": 0.50,
            "shoulder_width": 0.20,
        })

        # Cruza o limiar de agachamento ainda descendo.
        first = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.54,
            "shoulder_width": 0.20,
        }, 1.00)
        self.assertNotEqual(first, Estado.AGACHADO)

        # Continua descendo; a velocidade e negativa e deve ser aceita.
        second = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.55,
            "shoulder_width": 0.20,
        }, 1.20)
        self.assertEqual(second, Estado.AGACHADO)

    def test_upper_body_open_arms_restarts(self):
        c = UpperBodyClassifier()
        c.definir_baseline({
            "shoulder_x": 0.50,
            "shoulder_y": 0.40,
            "shoulder_width": 0.20,
        })
        state = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.40,
            "shoulder_width": 0.20,
            "arm_span": 3.40,
            "arm_min_side_extension": 0.75,
            "arm_vertical_offset": 0.20,
        }, 1.0)
        self.assertEqual(state, Estado.REINICIAR)
        self.assertEqual(c.debug["arms_open"], 1.0)

    def test_body_deep_crouch_does_not_depend_only_on_knee_angle(self):
        c = BodyClassifier()
        c.definir_baseline({
            "torso_x": 0.50,
            "hip_x": 0.50,
            "hip_y": 0.50,
            "ankle_y": 0.90,
            "shoulder_width": 0.20,
            "torso_height": 0.20,
            "left_knee_angle": 180.0,
            "right_knee_angle": 180.0,
        })
        state = c.classificar({
            "torso_x": 0.50,
            "hip_x": 0.50,
            "hip_y": 0.55,  # queda de 0.25 torso_height: agachamento profundo
            "ankle_y": 0.90,
            "shoulder_width": 0.20,
            "torso_height": 0.20,
            "left_knee_angle": 175.0,
            "right_knee_angle": 175.0,
        }, 1.0)
        self.assertEqual(state, Estado.AGACHADO)


class CalibratorTests(unittest.TestCase):
    def test_uses_median(self):
        c = Calibrator(countdown_seconds=0.0, sample_count=5)
        with patch("calibration.calibrator.time.perf_counter", return_value=10.0):
            c.start()
            baseline = None
            for value in [1.0, 1.1, 50.0, 0.9, 1.0]:
                baseline = c.update({"x": value}) or baseline
        self.assertIsNotNone(baseline)
        self.assertAlmostEqual(baseline["x"], 1.0)


if __name__ == "__main__":
    unittest.main()
